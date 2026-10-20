from pathlib import Path
from typing import TypedDict
from uuid import UUID

from app.core.types import ContentDraft, LLMResponse, MediaBundle, ProjectContext, TrendCandidate


class PipelineState(TypedDict, total=False):
    """Estado de un contenido a lo largo del grafo. Cada nodo devuelve solo las claves que cambia."""

    project: ProjectContext
    content_id: UUID | None
    status: str  # idea | guion | generado (refleja contents.status)
    topic: str
    keywords: list[str]
    images: list[bytes]
    part: int
    instructions: bool
    previous: str
    has_unused: bool
    candidates: list[TrendCandidate]
    draft: ContentDraft
    llm: LLMResponse
    media: MediaBundle
    workdir: Path
    error: str
    halt: bool  # cuota de LLM agotada: no tiene sentido seguir con más contenidos
