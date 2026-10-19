"""Subtítulos a partir de los segmentos de la narración. Lógica pura, sin dependencias."""

import math

from app.core.types import Segment


def chunk_segments(segments: list[Segment], max_words: int = 5) -> list[Segment]:
    """Parte frases largas en trozos cortos legibles en vertical; el tiempo se reparte según los caracteres."""
    out: list[Segment] = []
    for seg in segments:
        words = seg.text.split()
        if not words:
            continue
        size = math.ceil(len(words) / math.ceil(len(words) / max_words))
        groups = [words[i : i + size] for i in range(0, len(words), size)]
        weights = [sum(len(w) + 1 for w in g) for g in groups]
        t = seg.start
        for group, weight in zip(groups, weights):
            end = t + (seg.end - seg.start) * weight / sum(weights)
            out.append(Segment(" ".join(group), t, end))
            t = end
    return out


def _stamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    return f"{ms // 3_600_000:02}:{ms // 60_000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def to_srt(segments: list[Segment]) -> str:
    return "".join(
        f"{i}\n{_stamp(s.start)} --> {_stamp(s.end)}\n{s.text}\n\n" for i, s in enumerate(segments, 1)
    )
