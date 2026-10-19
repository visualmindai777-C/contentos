from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ContentStatus as S
from app.core.errors import Conflict, NotFound
from app.models import Content
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
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ContentRepository(session)

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
