"""Guion de mini novela: personajes, escenas y diálogos. Lógica pura. El guion es texto plano (contents.script):

    PERSONAJES
    LUCÍA | f | young woman, short red hair, turquoise t-shirt
    ESCENA | Lucía in a cozy kitchen at night, shocked face, medium shot
    LUCÍA: ¿Me mentiste todo este tiempo?
    NARRADOR: Esa noche todo cambió.
"""

import re
from dataclasses import dataclass, field

NARRATOR = "NARRADOR"
_NARRATOR_NAMES = {"NARRADOR", "NARRADORA", "VOZ EN OFF"}
_SCENE = re.compile(r"^\s*ESCENA\b[^|:\n]*[|:]\s*(.+?)\s*$", re.IGNORECASE)
_CHARACTER = re.compile(r"^\s*([^|:\n]{1,30}?)\s*\|\s*([fmFM])\w*\s*\|\s*(.+?)\s*$")
_LINE = re.compile(r"^\s*([^\W\d_][\w .'\-]{0,28}?)\s*(?:\([^)]*\))?\s*:\s*(.+?)\s*$")
_MARKUP = re.compile(r"[*_`#]")


@dataclass(frozen=True, slots=True)
class Character:
    name: str
    gender: str  # "f" | "m"
    look: str


@dataclass(frozen=True, slots=True)
class Line:
    speaker: str  # nombre en mayúsculas, o NARRADOR
    text: str


@dataclass(slots=True)
class Scene:
    setting: str
    lines: list[Line] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Screenplay:
    characters: dict[str, Character]
    scenes: list[Scene]

    @property
    def lines(self) -> list[Line]:
        return [line for scene in self.scenes for line in scene.lines]


def _speaker(raw: str) -> str:
    name = raw.strip().upper()
    return NARRATOR if name in _NARRATOR_NAMES else name


def parse_screenplay(script: str) -> Screenplay | None:
    """None si el texto no tiene forma de guion de novela (se usa el flujo de narración normal)."""
    characters: dict[str, Character] = {}
    scenes: list[Scene] = []
    for raw in _MARKUP.sub("", script).splitlines():
        if not raw.strip() or raw.strip().upper().startswith("PERSONAJES"):
            continue
        if m := _SCENE.match(raw):
            scenes.append(Scene(setting=m.group(1)))
        elif not scenes and (m := _CHARACTER.match(raw)):
            name = _speaker(m.group(1))
            characters[name] = Character(name, m.group(2).lower(), m.group(3))
        elif scenes and (m := _LINE.match(raw)):
            scenes[-1].lines.append(Line(_speaker(m.group(1)), m.group(2)))
    scenes = [s for s in scenes if s.lines]
    return Screenplay(characters, scenes) if len(scenes) >= 2 and sum(len(s.lines) for s in scenes) >= 4 else None
