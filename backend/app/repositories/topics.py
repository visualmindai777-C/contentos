from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.types import TrendCandidate
from app.models import Content, Topic
from app.repositories.base import Repository


class TopicRepository(Repository):
    async def find(
        self, project_id: UUID | None, limit: int, offset: int, *, sort: str = "recent", days: int | None = None,
    ) -> Sequence[Topic]:
        """Las ideas que el usuario pega ('idea') son suyas, no tendencias: no se listan."""
        order = (Topic.score.desc(), Topic.created_at.desc()) if sort == "score" else (Topic.created_at.desc(),)
        query = select(Topic).where(Topic.source != "idea").order_by(*order).limit(limit).offset(offset)
        if project_id:
            query = query.where(Topic.project_id == project_id)
        if days:
            query = query.where(Topic.created_at >= datetime.now(UTC) - timedelta(days=days))
        topics = (await self.session.scalars(query)).all()
        used = set(await self.session.scalars(select(Content.topic_id).where(Content.topic_id.in_([t.id for t in topics]))))
        for t in topics:
            t.used = t.id in used  # atributo transitorio: lo lee TopicOut
        return topics

    async def delete(self, topic_id: UUID) -> bool:
        """Los contenidos ya creados con el tema se conservan (su topic_id queda en NULL)."""
        return (await self.session.execute(delete(Topic).where(Topic.id == topic_id))).rowcount > 0

    async def clear_unused(self, project_id: UUID) -> int:
        """Borra los temas de tendencias que no tienen contenido. Las ideas del usuario ('idea') no se tocan."""
        used = select(Content.id).where(Content.topic_id == Topic.id).exists()
        stmt = delete(Topic).where(Topic.project_id == project_id, Topic.source != "idea", ~used)
        return (await self.session.execute(stmt)).rowcount

    async def get(self, topic_id: UUID) -> Topic | None:
        return await self.session.get(Topic, topic_id)

    async def add_new(self, project_id: UUID, candidates: Sequence[TrendCandidate]) -> int:
        """Inserta las tendencias que aún no existen en el proyecto; devuelve cuántas eran nuevas."""
        rows = [
            {"project_id": project_id, "topic": c.topic[:300], "keywords": c.keywords, "source": c.source,
             "summary": c.summary[:500], "score": c.score}
            for c in candidates
        ]
        if not rows:
            return 0
        stmt = pg_insert(Topic).values(rows)
        # Un tema que ya existía sin resumen (de antes de que hubiera resúmenes) lo recibe ahora
        stmt = stmt.on_conflict_do_update(
            index_elements=["project_id", "topic"], set_={"summary": stmt.excluded.summary}, where=Topic.summary == "",
        )
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
