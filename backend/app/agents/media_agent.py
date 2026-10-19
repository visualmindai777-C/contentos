import asyncio
import logging
import mimetypes
import re
from collections.abc import Awaitable, Callable
from pathlib import Path

from app.core.interfaces import ImageProvider, ProviderError, RateLimitError, TTSProvider, VideoProvider
from app.core.subtitles import chunk_segments, to_srt
from app.core.types import ContentDraft, GeneratedImage, MediaBundle, ProjectContext, VideoSpec

logger = logging.getLogger("app.pipeline")

IMAGE_SIZE = (768, 1024)  # el vídeo sale en 1080x1920; a esta resolución Pollinations va más rápido
MIN_IMAGES = 2
DEFAULT_CROP_BOTTOM = 0.05  # Pollinations anónimo estampa su logo en el ~3 % inferior; nologo=true se ignora sin clave
DEFAULT_WAIT = 45.0  # Pollinations anónimo: 1 imagen cada ~45 s por IP
TRANSIENT_WAIT = 5.0  # timeouts y errores de red del proveedor
MAX_WAIT = 120.0
DEFAULT_STYLE = "cinematic digital illustration, dramatic lighting, highly detailed, natural proportions, no text, no watermark"

_EMOJI = re.compile("[\U0001f300-\U0001faff☀-➿️]")
_MARKUP = re.compile(r"[#*_`~<>]")
_SENTENCES = re.compile(r"(?<=[.!?…])\s+")


def clean_for_speech(script: str) -> str:
    return re.sub(r"\s+", " ", _MARKUP.sub("", _EMOJI.sub("", script))).strip()


def scene_prompts(script: str, topic: str, count: int, style: str) -> list[str]:
    """Una escena por tramo del guion. El LLM devuelve solo los seis campos aprobados, así que las escenas salen del texto."""
    sentences = [s for s in _SENTENCES.split(clean_for_speech(script)) if s]
    n = len(sentences)
    count = max(1, min(count, n))
    chunks = [" ".join(sentences[i * n // count : (i + 1) * n // count]) for i in range(count)]
    return [f"{style}. Tema: {topic}. Escena: {chunk[:220]}" for chunk in chunks]


class MediaAgent:
    """Narración, imágenes, subtítulos y vídeo. La voz (CPU) y las imágenes (espera de red) se solapan."""

    def __init__(
        self, tts: TTSProvider, images: ImageProvider, video: VideoProvider, *, voice: str, lang: str,
        retries: int = 3, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self._tts, self._images, self._video = tts, images, video
        self._voice, self._lang = voice, lang
        self._retries = retries
        self._sleep = sleep

    async def run(self, project: ProjectContext, topic: str, draft: ContentDraft, workdir: Path) -> MediaBundle:
        cfg = project.config
        narration, images = await asyncio.gather(
            self._tts.synthesize(
                clean_for_speech(draft.script), voice=cfg.get("tts_voice", self._voice), lang=cfg.get("tts_lang", self._lang)
            ),
            self._generate_all(scene_prompts(draft.script, topic, int(cfg.get("images_per_video", 4)), cfg.get("image_style", DEFAULT_STYLE))),
        )
        audio = workdir / "audio.wav"
        audio.write_bytes(narration.audio)
        paths = []
        for i, image in enumerate(images):
            path = workdir / f"img_{i}{mimetypes.guess_extension(image.mime_type) or '.jpg'}"
            path.write_bytes(image.data)
            paths.append(path)

        video = await self._video.render(VideoSpec(
            images=paths, audio=audio, segments=narration.segments, output=workdir / "video.mp4",
            crop_bottom=float(cfg.get("image_crop_bottom", DEFAULT_CROP_BOTTOM)),
        ))
        return MediaBundle(video=video, images=paths, subtitles=to_srt(chunk_segments(narration.segments)))

    async def _generate_all(self, prompts: list[str]) -> list[GeneratedImage]:
        images = []
        for seed, prompt in enumerate(prompts):  # en serie: el proveedor gratuito solo admite una a la vez
            if image := await self._generate(prompt, seed):
                images.append(image)
        if len(images) < MIN_IMAGES:
            raise ProviderError(f"solo se generaron {len(images)} de {len(prompts)} imágenes")
        return images

    async def _generate(self, prompt: str, seed: int) -> GeneratedImage | None:
        for attempt in range(self._retries + 1):
            try:
                return await self._images.generate(prompt, width=IMAGE_SIZE[0], height=IMAGE_SIZE[1], seed=seed)
            except ProviderError as e:  # incluye RateLimitError; una imagen que no sale se omite y el vídeo usa las demás
                logger.warning("image failed", extra={"fields": {"attempt": attempt, "error": str(e)[:160]}})
                if attempt == self._retries:
                    return None
                wait = (e.retry_after or DEFAULT_WAIT) + 1 if isinstance(e, RateLimitError) else TRANSIENT_WAIT
                await self._sleep(min(wait, MAX_WAIT))
        return None
