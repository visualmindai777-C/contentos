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


def test_r2_operations(tmp_path):
    s3 = FakeS3()
    store = R2Storage("a", "b", "c", "bucket", client=s3)
    video = tmp_path / "v.mp4"
    video.write_bytes(b"12345")
    assert run(store.put_bytes("c/1/caption.txt", b"hola", "text/plain")).file_size == 4
    assert run(store.put_file("c/1/video.mp4", video, "video/mp4")).file_size == 5
    run(store.delete("c/1/caption.txt"))
    assert [c[0] for c in s3.calls] == ["put_object", "upload_file", "delete_object"]


# --- FFmpeg (real) ---
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg no instalado")
def test_ffmpeg_renders_vertical_video(tmp_path):
    def ff(*args):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)

    images = []
    for i, color in enumerate(("red", "blue")):
        path = tmp_path / f"i{i}.png"
        ff("-f", "lavfi", "-i", f"color=c={color}:s=540x960", "-frames:v", "1", str(path))
        images.append(path)
    audio = tmp_path / "a.wav"
    ff("-f", "lavfi", "-i", "sine=frequency=440:duration=3", str(audio))

    segments = [Segment("Hola mundo esto es una prueba de subtitulos largos", 0, 3)]
    video = run(FFmpegVideo().render(VideoSpec(images, audio, segments, tmp_path / "out" / "video.mp4", crop_bottom=0.05)))
    assert video.path.exists() and video.file_size > 0 and abs(video.duration - 3) < 0.3


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
