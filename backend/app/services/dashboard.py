from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ContentStatus as S
from app.repositories.contents import ContentRepository
from app.repositories.topics import TopicRepository
from app.schemas.entities import DashboardStats, QueueStatus

PENDING = (S.IDEA, S.GUION, S.GENERADO, S.REVISADO)


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.contents = ContentRepository(session)
        self.topics = TopicRepository(session)

    async def stats(self) -> DashboardStats:
        counts = await self.contents.count_by_status()
        queued, failed = await self.contents.count_queue()
        return DashboardStats(
            total=sum(counts.values()),
            approved=counts.get(S.APROBADO, 0),
            published=counts.get(S.PUBLICADO, 0),
            rejected=counts.get(S.RECHAZADO, 0),
            pending=sum(counts.get(s, 0) for s in PENDING),
            topics=await self.topics.count(),
            queued=queued,
            failed=failed,
        )

    async def queue(self) -> QueueStatus:
        """Lo consulta el Worker de Cloudflare para decidir si lanza el pipeline."""
        pending, failed = await self.contents.count_queue()
        return QueueStatus(pending=pending, failed=failed)
