"""Unión de fragmentos WAV (mismo formato) con pausas. Solo biblioteca estándar."""

import io
import wave


def wav_seconds(data: bytes) -> float:
    with wave.open(io.BytesIO(data)) as w:
        return w.getnframes() / w.getframerate()


def join_wavs(parts: list[bytes], gap: float = 0.3) -> tuple[bytes, list[float]]:
    """Devuelve el WAV unido y el instante de inicio de cada fragmento."""
    out, starts, elapsed = io.BytesIO(), [], 0.0
    writer: wave.Wave_write | None = None
    for i, data in enumerate(parts):
        with wave.open(io.BytesIO(data)) as r:
            if writer is None:
                writer = wave.open(out, "wb")
                writer.setnchannels(r.getnchannels())
                writer.setsampwidth(r.getsampwidth())
                writer.setframerate(r.getframerate())
            rate, width, channels = r.getframerate(), r.getsampwidth(), r.getnchannels()
            starts.append(elapsed)
            writer.writeframes(r.readframes(r.getnframes()))
            elapsed += r.getnframes() / rate
        if i < len(parts) - 1 and gap:
            silence = round(gap * rate)
            writer.writeframes(b"\x00" * silence * width * channels)
            elapsed += silence / rate
    if writer is None:
        raise ValueError("no hay audio que unir")
    writer.close()
    return out.getvalue(), starts
