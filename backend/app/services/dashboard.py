from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.contents import ContentRepository
from app.repositories.metrics import MetricsRepository
from app.schemas.entities import DashboardStats, QueueStatus


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.contents = ContentRepository(session)
        self.metrics = MetricsRepository(session)

    async def stats(self) -> DashboardStats:
        m = await self.metrics.snapshot(datetime.now(UTC))
        return DashboardStats(
            total=m.total, approved=m.approved, published=m.published, rejected=m.rejected,
            pending=m.pending, topics=m.topics, queued=m.queued, failed=m.failed,
        )

    async def queue(self) -> QueueStatus:
        """Lo consulta el Worker de Cloudflare para decidir si lanza el pipeline."""
        pending, failed = await self.contents.count_queue()
        return QueueStatus(pending=pending, failed=failed)
