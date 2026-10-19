from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.types import TrendCandidate
from app.models import Content, Topic
from app.repositories.base import Repository


class TopicRepository(Repository):
    async def find(self, project_id: UUID | None, limit: int, offset: int) -> Sequence[Topic]:
        query = select(Topic).order_by(Topic.created_at.desc()).limit(limit).offset(offset)
        if project_id:
            query = query.where(Topic.project_id == project_id)
        return (await self.session.scalars(query)).all()

    async def get(self, topic_id: UUID) -> Topic | None:
        return await self.session.get(Topic, topic_id)

    async def add_new(self, project_id: UUID, candidates: Sequence[TrendCandidate]) -> int:
        """Inserta las tendencias que aún no existen en el proyecto; devuelve cuántas eran nuevas."""
        rows = [
            {"project_id": project_id, "topic": c.topic[:300], "keywords": c.keywords, "source": c.source, "score": c.score}
            for c in candidates
        ]
        if not rows:
            return 0
        stmt = pg_insert(Topic).values(rows).on_conflict_do_nothing(index_elements=["project_id", "topic"])
        return (await self.session.execute(stmt)).rowcount

    async def next_unused(self, project_id: UUID, max_age_days: int = 7) -> Topic | None:
        """Mejor tema reciente que todavía no tiene contenido."""
        since = datetime.now(UTC) - timedelta(days=max_age_days)
        used = select(Content.id).where(Content.topic_id == Topic.id).exists()
        query = (
            select(Topic).where(Topic.project_id == project_id, Topic.created_at >= since, ~used)
            .order_by(Topic.score.desc(), Topic.created_at.desc()).limit(1)
        )
        return await self.session.scalar(query)

    async def count(self) -> int:
        return await self.session.scalar(select(func.count()).select_from(Topic)) or 0
