from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import defer

from app.core.enums import ContentStatus
from app.models import Content
from app.repositories.base import Repository


QUEUE_STATUSES = ["idea", "guion"]


class ContentRepository(Repository):
    async def get(self, content_id: UUID) -> Content | None:
        return await self.session.get(Content, content_id)

    async def find(self, project_id: UUID | None, status: ContentStatus | None, limit: int, offset: int) -> Sequence[Content]:
        query = (
            select(Content)
            .options(defer(Content.hook), defer(Content.script), defer(Content.caption), defer(Content.hashtags), defer(Content.cta))
            .order_by(Content.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if project_id:
            query = query.where(Content.project_id == project_id)
        if status:
            query = query.where(Content.status == status.value)
        return (await self.session.scalars(query)).all()

    async def find_queue(self, project_ids: Sequence[UUID] | None, limit: int) -> Sequence[UUID]:
        """Cola del pipeline: 'idea' (falta guion) y 'guion' (falta media) SIN error. Un contenido fallido sale de la
        cola hasta que el usuario pulse Reintentar: así un fallo persistente no gasta cuota de LLM ni minutos de Actions."""
        query = (
            select(Content.id).where(Content.status.in_(QUEUE_STATUSES), Content.last_error == "")
            .order_by(Content.updated_at, Content.created_at).limit(limit)
        )
        if project_ids:
            query = query.where(Content.project_id.in_(project_ids))
        return (await self.session.scalars(query)).all()

    async def count_queue(self) -> tuple[int, int]:
        """(pendientes, con error) de la cola del pipeline."""
        query = select(
            func.count().filter(Content.last_error == ""), func.count().filter(Content.last_error != "")
        ).where(Content.status.in_(QUEUE_STATUSES))
        pending, failed = (await self.session.execute(query)).one()
        return pending, failed

    async def mark_failed(self, content_id: UUID, error: str) -> None:
        await self.session.execute(update(Content).where(Content.id == content_id).values(last_error=error[:500]))

    async def count_by_status(self) -> dict[str, int]:
        rows = await self.session.execute(select(Content.status, func.count()).group_by(Content.status))
        return {status: n for status, n in rows}

    async def tokens_total(self) -> int:
        return await self.session.scalar(select(func.coalesce(func.sum(Content.tokens_used), 0))) or 0

    async def llm_touched_since(self, since: datetime) -> int:
        query = select(func.count()).select_from(Content).where(Content.llm_provider != "", Content.updated_at >= since)
        return await self.session.scalar(query) or 0
