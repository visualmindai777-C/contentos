import math

from app.core.text import extract_keywords

__all__ = ["extract_keywords", "log_score"]


def log_score(value: float, floor: float, ceil: float) -> float:
    """Escala logarítmica a 0–100: floor → 0, ceil → 100."""
    if value <= floor:
        return 0.0
    ratio = (math.log10(value) - math.log10(floor)) / (math.log10(ceil) - math.log10(floor))
    return round(min(1.0, ratio) * 100, 1)
