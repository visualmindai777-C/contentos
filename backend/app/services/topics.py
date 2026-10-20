from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.models import Topic
from app.repositories.topics import TopicRepository
from app.schemas.entities import TopicCreate


class TopicService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TopicRepository(session)

    async def list(
        self, project_id: UUID | None, limit: int, offset: int, sort: str = "recent", days: int | None = None,
    ) -> Sequence[Topic]:
        return await self.repo.find(project_id, limit, offset, sort=sort, days=days)

    async def delete(self, topic_id: UUID) -> None:
        if not await self.repo.delete(topic_id):
            raise NotFound("Tema no encontrado")
        await self.session.commit()

    async def clear_unused(self, project_id: UUID) -> int:
        removed = await self.repo.clear_unused(project_id)
        await self.session.commit()
        return removed

    async def create(self, data: TopicCreate) -> Topic:
        topic = await self.repo.save(Topic(**data.model_dump()))
        await self.session.commit()
        return topic
