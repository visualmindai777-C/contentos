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
