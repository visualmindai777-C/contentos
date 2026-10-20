"""Contratos entre agentes e infraestructura. Los agentes importan solo este módulo y app.core.types.

Las implementaciones concretas (providers/) se enlazan en un único sitio: container.py.
Protocol (tipado estructural): un provider no necesita importar nada de la app para cumplir el contrato.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.core.enums import Platform
from app.core.types import (
    GeneratedImage, LLMResponse, Message, Narration, PostMetrics, ProjectContext,
    PublishRequest, PublishResult, RenderedVideo, StoredObject, TrendCandidate, VideoSpec,
)


class ProviderError(Exception):
    """Fallo de un proveedor externo (red, respuesta inválida, cuota agotada)."""


class RateLimitError(ProviderError):
    """El proveedor devolvió 429 o cuota agotada. Es esperable en tiers gratuitos: el llamador reintenta o aborta."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


@runtime_checkable
class LLMClient(Protocol):
    async def complete(
        self, messages: Sequence[Message], *, json_mode: bool = False, max_tokens: int = 1200
    ) -> LLMResponse:
        """Una llamada = una petición contada contra la cuota. El fallback entre modelos es cosa del provider
        y debe reflejarse en LLMResponse.model. Lanza RateLimitError si todos los modelos están agotados."""
        ...


@runtime_checkable
class ImageProvider(Protocol):
    async def generate(
        self, prompt: str, *, width: int = 1080, height: int = 1920, seed: int | None = None
    ) -> GeneratedImage:
        """Una imagen por llamada. Lanza RateLimitError ante 429."""
        ...


@runtime_checkable
class TTSProvider(Protocol):
    async def synthesize(self, text: str, *, voice: str, lang: str) -> Narration:
        """Devuelve audio y segmentos con tiempos (para subtítulos). El trabajo bloqueante va en un hilo."""
        ...


@runtime_checkable
class VideoProvider(Protocol):
    async def render(self, spec: VideoSpec) -> RenderedVideo:
        """Monta imágenes + audio + subtítulos en spec.output (vertical por defecto)."""
        ...


@runtime_checkable
class ObjectStorage(Protocol):
    async def put_bytes(self, key: str, data: bytes, mime_type: str) -> StoredObject: ...

    async def put_file(self, key: str, path: Path, mime_type: str) -> StoredObject:
        """Subida desde disco (vídeo) sin cargarlo en memoria."""
        ...

    async def delete(self, key: str) -> None: ...

    async def get_bytes(self, key: str) -> bytes: ...


@runtime_checkable
class TrendSource(Protocol):
    name: str

    async def fetch(self, project: ProjectContext, limit: int) -> list[TrendCandidate]:
        """Una fuente de tendencias (Google Trends, Reddit...). No usa LLM."""
        ...


@runtime_checkable
class Publisher(Protocol):
    platform: Platform

    async def publish(self, request: PublishRequest) -> PublishResult: ...

    async def get_metrics(self, external_id: str) -> PostMetrics: ...


@dataclass(frozen=True, slots=True)
class Providers:
    """Dependencias que reciben los agentes. Se construye en container.py; los tests pasan fakes.

    Publisher queda fuera: en el MVP la publicación es manual y no la ejecuta el pipeline.
    """

    llm: LLMClient
    images: ImageProvider
    tts: TTSProvider
    video: VideoProvider
    storage: ObjectStorage
    trends: Sequence[TrendSource]
