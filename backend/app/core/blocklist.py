"""Términos vetados: obras, personajes o marcas que el sistema no debe mencionar ni repetir. Lógica pura."""

import unicodedata

# Se suman a los del proyecto (config["banned_terms"]). Comparación sin mayúsculas, tildes ni signos.
DEFAULT_BANNED = ("mr robot", "mister robot", "elliot alderson", "fsociety")


def _norm(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join("".join(c if c.isalnum() else " " for c in plain.casefold()).split())


def banned_terms(config: dict) -> tuple[str, ...]:
    return (*DEFAULT_BANNED, *(str(t) for t in config.get("banned_terms", [])))


def find_banned(text: str, terms: tuple[str, ...]) -> str | None:
    """El primer término vetado que aparece como palabra(s) completa(s) en el texto, o None."""
    haystack = f" {_norm(text)} "
    for term in terms:
        needle = _norm(term)
        if needle and f" {needle} " in haystack:
            return term
    return None
