import asyncio
import logging
import mimetypes
import re
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path

from app.core.audio import join_wavs
from app.core.interfaces import ImageProvider, MotionProvider, ProviderError, RateLimitError, TTSProvider, VideoProvider
from app.core.screenplay import NARRATOR, Screenplay, parse_screenplay
from app.core.subtitles import chunk_segments, to_srt
from app.core.types import ContentDraft, GeneratedImage, MediaBundle, Narration, ProjectContext, Segment, VideoSpec

logger = logging.getLogger("app.pipeline")

BRAND_DIR = Path(__file__).resolve().parent.parent / "assets" / "brand"  # kit de marca visualmindai777
IMAGE_SIZE = (768, 1024)  # el vídeo sale en 1080x1920; a esta resolución Pollinations va más rápido
MIN_IMAGES = 2
DEFAULT_CROP_BOTTOM = 0.05  # Pollinations anónimo estampa su logo en el ~3 % inferior; nologo=true se ignora sin clave
DEFAULT_WAIT = 45.0  # Pollinations anónimo: 1 imagen cada ~45 s por IP
TRANSIENT_WAIT = 5.0  # timeouts y errores de red del proveedor
MAX_WAIT = 120.0
PIXAR_STYLE = (
    "3D animated movie style, Pixar-like cartoon character, big expressive eyes, soft studio lighting, "
    "vibrant colors, smooth shading, medium shot, no text, no watermark"
)
DEFAULT_VOICES = {"f": "ef_dora", "m": "em_alex", NARRATOR: "em_alex"}  # voces de Kokoro en español
LINE_GAP = 0.3  # pausa entre líneas de diálogo, en segundos
MAX_SCENES = 5
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
        retries: int = 3, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep, motion: MotionProvider | None = None,
    ):
        self._tts, self._images, self._video = tts, images, video
        self._voice, self._lang = voice, lang
        self._retries = retries
        self._sleep = sleep
        self._motion = motion

    async def run(
        self, project: ProjectContext, topic: str, draft: ContentDraft, workdir: Path, *, existing_images: Sequence[bytes] | None = None,
    ) -> MediaBundle:
        cfg = project.config
        play = parse_screenplay(draft.script) if cfg.get("format") == "novela" else None
        if play:
            return await self._run_novela(project, play, workdir, existing_images)
        narration, images = await asyncio.gather(
            self._tts.synthesize(
                clean_for_speech(draft.script), voice=cfg.get("tts_voice", self._voice), lang=cfg.get("tts_lang", self._lang)
            ),
            self._generate_all(
                scene_prompts(draft.script, topic, int(cfg.get("images_per_video", 4)), cfg.get("image_style", DEFAULT_STYLE)),
                None, existing_images,
            ),
        )
        audio = workdir / "audio.wav"
        audio.write_bytes(narration.audio)
        paths = self._save_images(images, workdir)

        video = await self._video.render(VideoSpec(
            images=paths, audio=audio, segments=narration.segments, output=workdir / "video.mp4",
            crop_bottom=float(cfg.get("image_crop_bottom", DEFAULT_CROP_BOTTOM)), **self._brand(cfg),
            clips=await self._clips(cfg, paths, [narration.duration / len(paths)] * len(paths), workdir),
        ))
        return MediaBundle(video=video, images=paths, subtitles=to_srt(chunk_segments(narration.segments)))

    async def _run_novela(
        self, project: ProjectContext, play: Screenplay, workdir: Path, existing: Sequence[bytes] | None = None,
    ) -> MediaBundle:
        """Mini novela: una voz por personaje, una imagen por escena y las escenas duran lo que duran sus diálogos."""
        cfg = project.config
        scenes = play.scenes[:MAX_SCENES]
        style = cfg.get("image_style", PIXAR_STYLE)
        prompts = [f"{style}. {self._look(play, scene)}{scene.setting}" for scene in scenes]
        # La misma semilla para el mismo personaje principal: ayuda a que conserve la cara entre escenas
        names = sorted(play.characters)
        seeds = [10 * (names.index(m) + 1) if (m := self._main(play, scene)) else i for i, scene in enumerate(scenes)]
        (narration, scene_seconds), images = await asyncio.gather(
            self._dialogue(play, scenes, cfg), self._generate_all(prompts, seeds, existing),
        )
        audio = workdir / "audio.wav"
        audio.write_bytes(narration.audio)
        paths = self._save_images(images, workdir)
        # Si alguna imagen no salió, sus escenas se funden con la anterior: la duración de esa imagen se suma
        durations = self._merge_durations(scene_seconds, len(prompts), len(paths), images)
        video = await self._video.render(VideoSpec(
            images=paths, audio=audio, segments=narration.segments, output=workdir / "video.mp4",
            durations=durations, crop_bottom=float(cfg.get("image_crop_bottom", DEFAULT_CROP_BOTTOM)), **self._brand(cfg),
            clips=await self._clips(cfg, paths, durations, workdir),
        ))
        return MediaBundle(video=video, images=paths, subtitles=to_srt(chunk_segments(narration.segments)))

    @staticmethod
    def _main(play: Screenplay, scene) -> str | None:
        speakers = [l.speaker for l in scene.lines if l.speaker in play.characters]
        return max(sorted(set(speakers)), key=speakers.count) if speakers else None

    def _look(self, play: Screenplay, scene) -> str:
        """Aspecto fijo del personaje que más habla en la escena, repetido en cada imagen para que se parezca."""
        main = self._main(play, scene)
        return f"{play.characters[main].look}. " if main else ""

    async def _dialogue(self, play: Screenplay, scenes, cfg: dict) -> tuple[Narration, list[float]]:
        voices = {**DEFAULT_VOICES, **cfg.get("voices", {})}
        lang = cfg.get("tts_lang", self._lang)
        parts: list[bytes] = []
        spoken: list[list[Segment]] = []
        scene_of: list[int] = []
        for s, scene in enumerate(scenes):
            for line in scene.lines:
                char = play.characters.get(line.speaker)
                voice = voices.get(line.speaker) or voices.get(char.gender if char else "f", self._voice)
                said = await self._tts.synthesize(clean_for_speech(line.text), voice=voice, lang=lang)
                parts.append(said.audio)
                spoken.append(said.segments)
                scene_of.append(s)
        wav, starts = join_wavs(parts, LINE_GAP)
        segments = [Segment(seg.text, start + seg.start, start + seg.end) for segs, start in zip(spoken, starts) for seg in segs]
        total = segments[-1].end
        scene_seconds = [0.0] * len(scenes)
        for i, s in enumerate(scene_of):
            end = starts[i + 1] if i + 1 < len(starts) else total
            scene_seconds[s] += end - starts[i]
        return Narration(wav, "audio/wav", total, segments), scene_seconds

    @staticmethod
    def _merge_durations(seconds: list[float], wanted: int, got: int, images: list) -> list[float]:
        if got == wanted:
            return seconds
        # Las imágenes que sí salieron se reparten el tiempo total a partes proporcionales a sus escenas originales
        return [sum(seconds) / got] * got

    @staticmethod
    def _save_images(images: list[GeneratedImage], workdir: Path) -> list[Path]:
        paths = []
        for i, image in enumerate(images):
            path = workdir / f"img_{i}{mimetypes.guess_extension(image.mime_type) or '.jpg'}"
            path.write_bytes(image.data)
            paths.append(path)
        return paths

    async def _clips(self, cfg: dict, paths: list[Path], durations: list[float], workdir: Path) -> list[Path | None] | None:
        """Paralaje 3D por escena si el proyecto lo pide (`"motion": "parallax"`). Si falla, esa escena sigue con zoom."""
        if cfg.get("motion") != "parallax" or self._motion is None:
            return None
        clips: list[Path | None] = []
        for i, (path, seconds) in enumerate(zip(paths, durations)):
            try:  # un poco más largo que la escena: FFmpeg recorta al instante exacto
                clips.append(await self._motion.animate(path, workdir / f"clip_{i}.mp4", seconds=seconds + 0.4, index=i))
            except ProviderError as e:
                logger.warning("motion failed", extra={"fields": {"scene": i, "error": str(e)[:200]}})
                clips.append(None)
        return clips if any(clips) else None

    @staticmethod
    def _brand(cfg: dict) -> dict:
        """Marca de agua y tarjeta final del canal. Por defecto solo en novelas; `"brand": false` la quita."""
        if not cfg.get("brand", cfg.get("format") == "novela"):
            return {}
        watermark, outro = BRAND_DIR / "watermark.png", BRAND_DIR / "outro.png"
        return {"watermark": watermark if watermark.exists() else None, "outro": outro if outro.exists() else None}

    async def _generate_all(
        self, prompts: list[str], seeds: list[int] | None = None, existing: Sequence[bytes] | None = None,
    ) -> list[GeneratedImage]:
        images = []
        for i, (seed, prompt) in enumerate(zip(seeds or range(len(prompts)), prompts)):  # en serie: el proveedor gratuito solo admite una a la vez
            if existing and i < len(existing):  # imagen ya generada (corrección de texto): no se vuelve a pedir
                data = existing[i]
                images.append(GeneratedImage(data, "image/png" if data.startswith(b"\x89PNG") else "image/jpeg"))
            elif image := await self._generate(prompt, seed):
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
