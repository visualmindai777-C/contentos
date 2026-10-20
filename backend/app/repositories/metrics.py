from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select

from app.core.enums import ContentStatus as S
from app.models import Asset, Content, Topic
from app.repositories.base import Repository

QUEUE = ("idea", "guion")
REVIEW = (S.GENERADO.value, S.REVISADO.value)
PENDING = (S.IDEA.value, S.GUION.value, S.GENERADO.value, S.REVISADO.value)


@dataclass(frozen=True, slots=True)
class Snapshot:
    total: int
    approved: int
    published: int
    rejected: int
    pending: int
    queued: int
    scripted: int
    review: int
    failed: int
    tokens: int
    llm_calls: int
    topics: int
    asset_bytes: int


class MetricsRepository(Repository):
    async def snapshot(self, since: datetime) -> Snapshot:
        """Todas las cifras del dashboard y de los límites en UNA consulta: la BD está lejos de la API y cada ida y vuelta cuesta."""
        c = Content
        query = select(
            func.count(),
            func.count().filter(c.status == S.APROBADO.value),
            func.count().filter(c.status == S.PUBLICADO.value),
            func.count().filter(c.status == S.RECHAZADO.value),
            func.count().filter(c.status.in_(PENDING)),
            func.count().filter(c.status.in_(QUEUE), c.last_error == ""),
            func.count().filter(c.status == S.GUION.value, c.last_error == ""),
            func.count().filter(c.status.in_(REVIEW)),
            func.count().filter(c.status.in_(QUEUE), c.last_error != ""),
            func.coalesce(func.sum(c.tokens_used), 0),
            func.count().filter(c.llm_provider != "", c.updated_at >= since),
            select(func.count()).select_from(Topic).scalar_subquery(),
            select(func.coalesce(func.sum(Asset.file_size), 0)).scalar_subquery(),
        )
        return Snapshot(*(int(v) for v in (await self.session.execute(query)).one()))
