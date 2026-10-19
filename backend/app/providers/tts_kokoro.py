import asyncio
import io
from typing import Any

from app.core.interfaces import ProviderError
from app.core.types import Narration, Segment

SAMPLE_RATE = 24_000
SENTENCES = r"(?<=[.!?…])\s+"


class KokoroTTS:
    """Kokoro-82M en CPU. torch/kokoro se importan al primer uso: la API no los necesita."""

    def __init__(self) -> None:
        self._pipelines: dict[str, Any] = {}

    async def synthesize(self, text: str, *, voice: str, lang: str) -> Narration:
        return await asyncio.to_thread(self._synthesize, text, voice, lang)

    def _pipeline(self, lang: str) -> Any:
        if lang not in self._pipelines:
            from kokoro import KPipeline

            self._pipelines[lang] = KPipeline(lang_code=lang)
        return self._pipelines[lang]

    def _synthesize(self, text: str, voice: str, lang: str) -> Narration:
        import numpy as np
        import soundfile as sf

        chunks: list[Any] = []
        segments: list[Segment] = []
        elapsed = 0.0
        try:
            for result in self._pipeline(lang)(text, voice=voice, speed=1.0, split_pattern=SENTENCES):
                graphemes, _, audio = result
                if audio is None:
                    continue
                samples = audio.numpy() if hasattr(audio, "numpy") else np.asarray(audio)
                duration = len(samples) / SAMPLE_RATE
                segments.append(Segment(graphemes.strip(), elapsed, elapsed + duration))
                chunks.append(samples)
                elapsed += duration
        except Exception as e:
            raise ProviderError(f"kokoro: {e!r}") from e
        if not chunks:
            raise ProviderError("kokoro: no generó audio")

        buffer = io.BytesIO()
        sf.write(buffer, np.concatenate(chunks), SAMPLE_RATE, format="WAV", subtype="PCM_16")
        return Narration(audio=buffer.getvalue(), mime_type="audio/wav", duration=elapsed, segments=segments)
