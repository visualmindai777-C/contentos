"""Pipeline completo con fakes de las interfaces sobre un Postgres real.

Requiere TEST_DATABASE_URL (p. ej. el servicio `db` de docker-compose con db/schema.sql aplicado); si no, se omite.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

URL = os.environ.get("TEST_DATABASE_URL")
if not URL:
    pytest.skip("TEST_DATABASE_URL no definida", allow_module_level=True)

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.agents.content_agent import ContentAgent
from app.agents.graph import Agents
from app.agents.media_agent import MediaAgent
from app.agents.runner import run_batch
from app.agents.storage_agent import StorageAgent
from app.agents.trend_agent import TrendAgent
from app.core.interfaces import ProviderError, RateLimitError
from app.core.types import GeneratedImage, LLMResponse, Narration, RenderedVideo, Segment, StoredObject, TrendCandidate
from app.models import Asset, Content, Project, Topic, User
from app.services.contents import ContentService

SCRIPT = " ".join(f"Palabra{i}" for i in range(45)) + ". Segunda frase del guion. Tercera frase del guion. Cuarta frase final."
DRAFT = json.dumps({"title": "Título de prueba", "hook": "Gancho", "script": SCRIPT, "caption": "Descripción",
                    "hashtags": ["ia", "#curiosidades", "ia"], "cta": "Sígueme"})
run = asyncio.run


class FakeLLM:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), 0

    async def complete(self, messages, *, json_mode=False, max_tokens=1200):
        self.calls += 1
        reply = self.replies.pop(0) if self.replies else DRAFT
        if isinstance(reply, Exception):
            raise reply
        return LLMResponse(reply, "fake", "fake-model", 100)


class FakeImages:
    def __init__(self, fail_first=None):
        self.calls, self.fail_first = 0, fail_first

    async def generate(self, prompt, *, width=1080, height=1920, seed=None):
        self.calls += 1
        if self.fail_first and self.calls == 1:
            raise self.fail_first
        return GeneratedImage(b"jpg", "image/jpeg")


class FakeTTS:
    async def synthesize(self, text, *, voice, lang):
        return Narration(b"wav", "audio/wav", 12.0, [Segment("hola mundo", 0, 12)])


class FakeVideo:
    def __init__(self):
        self.broken = False

    async def render(self, spec):
        if self.broken:
            raise ProviderError("ffmpeg roto")
        spec.output.write_bytes(b"mp4" * 100)
        return RenderedVideo(spec.output, 12.0, 300)


class FakeStorage:
    def __init__(self):
        self.objects = {}

    async def put_bytes(self, key, data, mime_type):
        self.objects[key] = data
        return StoredObject(key, len(data), mime_type, "fake")

    async def put_file(self, key, path, mime_type):
        return await self.put_bytes(key, path.read_bytes(), mime_type)

    async def delete(self, key):
        self.objects.pop(key, None)


class FakeTrend:
    name = "fake"

    def __init__(self):
        self.calls = 0

    async def fetch(self, project, limit):
        self.calls += 1
        return [TrendCandidate("Tema A", 80, ["inteligencia"], "fake"), TrendCandidate("Tema B", 50, ["robots"], "fake")]


class Rig:
    def __init__(self, sf, project_id, llm=None, images=None):
        self.sf, self.pid = sf, project_id
        self.llm, self.images, self.video, self.store, self.trend = llm or FakeLLM(), images or FakeImages(), FakeVideo(), FakeStorage(), FakeTrend()
        self.sleeps = []

        async def sleep(seconds):
            self.sleeps.append(seconds)

        self.agents = Agents(
            trend=TrendAgent([self.trend]), content=ContentAgent(self.llm),
            media=MediaAgent(FakeTTS(), self.images, self.video, voice="v", lang="e", sleep=sleep),
            storage=StorageAgent(sf, self.store),
        )

    async def batch(self, limit=1):
        return await run_batch(self.agents, limit=limit, project_ids=[self.pid])

    async def contents(self):
        async with self.sf() as s:
            return list((await s.scalars(select(Content).where(Content.project_id == self.pid).order_by(Content.created_at))).all())


@asynccontextmanager
async def rig(**kw):
    engine = create_async_engine(URL, poolclass=NullPool)
    sf = async_sessionmaker(engine, expire_on_commit=False)
    async with sf() as s:
        project = Project(user_id=await s.scalar(select(User.id).limit(1)), slug=f"t-{uuid4().hex[:8]}", name="Test",
                          niche="curiosidades sobre inteligencia artificial", language="es", config={"images_per_video": 3})
        s.add(project)
        await s.commit()
    try:
        yield Rig(sf, project.id, **kw)
    finally:
        async with sf() as s:
            await s.execute(delete(Project).where(Project.id == project.id))
            await s.commit()
        await engine.dispose()


def test_happy_path_generates_content_and_artifacts():
    async def scenario():
        async with rig() as r:
            result = await r.batch()
            (content,) = await r.contents()
            async with r.sf() as s:
                assets = list((await s.scalars(select(Asset).where(Asset.content_id == content.id))).all())
            return r, result, content, assets

    r, result, content, assets = run(scenario())
    assert (result.generated, result.failed, result.halted) == (1, 0, False)
    assert content.status == "generado" and content.title == "Título de prueba" and content.duration_seconds == 12.0
    assert (content.llm_provider, content.model_name, content.tokens_used) == ("fake", "fake-model", 100)
    assert content.hashtags == ["#ia", "#curiosidades"]  # normaliza y deduplica
    assert r.llm.calls == 1 and r.images.calls == 3
    assert sorted(a.kind for a in assets) == ["caption", "hashtags", "image", "image", "image", "metadata", "subtitles", "video"]
    prefix = f"contents/{content.id}"
    assert {f"{prefix}/video.mp4", f"{prefix}/caption.txt", f"{prefix}/hashtags.txt", f"{prefix}/metadata.json"} <= set(r.store.objects)
    meta = json.loads(r.store.objects[f"{prefix}/metadata.json"])
    assert set(meta) == {"topic", "title", "duration", "status", "created_at"} and meta["topic"] == "Tema A"


def test_queue_only_does_not_create_new_content():
    async def scenario():
        async with rig() as r:
            empty = await run_batch(r.agents, limit=3, project_ids=[r.pid], new_ideas=False)
            async with r.sf() as s:  # una idea pedida a mano
                s.add(Content(project_id=r.pid, title="Idea manual"))
                await s.commit()
            queued = await run_batch(r.agents, limit=3, project_ids=[r.pid], new_ideas=False)
            return r, empty, queued, await r.contents()

    r, empty, queued, contents = run(scenario())
    assert empty.processed == 0 and r.trend.calls == 0
    assert queued.generated == 1 and len(contents) == 1 and r.llm.calls == 1 and r.trend.calls == 0


def test_topics_are_reused_without_refetching_sources():
    async def scenario():
        async with rig() as r:
            result = await r.batch(limit=2)
            async with r.sf() as s:
                topics = {t.id: t.topic for t in (await s.scalars(select(Topic).where(Topic.project_id == r.pid))).all()}
            return r, result, [topics[c.topic_id] for c in await r.contents()]

    r, result, used = run(scenario())
    assert result.generated == 2 and r.trend.calls == 1
    assert sorted(used) == ["Tema A", "Tema B"]


def test_invalid_json_twice_records_error_keeps_idea_and_leaves_the_queue_until_retry():
    async def scenario():
        async with rig(llm=FakeLLM("no es json", "{}")) as r:
            first = await r.batch()
            (failed,) = await r.contents()
            waiting = await run_batch(r.agents, limit=3, project_ids=[r.pid], new_ideas=False)  # no se reprocesa solo
            calls_while_waiting = r.llm.calls
            async with r.sf() as s:
                await ContentService(s).retry(failed.id)
            second = await r.batch()  # el LLM ya responde bien (DRAFT por defecto)
            return r, first, failed, waiting, calls_while_waiting, second, (await r.contents())[0]

    r, first, failed, waiting, calls_while_waiting, second, done = run(scenario())
    assert (first.generated, first.failed, first.halted) == (0, 1, False)
    assert failed.status == "idea" and failed.tokens_used == 0 and failed.last_error.startswith("content:")
    assert waiting.processed == 0 and calls_while_waiting == 2  # sin reintentos automáticos que gasten cuota
    assert second.generated == 1 and done.status == "generado" and done.last_error == "" and r.llm.calls == 3


def test_llm_rate_limit_halts_the_batch_without_marking_contents_as_failed():
    async def scenario():
        async with rig(llm=FakeLLM(RateLimitError("cuota"), DRAFT, DRAFT)) as r:
            result = await r.batch(limit=3)
            return r, result, await r.contents()

    r, result, (content,) = run(scenario())
    assert result.halted and result.processed == 1 and r.llm.calls == 1
    assert content.status == "idea" and content.last_error == ""  # sigue en cola para el próximo ciclo


def test_media_failure_keeps_script_records_error_and_retry_does_not_call_llm_again():
    async def scenario():
        async with rig() as r:
            r.video.broken = True
            first = await r.batch()
            (mid,) = await r.contents()
            r.video.broken = False
            idle = await run_batch(r.agents, limit=3, project_ids=[r.pid], new_ideas=False)
            async with r.sf() as s:
                await ContentService(s).retry(mid.id)
            second = await r.batch()
            return r, first, mid, idle, second, (await r.contents())[0]

    r, first, mid, idle, second, end = run(scenario())
    assert first.failed == 1 and (mid.status, mid.script != "") == ("guion", True) and mid.last_error.startswith("media:")
    assert idle.processed == 0
    assert second.generated == 1 and end.status == "generado" and end.last_error == "" and r.llm.calls == 1


def test_image_rate_limit_waits_retry_after_and_still_finishes():
    async def scenario():
        async with rig(images=FakeImages(fail_first=RateLimitError("cuota", retry_after=2.0))) as r:
            return r, await r.batch()

    r, result = run(scenario())
    assert result.generated == 1 and r.sleeps == [3.0]


def test_image_transient_error_is_retried_and_all_failing_images_fail_the_media_step():
    async def scenario():
        async with rig(images=FakeImages(fail_first=ProviderError("timeout"))) as r:
            retried = await r.batch()
            sleeps = list(r.sleeps)
        broken = FakeImages(fail_first=ProviderError("x"))
        broken.generate = lambda *a, **k: (_ for _ in ()).throw(ProviderError("siempre falla"))
        async with rig(images=broken) as r2:
            return retried, sleeps, await r2.batch(), await r2.contents()

    retried, sleeps, failed, (content,) = run(scenario())
    assert retried.generated == 1 and sleeps == [5.0]
    assert failed.failed == 1 and content.status == "guion"  # guion conservado para reintentar solo la media


def test_regenerate_replaces_assets_and_deletes_stale_objects():
    async def scenario():
        async with rig() as r:
            await r.batch()
            (content,) = await r.contents()
            stale = f"contents/{content.id}/images/img_9.jpg"
            r.store.objects[stale] = b"old"
            async with r.sf() as s:
                s.add(Asset(content_id=content.id, kind="image", storage_key=stale, mime_type="image/jpeg"))
                (await s.get(Content, content.id)).status = "idea"  # lo que hace PATCH /regenerate
                await s.commit()
            result = await r.batch()
            async with r.sf() as s:
                keys = {a.storage_key for a in (await s.scalars(select(Asset).where(Asset.content_id == content.id))).all()}
            return r, result, stale, keys

    r, result, stale, keys = run(scenario())
    assert result.generated == 1 and stale not in keys and stale not in r.store.objects and r.llm.calls == 2


def test_purge_deletes_files_and_rows_only_for_rejected_contents():
    from app.core.errors import Conflict

    async def scenario():
        async with rig() as r:
            await r.batch()
            (content,) = await r.contents()
            keys = set(r.store.objects)
            async with r.sf() as s:
                with pytest.raises(Conflict):  # generado: no se puede borrar
                    await ContentService(s, r.store).purge(content.id)
                (await s.get(Content, content.id)).status = "rechazado"
                await s.commit()
            async with r.sf() as s:
                await ContentService(s, r.store).purge(content.id)
            async with r.sf() as s:
                left = (await s.scalars(select(Asset).where(Asset.content_id == content.id))).all()
                gone = await s.get(Content, content.id) is None
            return r, keys, left, gone

    r, keys, left, gone = run(scenario())
    assert keys and not r.store.objects and not left and gone


def test_dashboard_and_limits_come_from_a_single_consistent_snapshot():
    from app.services.dashboard import DashboardService
    from app.services.usage import UsageService

    os.environ.setdefault("DATABASE_URL", URL)  # UsageService lee Settings, que exige la URL

    async def scenario():
        async with rig() as r:
            await r.batch()
            async with r.sf() as s:
                stats = await DashboardService(s).stats()
                limits = await UsageService(s).limits()
                total = len((await s.scalars(select(Content))).all())
            return stats, limits, total

    stats, limits, total = run(scenario())
    assert stats.total == total == limits.estimated_content_count and stats.pending >= 1
    assert limits.estimated_tokens_used > 0 and limits.llm_calls_today >= 1  # los assets de prueba pesan bytes: se redondean a 0 MB


# --- Evaluar una idea propia ---
def _idea_llm(verdict: dict):
    from app.core.types import LLMResponse

    class LLM:
        async def complete(self, messages, *, json_mode=False, max_tokens=1200):
            return LLMResponse(json.dumps(verdict), "fake", "m", 10)

    return LLM()


def test_idea_viable_is_queued_and_unviable_is_not():
    from app.services.ideas import IdeaService

    ok_verdict = {"viable": True, "score": 82, "reason": "Buena", "risks": [], "title": "Mi idea (Parte 1)", "improvement": ""}

    async def scenario():
        async with rig() as r:
            async with r.sf() as s:
                good = await IdeaService(s, _idea_llm(ok_verdict)).evaluate(r.pid, "Una pareja descubre un secreto de familia")
            async with r.sf() as s:
                bad = await IdeaService(s, _idea_llm({**ok_verdict, "viable": False, "score": 10})).evaluate(r.pid, "Otra idea distinta aquí")
            async with r.sf() as s:  # score bajo: el modelo dice viable pero no pasa el umbral
                low = await IdeaService(s, _idea_llm({**ok_verdict, "score": 30})).evaluate(r.pid, "Tercera idea diferente aquí")
            return good, bad, low, await r.contents()

    good, bad, low, contents = run(scenario())
    assert good["mode"] == "idea" and good["viable"] and good["content_id"] and not bad["viable"] and bad["content_id"] is None and not low["viable"]
    assert [c.status for c in contents] == ["idea"] and contents[0].title == "Mi idea (Parte 1)"


# --- Series (parte 2) ---
def test_next_part_links_the_series_and_gives_the_pipeline_the_previous_script():
    from app.core.errors import Conflict

    async def scenario():
        async with rig() as r:
            await r.batch()
            (parent,) = await r.contents()
            async with r.sf() as s:
                svc = ContentService(s)
                child = await svc.next_part(parent.id)
                with pytest.raises(Conflict):  # una sola continuación por parte
                    await svc.next_part(parent.id)
            async with r.sf() as s:
                series = await ContentService(s).series(child.id)
            job = await r.agents.storage.load_job(child.id)
            return parent, child, series, job

    parent, child, series, job = run(scenario())
    assert (child.part, child.parent_id, child.status) == (2, parent.id, "idea")
    assert [(p["part"], p["status"]) for p in series] == [(1, "generado"), (2, "idea")]
    assert job.part == 2 and job.previous.startswith("PARTE 1") and "Segunda frase del guion" in job.previous


def test_next_part_requires_a_generated_content():
    from app.core.errors import Conflict

    async def scenario():
        async with rig() as r:
            async with r.sf() as s:
                idea = Content(project_id=r.pid)
                s.add(idea)
                await s.commit()
            async with r.sf() as s:
                with pytest.raises(Conflict):
                    await ContentService(s).next_part(idea.id)

    run(scenario())


def test_topics_list_sorts_by_score_and_hides_pasted_ideas():
    from app.services.ideas import IdeaService
    from app.services.topics import TopicService

    verdict = {"viable": True, "score": 80, "reason": "ok", "risks": [], "title": "T", "improvement": "",
               "hook": "h", "caption": "c", "hashtags": ["x"]}

    async def scenario():
        async with rig() as r:
            async with r.sf() as s:
                s.add_all([Topic(project_id=r.pid, topic="bajo", source="reddit", score=10),
                           Topic(project_id=r.pid, topic="alto", source="google_trends", score=90),
                           Topic(project_id=r.pid, topic="medio", source="wikipedia", score=50)])
                await s.commit()
            async with r.sf() as s:
                await IdeaService(s, _idea_llm(verdict)).evaluate(r.pid, "Una idea que pego yo mismo en Mi idea")
            async with r.sf() as s:
                by_score = [t.topic for t in await TopicService(s).list(r.pid, 50, 0, "score", 7)]
            job = await r.agents.storage.load_job((await r.contents())[0].id)
            return by_score, job

    by_score, job = run(scenario())
    assert by_score == ["alto", "medio", "bajo"]  # la idea pegada no aparece
    assert job.instructions is True


def test_idea_with_a_ready_screenplay_skips_the_llm_script_and_goes_straight_to_media():
    from app.services.ideas import IdeaService

    script = "PERSONAJES\nANA | f | young woman, red hair\nESCENA | Ana in a kitchen, medium shot\nANA: Hola.\nANA: ¿Me oyes?\nESCENA | Ana outside, medium shot\nANA: Adiós.\nANA: Hasta luego."
    verdict = {"viable": True, "score": 77, "reason": "ok", "risks": [], "title": "Mi guion", "improvement": "",
               "hook": "Hola.", "caption": "Una pregunta", "hashtags": ["novela", "#drama"]}

    async def scenario():
        async with rig() as r:
            async with r.sf() as s:
                out = await IdeaService(s, _idea_llm(verdict)).evaluate(r.pid, script)
            (content,) = await r.contents()
            return out, content

    out, content = run(scenario())
    assert out["mode"] == "guion" and "hook" not in out
    assert (content.status, content.script, content.hashtags, content.topic_id) == ("guion", script, ["#novela", "#drama"], None)


def test_topics_can_be_deleted_and_unused_ones_cleared_in_bulk():
    from app.core.errors import NotFound
    from app.services.topics import TopicService

    async def scenario():
        async with rig() as r:
            async with r.sf() as s:
                keep, drop, mine = (Topic(project_id=r.pid, topic=t, source=src, score=1, summary="resumen")
                                    for t, src in (("usado", "reddit"), ("sin usar", "reddit"), ("idea mia", "idea")))
                s.add_all([keep, drop, mine])
                await s.flush()
                s.add(Content(project_id=r.pid, topic_id=keep.id))
                await s.commit()
            async with r.sf() as s:
                svc = TopicService(s)
                listed = {t.topic: t.used for t in await svc.list(r.pid, 50, 0)}
                removed = await svc.clear_unused(r.pid)
            async with r.sf() as s:
                remaining = {t.topic for t in (await s.scalars(select(Topic).where(Topic.project_id == r.pid))).all()}
                await TopicService(s).delete(keep.id)
            async with r.sf() as s:
                with pytest.raises(NotFound):
                    await TopicService(s).delete(keep.id)
                content = (await s.scalars(select(Content).where(Content.project_id == r.pid))).one()
            return listed, removed, remaining, content

    listed, removed, remaining, content = run(scenario())
    assert listed == {"usado": True, "sin usar": False}  # la idea del usuario no se lista
    assert removed == 1 and remaining == {"usado", "idea mia"}
    assert content.topic_id is None  # el contenido sobrevive al borrado del tema
