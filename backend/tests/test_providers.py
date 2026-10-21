import asyncio
import json
import shutil
import subprocess
import uuid
from pathlib import Path

import httpx
import pytest

from app.container import build_providers
from app.core.interfaces import ProviderError, RateLimitError
from app.core.settings import Settings
from app.core.subtitles import chunk_segments, to_srt
from app.core.types import Message, ProjectContext, Segment, VideoSpec
from app.providers.image_pollinations import PollinationsProvider
from app.providers.llm_openrouter import OpenRouterClient, missing_models
from app.providers.storage_r2 import R2Storage
from app.providers.trends.google import GoogleTrendsSource
from app.providers.trends.hackernews import HackerNewsSource
from app.providers.trends.reddit import RedditSource
from app.providers.trends.wikipedia import WikipediaSource
from app.providers.video_ffmpeg import FFmpegVideo

run = asyncio.run
MSG = [Message("user", "hola")]
PROJECT = ProjectContext(uuid.uuid4(), "P", "ia", "es", {"subreddits": ["technology", "futurology"]})


def transport(handler):
    return httpx.MockTransport(handler)


def completion(text="ok", tokens=42):
    return {"choices": [{"message": {"content": text}}], "usage": {"total_tokens": tokens}}


# --- OpenRouter ---
def test_openrouter_falls_back_to_next_model():
    seen = []

    def handler(req):
        model = json.loads(req.content)["model"]
        seen.append(model)
        return httpx.Response(429, headers={"retry-after": "3"}) if model == "m1" else httpx.Response(200, json=completion())

    r = run(OpenRouterClient("k", ["m1", "m2"], transport=transport(handler)).complete(MSG))
    assert (r.model, r.tokens_used, r.provider, seen) == ("m2", 42, "openrouter", ["m1", "m2"])


def test_openrouter_logs_why_each_model_failed(caplog):
    def handler(req):
        model = json.loads(req.content)["model"]
        return httpx.Response(404, text="model not found") if model == "dead" else httpx.Response(200, json=completion())

    with caplog.at_level("WARNING", logger="app.pipeline"):
        run(OpenRouterClient("k", ["dead", "alive"], transport=transport(handler)).complete(MSG))
    failed = [r for r in caplog.records if r.getMessage() == "openrouter model failed"]
    assert len(failed) == 1 and failed[0].fields["model"] == "dead" and "404" in failed[0].fields["error"]


def test_openrouter_empty_reply_reports_finish_reason_and_asks_for_low_reasoning():
    captured = {}

    def handler(req):
        captured.update(json.loads(req.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": None}, "finish_reason": "length"}]})

    with pytest.raises(ProviderError, match="finish_reason=length.*max_tokens") as exc:
        run(OpenRouterClient("k", ["m1"], transport=transport(handler)).complete(MSG, max_tokens=4000))
    assert not isinstance(exc.value, RateLimitError)
    assert captured["reasoning"] == {"effort": "low"} and captured["max_tokens"] == 4000


def test_openrouter_transient_limit_wins_over_other_failures():
    def handler(req):
        return httpx.Response(429) if json.loads(req.content)["model"] == "m1" else httpx.Response(200, json=completion(""))

    with pytest.raises(RateLimitError):  # m1 limitado + m2 vacío → transitorio, no es culpa del contenido
        run(OpenRouterClient("k", ["m1", "m2"], transport=transport(handler)).complete(MSG))


def test_openrouter_all_models_rate_limited():
    client = OpenRouterClient("k", ["m1", "m2"], transport=transport(lambda r: httpx.Response(429)))
    with pytest.raises(RateLimitError):
        run(client.complete(MSG))


def test_openrouter_error_inside_200_body():
    body = {"error": {"code": 429, "message": "free quota"}}
    with pytest.raises(RateLimitError):
        run(OpenRouterClient("k", ["m1"], transport=transport(lambda r: httpx.Response(200, json=body))).complete(MSG))


def test_openrouter_json_mode_and_auth_header():
    captured = {}

    def handler(req):
        captured.update(json.loads(req.content), auth=req.headers["authorization"])
        return httpx.Response(200, json=completion("{}"))

    run(OpenRouterClient("secret", ["m1"], transport=transport(handler)).complete(MSG, json_mode=True))
    assert captured["response_format"] == {"type": "json_object"} and captured["auth"] == "Bearer secret"


def test_missing_models_reports_ids_gone_from_the_catalog():
    catalog = {"data": [{"id": "google/gemma-4-31b-it:free"}, {"id": "openrouter/free"}]}
    handler = lambda r: httpx.Response(200, json=catalog)
    ids = ["google/gemma-4-31b-it:free", "qwen/qwen3-235b-a22b:free", "openrouter/free"]
    assert run(missing_models(ids, transport=transport(handler))) == ["qwen/qwen3-235b-a22b:free"]
    with pytest.raises(ProviderError):
        run(missing_models(ids, transport=transport(lambda r: httpx.Response(200, json={"x": 1}))))


# --- Pollinations ---
def test_pollinations_returns_image():
    h = lambda r: httpx.Response(200, content=b"\xff\xd8jpg", headers={"content-type": "image/jpeg"})
    img = run(PollinationsProvider(transport=transport(h)).generate("un gato", width=540, height=960, seed=1))
    assert img.mime_type == "image/jpeg" and img.data.startswith(b"\xff\xd8")


def test_pollinations_429_and_non_image():
    with pytest.raises(RateLimitError) as exc:
        run(PollinationsProvider(transport=transport(lambda r: httpx.Response(429, headers={"retry-after": "7"}))).generate("x"))
    assert exc.value.retry_after == 45.0  # mínimo de la ventana anónima aunque el servidor diga 7
    free_limit = {"status": 402, "error": {"code": "FREE_LIMIT", "message": "Free limit reached. Retry after 38s, or get a key"}}
    with pytest.raises(RateLimitError) as exc:
        run(PollinationsProvider(transport=transport(lambda r: httpx.Response(402, json=free_limit))).generate("x"))
    assert exc.value.retry_after == 45.0
    with pytest.raises(RateLimitError) as exc:  # con clave se respeta lo que diga el servidor
        run(PollinationsProvider("key", transport=transport(lambda r: httpx.Response(402, json=free_limit))).generate("x"))
    assert exc.value.retry_after == 38.0
    html = lambda r: httpx.Response(200, text="<html>", headers={"content-type": "text/html"})
    with pytest.raises(ProviderError):
        run(PollinationsProvider(transport=transport(html)).generate("x"))


# --- Tendencias ---
GOOGLE_RSS = """<?xml version="1.0"?>
<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0"><channel>
<item><title>modelo nuevo</title><ht:approx_traffic>200+</ht:approx_traffic>
<ht:news_item><ht:news_item_title>Lanzan un modelo de inteligencia artificial</ht:news_item_title></ht:news_item></item>
<item><title>liga final</title><ht:approx_traffic>500K+</ht:approx_traffic></item>
</channel></rss>"""


def test_google_trends_parses_and_ranks():
    out = run(GoogleTrendsSource(transport=transport(lambda r: httpx.Response(200, text=GOOGLE_RSS))).fetch(PROJECT, 5))
    assert [t.topic for t in out] == ["liga final", "modelo nuevo"]
    assert out[0].score > out[1].score and "inteligencia" in out[1].keywords and out[0].source == "google_trends"


ATOM = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Primero</title></entry><entry><title>Segundo</title></entry></feed>"""


def test_reddit_ranks_by_position_and_tolerates_failing_sub():
    def handler(req):
        return httpx.Response(200, text=ATOM) if "/r/technology/" in str(req.url) else httpx.Response(500)

    out = run(RedditSource(transport=transport(handler)).fetch(PROJECT, 5))
    assert [(t.topic, t.score) for t in out] == [("Primero", 100.0), ("Segundo", 50.0)]


def test_reddit_all_failing_raises_and_no_subs_is_empty():
    with pytest.raises(ProviderError):
        run(RedditSource(transport=transport(lambda r: httpx.Response(403))).fetch(PROJECT, 5))
    empty = ProjectContext(uuid.uuid4(), "P", "ia", "es", {})
    assert run(RedditSource(transport=transport(lambda r: httpx.Response(500))).fetch(empty, 5)) == []


def test_wikipedia_skips_special_pages():
    body = {"items": [{"articles": [
        {"article": "Portada", "views": 900000}, {"article": "Especial:Buscar", "views": 800000},
        {"article": "Inteligencia_artificial", "views": 50000},
    ]}]}
    out = run(WikipediaSource(transport=transport(lambda r: httpx.Response(200, json=body))).fetch(PROJECT, 5))
    assert [t.topic for t in out] == ["Inteligencia artificial"]


# --- Subtítulos ---
def test_subtitles_chunking_and_srt():
    chunks = chunk_segments([Segment("uno dos tres cuatro cinco seis siete ocho", 0.0, 4.0)], max_words=4)
    assert [c.text for c in chunks] == ["uno dos tres cuatro", "cinco seis siete ocho"]
    assert chunks[0].start == 0.0 and chunks[-1].end == pytest.approx(4.0)
    assert to_srt(chunks[:1]).startswith("1\n00:00:00,000 --> 00:00:0")


# --- R2 ---
class FakeS3:
    def __init__(self):
        self.calls = []

    def put_object(self, **kw): self.calls.append(("put_object", kw["Key"], kw["ContentType"]))
    def upload_file(self, path, bucket, key, **kw): self.calls.append(("upload_file", key, kw["ExtraArgs"]["ContentType"]))
    def delete_object(self, **kw): self.calls.append(("delete_object", kw["Key"]))

    def get_object(self, **kw):
        import io
        return {"Body": io.BytesIO(b"datos")}


def test_r2_operations(tmp_path):
    s3 = FakeS3()
    store = R2Storage("a", "b", "c", "bucket", client=s3)
    video = tmp_path / "v.mp4"
    video.write_bytes(b"12345")
    assert run(store.put_bytes("c/1/caption.txt", b"hola", "text/plain")).file_size == 4
    assert run(store.put_file("c/1/video.mp4", video, "video/mp4")).file_size == 5
    assert run(store.get_bytes("c/1/caption.txt")) == b"datos"
    run(store.delete("c/1/caption.txt"))
    assert [c[0] for c in s3.calls] == ["put_object", "upload_file", "delete_object"]


# --- FFmpeg (real) ---
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg no instalado")
def test_ffmpeg_renders_vertical_video(tmp_path):
    def ff(*args):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)

    images = []
    for i, color in enumerate(("red", "blue", "green", "yellow")):  # una imagen por cada movimiento de cámara
        path = tmp_path / f"i{i}.png"
        ff("-f", "lavfi", "-i", f"color=c={color}:s=540x960", "-frames:v", "1", str(path))
        images.append(path)
    audio = tmp_path / "a.wav"
    ff("-f", "lavfi", "-i", "sine=frequency=440:duration=3", str(audio))

    segments = [Segment("Hola mundo esto es una prueba de subtitulos largos", 0, 3)]
    video = run(FFmpegVideo().render(VideoSpec(images, audio, segments, tmp_path / "out" / "video.mp4", crop_bottom=0.05)))
    assert video.path.exists() and video.file_size > 0 and abs(video.duration - 3) < 0.3

    from app.agents.media_agent import BRAND_DIR

    branded = run(FFmpegVideo().render(VideoSpec(
        images, audio, segments, tmp_path / "brand" / "video.mp4", crop_bottom=0.05,
        watermark=BRAND_DIR / "watermark.png", outro=BRAND_DIR / "outro.png", outro_seconds=1.5,
    )))
    assert abs(branded.duration - 4.5) < 0.3  # 3 s de narración + 1,5 s de tarjeta final


# --- Container ---
def settings(**kw):
    base = dict(database_url="postgresql+asyncpg://x", openrouter_api_key="k", r2_account_id="a",
                r2_access_key_id="b", r2_secret_access_key="c", openrouter_models="m1,m2")
    return Settings(**{**base, **kw})


def test_container_wires_all_contracts():
    providers = build_providers(settings())
    assert [t.name for t in providers.trends] == ["google_trends", "reddit", "wikipedia"]


def test_container_requires_credentials():
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        build_providers(settings(openrouter_api_key=""))


# --- Descubrimiento de tendencias a demanda ---
def test_discovery_modes_widen_or_keep_the_project_scope():
    from types import SimpleNamespace

    from app.services.discovery import SUBREDDITS, context_for

    project = SimpleNamespace(id=uuid.uuid4(), name="P", niche="ia", language="es", config={"subreddits": ["technology"], "keywords": ["gpt"]})
    assert context_for(project, "nicho").config["subreddits"] == ["technology"]
    viral = context_for(project, "viral")
    assert viral.niche == "" and viral.config["subreddits"] == SUBREDDITS["viral"] and viral.config["keywords"] == []
    assert context_for(project, "monetizable").config["subreddits"] == SUBREDDITS["monetizable"]
    assert project.config["subreddits"] == ["technology"]  # el proyecto original no se modifica


def test_hackernews_front_page_scores_by_points():
    body = {"hits": [{"title": "Stripe raises prices", "points": 900}, {"title": "Show HN: tiny", "points": 12}, {"title": None, "points": 5}]}
    out = run(HackerNewsSource(transport=transport(lambda r: httpx.Response(200, json=body))).fetch(PROJECT, 5))
    assert [t.topic for t in out] == ["Stripe raises prices", "Show HN: tiny"]
    assert out[0].score > out[1].score and out[0].source == "hackernews"


# --- Mini novela ---
NOVELA = """PERSONAJES
LUCÍA | f | young woman, short red hair, turquoise t-shirt
MARCOS | m | bearded man, gray shirt
ESCENA | Lucía in a cozy kitchen at night, shocked face, medium shot
LUCÍA: ¿Me mentiste todo este tiempo?
MARCOS (nervioso): Puedo explicarlo, te lo juro.
ESCENA | Marcos on the balcony, guilty face, medium shot
NARRADOR: Esa noche, todo cambió.
MARCOS: No era quien creías.
"""


def test_screenplay_parses_characters_scenes_and_speakers():
    from app.core.screenplay import parse_screenplay

    play = parse_screenplay(NOVELA)
    assert play is not None and set(play.characters) == {"LUCÍA", "MARCOS"} and play.characters["MARCOS"].gender == "m"
    assert [len(s.lines) for s in play.scenes] == [2, 2]
    assert [l.speaker for l in play.lines] == ["LUCÍA", "MARCOS", "NARRADOR", "MARCOS"]
    assert parse_screenplay("Un guion normal sin formato de novela. " * 10) is None


def _wav(seconds: float) -> bytes:
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(24_000)
        w.writeframes(b"\x00\x00" * int(24_000 * seconds))
    return buf.getvalue()


def test_join_wavs_adds_gaps_and_reports_start_times():
    from app.core.audio import join_wavs, wav_seconds

    data, starts = join_wavs([_wav(1.0), _wav(2.0), _wav(0.5)], gap=0.25)
    assert starts == pytest.approx([0.0, 1.25, 3.5]) and wav_seconds(data) == pytest.approx(4.0)


def test_novela_uses_a_voice_per_character_one_image_per_scene_and_scene_durations(tmp_path):
    from app.agents.media_agent import MediaAgent
    from app.core.types import ContentDraft, GeneratedImage, Narration, RenderedVideo

    voices, prompts, specs = [], [], []

    class TTS:
        async def synthesize(self, text, *, voice, lang):
            voices.append(voice)
            return Narration(_wav(1.0), "audio/wav", 1.0, [Segment(text, 0.0, 1.0)])

    class Images:
        async def generate(self, prompt, *, width, height, seed):
            prompts.append(prompt)
            return GeneratedImage(b"\xff\xd8jpg", "image/jpeg")

    class Video:
        async def render(self, spec):
            specs.append(spec)
            return RenderedVideo(spec.output, 5.0, 1)

    project = ProjectContext(uuid.uuid4(), "N", "general", "es", {"format": "novela"})
    draft = ContentDraft("T (Parte 1)", "h", NOVELA, "c", ["#a"], "cta")
    bundle = run(MediaAgent(TTS(), Images(), Video(), voice="ef_dora", lang="e").run(project, "tema", draft, tmp_path))

    assert voices == ["ef_dora", "em_alex", "em_alex", "em_alex"]  # Lucía f, Marcos m, narrador y Marcos
    assert len(prompts) == 2 and "red hair" in prompts[0] and "Pixar" in prompts[0] and "bearded" in prompts[1]
    spec = specs[0]
    assert len(spec.images) == 2 and spec.durations == pytest.approx([2.6, 2.3])  # la pausa entre escenas se suma a la anterior and bundle.subtitles.startswith("1\n")


def test_novela_next_part_prompt_carries_the_story_so_far_and_closes_on_the_last_part():
    from app.agents.content_agent import ContentAgent
    from app.core.types import LLMResponse

    seen = []
    reply = json.dumps({"title": "T (Parte 2)", "hook": "h", "script": NOVELA + " " + "palabra " * 30, "caption": "c", "hashtags": ["#a"], "cta": "x"})

    class LLM:
        async def complete(self, messages, *, json_mode=False, max_tokens=1200):
            seen.append(messages[-1].content)
            return LLMResponse(reply, "fake", "m", 5)

    project = ProjectContext(uuid.uuid4(), "N", "general", "es", {"format": "novela", "series_parts": 3})
    agent = ContentAgent(LLM())
    run(agent.run(project, "tema", [], previous="PARTE 1 — Titulo\nLUCÍA: hola", part=2))
    run(agent.run(project, "tema", [], previous="PARTE 1 — Titulo\nLUCÍA: hola", part=3))
    assert "PARTE 1" in seen[0] and "(Parte 2)" in seen[0] and "cliffhanger" in seen[0]
    assert "(Parte 3)" in seen[1] and "última parte" in seen[1]


def test_user_instructions_are_prepended_with_priority():
    from app.agents.content_agent import ContentAgent
    from app.core.types import LLMResponse

    seen = []
    reply = json.dumps({"title": "T", "hook": "h", "script": "palabra " * 40, "caption": "c", "hashtags": ["#a"], "cta": "x"})

    class LLM:
        async def complete(self, messages, *, json_mode=False, max_tokens=1200):
            seen.append(messages[-1].content)
            return LLMResponse(reply, "fake", "m", 5)

    project = ProjectContext(uuid.uuid4(), "N", "general", "es", {})
    run(ContentAgent(LLM()).run(project, "Haz esto EXACTO: A, luego B", [], instructions=True))
    assert seen[0].startswith("INSTRUCCIONES DEL USUARIO") and "Haz esto EXACTO: A, luego B" in seen[0]


def test_sources_give_a_short_summary():
    from app.providers.trends.hackernews import HackerNewsSource

    rss = """<?xml version="1.0"?><rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0"><channel>
<item><title>modelo nuevo</title><ht:approx_traffic>200K+</ht:approx_traffic>
<ht:news_item><ht:news_item_title>Lanzan un modelo</ht:news_item_title><ht:news_item_snippet>Promete mejorar la traducción.</ht:news_item_snippet></ht:news_item></item></channel></rss>"""
    (g,) = run(GoogleTrendsSource(transport=transport(lambda r: httpx.Response(200, text=rss))).fetch(PROJECT, 5))
    assert g.summary == "Lanzan un modelo. Promete mejorar la traducción. (200K+ búsquedas)"

    atom = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Con texto</title><content type="html">&lt;p&gt;Mi suegra descubrió que llevo meses ahorrando en secreto para irme.&lt;/p&gt; submitted by /u/x [link] [comments]</content></entry>
<entry><title>Solo enlace</title><content type="html">&lt;a&gt;submitted by /u/y&lt;/a&gt; [link] [comments]</content></entry></feed>"""
    posts = run(RedditSource(transport=transport(lambda r: httpx.Response(200, text=atom))).fetch(
        ProjectContext(uuid.uuid4(), "P", "ia", "es", {"subreddits": ["relationships"]}), 5))
    assert posts[0].summary.startswith("Mi suegra descubrió") and posts[0].summary.endswith("(r/relationships)")
    assert posts[1].summary == "Entre lo más votado hoy en r/relationships"

    hn = {"hits": [{"title": "Stripe sube precios", "points": 120, "num_comments": 45, "url": "https://www.stripe.com/blog"}]}
    (h,) = run(HackerNewsSource(transport=transport(lambda r: httpx.Response(200, json=hn))).fetch(PROJECT, 5))
    assert h.summary == "120 puntos y 45 comentarios en Hacker News · stripe.com"

    def wiki(req):
        if "rest_v1/page/summary" in str(req.url):
            return httpx.Response(200, json={"extract": "Es un actor mexicano. " * 20})
        return httpx.Response(200, json={"items": [{"articles": [{"article": "Actor_X", "views": 90000}]}]})

    (w,) = run(WikipediaSource(transport=transport(wiki)).fetch(PROJECT, 5))
    assert w.summary.startswith("Es un actor mexicano.") and w.summary.endswith("…") and len(w.summary) <= 262


# --- Sesgos: términos vetados y no repetirse ---
def test_banned_terms_match_whole_words_ignoring_case_accents_and_punctuation():
    from app.core.blocklist import banned_terms, find_banned

    terms = banned_terms({"banned_terms": ["Hacienda Falsa"]})
    assert find_banned("Un hacker al estilo de MR. ROBOT", terms) == "mr robot"
    assert find_banned("La serie Mr Robot es genial", terms) == "mr robot"
    assert find_banned("Visitó la hacienda  falsa", terms) == "Hacienda Falsa"
    assert find_banned("Un robot amable ayuda a la señora Roberta", terms) is None


def test_trends_and_drafts_that_mention_banned_terms_are_dropped_or_retried():
    from app.agents.content_agent import ContentAgent
    from app.agents.trend_agent import TrendAgent
    from app.core.types import LLMResponse, TrendCandidate

    class Source:
        name = "fake"

        async def fetch(self, project, limit):
            return [TrendCandidate("Final de Mr. Robot explicado", 90, [], "fake"), TrendCandidate("Receta de pan", 50, [], "fake")]

    topics = run(TrendAgent([Source()]).discover(ProjectContext(uuid.uuid4(), "P", "x", "es", {})))
    assert [t.topic for t in topics] == ["Receta de pan"]

    bad = json.dumps({"title": "Un hacker como Mr. Robot", "hook": "h", "script": "palabra " * 40, "caption": "c", "hashtags": ["#a"], "cta": "x"})
    good = json.dumps({"title": "Una panadera valiente", "hook": "h", "script": "palabra " * 40, "caption": "c", "hashtags": ["#a"], "cta": "x"})
    replies, prompts = [bad, good], []

    class LLM:
        async def complete(self, messages, *, json_mode=False, max_tokens=1200):
            prompts.append(messages[-1].content)
            return LLMResponse(replies.pop(0), "fake", "m", 5)

    draft, _ = run(ContentAgent(LLM()).run(ProjectContext(uuid.uuid4(), "P", "x", "es", {}), "pan", [], recent=("Mi suegra y el testamento",)))
    assert draft.title == "Una panadera valiente" and len(prompts) == 2
    assert "Mr. Robot" in prompts[0] and "NO repitas" in prompts[0] and "Mi suegra y el testamento" in prompts[0]


def test_media_agent_reuses_existing_images_and_only_generates_the_missing_ones(tmp_path):
    from app.agents.media_agent import MediaAgent
    from app.core.types import ContentDraft, GeneratedImage, Narration, RenderedVideo

    prompts, specs = [], []

    class TTS:
        async def synthesize(self, text, *, voice, lang):
            return Narration(_wav(1.0), "audio/wav", 1.0, [Segment(text, 0.0, 1.0)])

    class Images:
        async def generate(self, prompt, *, width, height, seed):
            prompts.append(prompt)
            return GeneratedImage(b"\xff\xd8nueva", "image/jpeg")

    class Video:
        async def render(self, spec):
            specs.append(spec)
            return RenderedVideo(spec.output, 5.0, 1)

    project = ProjectContext(uuid.uuid4(), "N", "general", "es", {"format": "novela"})
    draft = ContentDraft("T", "h", NOVELA, "c", ["#a"], "cta")  # 2 escenas
    run(MediaAgent(TTS(), Images(), Video(), voice="ef_dora", lang="e").run(
        project, "tema", draft, tmp_path, existing_images=[b"\xff\xd8vieja"]))
    assert len(prompts) == 1 and "bearded" in prompts[0]  # solo la escena 2 se pidió de nuevo
    assert specs[0].images[0].read_bytes() == b"\xff\xd8vieja" and specs[0].images[1].read_bytes() == b"\xff\xd8nueva"


# --- Paralaje 3D (código abierto, sin servicios) ---
def _ffprobe_seconds(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg no instalado")
def test_parallax_clip_has_the_scene_duration_and_feeds_the_final_render(tmp_path):
    pytest.importorskip("cv2")
    import numpy as np

    from app.providers.motion_parallax import render_parallax

    sample = Path(__file__).parent / "assets" / "sample_a.jpg"
    depth = np.tile(np.linspace(0, 1, 64, dtype=np.float32), (64, 1))  # profundidad sintética: sin descargar el modelo
    clip = tmp_path / "clip.mp4"
    render_parallax(sample, depth, clip, seconds=1.0, index=0, fps=10, width=270, height=480)
    assert _ffprobe_seconds(clip) == pytest.approx(1.0, abs=0.2)

    audio = tmp_path / "a.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", str(audio)], check=True)
    big = tmp_path / "clip_big.mp4"
    render_parallax(sample, depth, big, seconds=2.4, index=1, fps=30)  # tamaño real 1080x1920
    video = run(FFmpegVideo().render(VideoSpec(
        [sample, sample], audio, [Segment("hola", 0, 2)], tmp_path / "o" / "v.mp4", durations=[1.0, 1.0], clips=[big, None],
    )))
    assert video.duration == pytest.approx(2.0, abs=0.3)


def test_media_agent_uses_parallax_clips_and_falls_back_to_zoom_when_a_scene_fails(tmp_path):
    from app.agents.media_agent import MediaAgent
    from app.core.types import ContentDraft, GeneratedImage, Narration, RenderedVideo

    specs, asked = [], []

    class TTS:
        async def synthesize(self, text, *, voice, lang):
            return Narration(_wav(1.0), "audio/wav", 1.0, [Segment(text, 0.0, 1.0)])

    class Images:
        async def generate(self, prompt, *, width, height, seed):
            return GeneratedImage(b"\xff\xd8jpg", "image/jpeg")

    class Video:
        async def render(self, spec):
            specs.append(spec)
            return RenderedVideo(spec.output, 5.0, 1)

    class Motion:
        async def animate(self, image, output, *, seconds, index):
            asked.append((index, round(seconds, 1)))
            if index == 1:
                raise ProviderError("sin memoria")
            return output

    draft = ContentDraft("T", "h", NOVELA, "c", ["#a"], "cta")
    agent = MediaAgent(TTS(), Images(), Video(), voice="ef_dora", lang="e", motion=Motion())
    off = ProjectContext(uuid.uuid4(), "N", "general", "es", {"format": "novela"})
    run(agent.run(off, "tema", draft, tmp_path))
    assert asked == [] and specs[-1].clips is None  # sin "motion": solo zoom

    on = ProjectContext(uuid.uuid4(), "N", "general", "es", {"format": "novela", "motion": "parallax"})
    run(agent.run(on, "tema", draft, tmp_path))
    assert [i for i, _ in asked] == [0, 1] and specs[-1].clips[0] is not None and specs[-1].clips[1] is None
