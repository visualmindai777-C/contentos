from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ContentStatus
from app.core.errors import Conflict
from app.models import Publication
from app.repositories.publications import PublicationRepository
from app.schemas.entities import PublicationCreate
from app.services.contents import ContentService


class PublicationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.contents = ContentService(session)
        self.repo = PublicationRepository(session)

    async def list(self, content_id: UUID | None, limit: int, offset: int) -> Sequence[Publication]:
        return await self.repo.find(content_id, limit, offset)

    async def register(self, data: PublicationCreate) -> Publication:
        """Registra una publicación manual y deja el contenido en 'publicado' (una sola transacción)."""
        content = await self.contents.get(data.content_id)
        if content.status not in (ContentStatus.APROBADO, ContentStatus.PUBLICADO):
            raise Conflict("Solo se puede publicar contenido aprobado")
        publication = await self.repo.save(Publication(
            content_id=data.content_id,
            platform=data.platform.value,
            published_at=data.published_at or datetime.now(UTC),
            notes=data.notes,
        ))
        content.status = ContentStatus.PUBLICADO.value
        await self.contents.repo.save(content)
        await self.session.commit()
        return publication
