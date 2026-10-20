from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ContentStatus as S
from app.core.errors import Conflict, NotFound
from app.core.interfaces import ObjectStorage
from app.core.settings import get_settings
from app.core.screenplay import parse_screenplay
from app.models import Content, Project
from app.repositories.assets import AssetRepository
from app.repositories.contents import ContentRepository
from app.schemas.entities import ContentCreate

# Transiciones manuales permitidas. El pipeline escribe estados por su cuenta (guion → generado).
TRANSITIONS: dict[S, set[S]] = {
    S.IDEA: {S.GUION, S.RECHAZADO},
    S.GUION: {S.GENERADO, S.RECHAZADO},
    S.GENERADO: {S.REVISADO, S.APROBADO, S.RECHAZADO},
    S.REVISADO: {S.APROBADO, S.RECHAZADO},
    S.APROBADO: {S.REVISADO, S.RECHAZADO, S.PUBLICADO},
    S.PUBLICADO: set(),
    S.RECHAZADO: {S.IDEA},
}


class ContentService:
    def __init__(self, session: AsyncSession, storage: ObjectStorage | None = None):
        self.session = session
        self.repo = ContentRepository(session)
        self._storage = storage

    async def get(self, content_id: UUID) -> Content:
        content = await self.repo.get(content_id)
        if content is None:
            raise NotFound("Contenido no encontrado")
        return content

    async def list(self, project_id: UUID | None, status: S | None, limit: int, offset: int) -> Sequence[Content]:
        return await self.repo.find(project_id, status, limit, offset)

    async def create(self, data: ContentCreate) -> Content:
        content = await self.repo.save(Content(**data.model_dump()))
        await self.session.commit()
        return content

    async def transition(self, content_id: UUID, target: S) -> Content:
        content = await self.get(content_id)
        if target == S.PUBLICADO:
            raise Conflict("Para publicar usa PATCH /contents/{id}/publish")
        if target not in TRANSITIONS[S(content.status)]:
            raise Conflict(f"Transición inválida: {content.status} → {target.value}")
        content.status = target.value
        await self.repo.save(content)
        await self.session.commit()
        return content

    async def regenerate(self, content_id: UUID) -> Content:
        """No genera nada: 'idea' es la cola. El workflow de GitHub Actions procesa los contenidos en 'idea'."""
        content = await self.get(content_id)
        if content.status == S.IDEA and not content.last_error:
            return content
        if content.status == S.PUBLICADO:
            raise Conflict("No se puede regenerar un contenido publicado")
        content.status = S.IDEA.value
        content.last_error = ""
        await self.repo.save(content)
        await self.session.commit()
        return content

    async def retry(self, content_id: UUID) -> Content:
        """Devuelve a la cola un contenido que falló, conservando su estado: 'guion' solo repite la media (sin LLM)."""
        content = await self.get(content_id)
        if content.status not in (S.IDEA, S.GUION) or not content.last_error:
            raise Conflict("El contenido no tiene un error que reintentar")
        content.last_error = ""
        await self.repo.save(content)
        await self.session.commit()
        return content

    async def update_script(self, content_id: UUID, script: str, title: str | None = None) -> Content:
        """Corrige el texto de un video ya generado. Las imágenes se conservan: vuelve a la cola solo para rehacer voz y video."""
        content = await self.get(content_id)
        if S(content.status) not in (S.GENERADO, S.REVISADO, S.APROBADO):
            raise Conflict("Solo se puede corregir un video generado y aún sin publicar")
        project = await self.session.get(Project, content.project_id)
        if (project.config or {}).get("format") == "novela" and parse_screenplay(script) is None:
            raise Conflict("El guion no sigue el formato de novela (PERSONAJES / ESCENA / diálogos)")
        content.script = script.strip()
        if title and title.strip():
            content.title = title.strip()[:100]
        content.status = S.GUION.value
        content.last_error = ""
        await self.repo.save(content)
        await self.session.commit()
        return content

    async def next_part(self, content_id: UUID) -> Content:
        """Crea la siguiente parte de una serie: un contenido en cola que continuará la historia de este."""
        parent = await self.get(content_id)
        if S(parent.status) not in (S.GENERADO, S.REVISADO, S.APROBADO, S.PUBLICADO) or not parent.script:
            raise Conflict("Solo se puede continuar un contenido ya generado")
        if await self.repo.has_child(content_id):
            raise Conflict(f"Ya existe la parte {parent.part + 1} de esta serie")
        child = await self.repo.save(Content(
            project_id=parent.project_id, topic_id=parent.topic_id, parent_id=parent.id, part=parent.part + 1,
        ))
        await self.session.commit()
        return child

    async def series(self, content_id: UUID) -> Sequence[dict]:
        await self.get(content_id)
        return await self.repo.series(content_id)

    async def purge(self, content_id: UUID) -> None:
        """Borra un contenido rechazado: primero sus archivos de R2 y, solo si eso salió bien, las filas (assets y publicaciones en cascada)."""
        content = await self.get(content_id)
        if content.status != S.RECHAZADO:
            raise Conflict("Solo se pueden eliminar definitivamente los contenidos rechazados")
        assets = await AssetRepository(self.session).find_for_content(content_id)
        if assets:
            storage = self._storage or self._r2()
            for asset in assets:
                await storage.delete(asset.storage_key)  # idempotente: una clave ya borrada no falla
        await self.session.delete(content)
        await self.session.commit()

    @staticmethod
    def _r2() -> ObjectStorage:
        s = get_settings()
        if not (s.r2_account_id and s.r2_access_key_id and s.r2_secret_access_key):
            raise Conflict("La API no tiene credenciales de R2: no se pueden borrar los archivos")
        from app.providers.storage_r2 import R2Storage  # boto3 solo se carga si hay algo que borrar

        return R2Storage(s.r2_account_id, s.r2_access_key_id, s.r2_secret_access_key, s.r2_bucket)
