"""Tipos de dominio que cruzan las interfaces. Solo stdlib: sin dependencias de proveedores."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from app.core.enums import Platform


@dataclass(frozen=True, slots=True)
class ProjectContext:
    id: UUID
    name: str
    niche: str
    language: str
    config: dict[str, Any] = field(default_factory=dict)


# --- Tendencias (salida de TrendAgent) ---
@dataclass(frozen=True, slots=True)
class TrendCandidate:
    topic: str
    score: float
    keywords: list[str]
    source: str


# --- LLM ---
@dataclass(frozen=True, slots=True)
class Message:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    tokens_used: int  # prompt + completion; alimenta contents.tokens_used


# --- Contenido (salida de ContentAgent, una sola llamada LLM) ---
@dataclass(frozen=True, slots=True)
class ContentDraft:
    title: str
    hook: str
    script: str
    caption: str
    hashtags: list[str]
    cta: str


# --- Media ---
@dataclass(frozen=True, slots=True)
class GeneratedImage:
    data: bytes
    mime_type: str


@dataclass(frozen=True, slots=True)
class Segment:
    """Fragmento de narración con tiempos en segundos: base de los subtítulos."""

    text: str
    start: float
    end: float


@dataclass(frozen=True, slots=True)
class Narration:
    audio: bytes
    mime_type: str
    duration: float
    segments: list[Segment]


@dataclass(frozen=True, slots=True)
class VideoSpec:
    """Los ficheros viven en un directorio de trabajo local; el vídeo nunca se carga entera en memoria."""

    images: list[Path]
    audio: Path
    segments: list[Segment]
    output: Path
    width: int = 1080
    height: int = 1920
    fps: int = 30
    watermark: Path | None = None  # ícono de marca (PNG con transparencia), arriba a la derecha, fuera de la zona de la interfaz
    outro: Path | None = None  # tarjeta final 9:16 de la marca
    outro_seconds: float = 2.0
    durations: list[float] | None = None  # segundos que ocupa cada imagen (novela); por defecto se reparten a partes iguales
    crop_bottom: float = 0.0  # fracción inferior que se recorta de cada imagen (marcas de agua de proveedores gratuitos)


@dataclass(frozen=True, slots=True)
class RenderedVideo:
    path: Path
    duration: float
    file_size: int


@dataclass(frozen=True, slots=True)
class MediaBundle:
    """Salida de MediaAgent: ficheros en un directorio temporal que StorageAgent sube y borra."""

    video: RenderedVideo
    images: list[Path]
    subtitles: str  # SRT


# --- Almacenamiento de objetos ---
@dataclass(frozen=True, slots=True)
class StoredObject:
    key: str
    file_size: int
    mime_type: str
    provider: str  # assets.storage_provider


# --- Publicación (hoy manual; mañana APIs reales) ---
@dataclass(frozen=True, slots=True)
class PublishRequest:
    content_id: UUID
    platform: Platform
    caption: str
    hashtags: list[str]
    video: Path | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class PublishResult:
    platform: Platform
    external_id: str
    url: str | None
    published_at: datetime


@dataclass(frozen=True, slots=True)
class PostMetrics:
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
