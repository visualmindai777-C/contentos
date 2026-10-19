from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.models import Publication
from app.repositories.base import Repository


class PublicationRepository(Repository):
    async def find(self, content_id: UUID | None, limit: int, offset: int) -> Sequence[Publication]:
        query = select(Publication).order_by(Publication.published_at.desc()).limit(limit).offset(offset)
        if content_id:
            query = query.where(Publication.content_id == content_id)
        return (await self.session.scalars(query)).all()
