import re

_WORD = re.compile(r"[^\W\d_]{4,}")


def extract_keywords(text: str, limit: int = 6) -> list[str]:
    seen: dict[str, None] = {}
    for word in _WORD.findall(text.lower()):
        seen.setdefault(word)
    return list(seen)[:limit]
