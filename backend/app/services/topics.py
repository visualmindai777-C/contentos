from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Topic
from app.repositories.topics import TopicRepository
from app.schemas.entities import TopicCreate


class TopicService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TopicRepository(session)

    async def list(self, project_id: UUID | None, limit: int, offset: int) -> Sequence[Topic]:
        return await self.repo.find(project_id, limit, offset)

    async def create(self, data: TopicCreate) -> Topic:
        topic = await self.repo.save(Topic(**data.model_dump()))
        await self.session.commit()
        return topic
