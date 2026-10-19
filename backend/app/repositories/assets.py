from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, select

from app.models import Asset
from app.repositories.base import Repository


class AssetRepository(Repository):
    async def find_for_content(self, content_id: UUID) -> Sequence[Asset]:
        query = select(Asset).where(Asset.content_id == content_id).order_by(Asset.created_at)
        return (await self.session.scalars(query)).all()

    async def replace_for_content(self, content_id: UUID, assets: Sequence[Asset]) -> None:
        await self.session.execute(delete(Asset).where(Asset.content_id == content_id))
        self.session.add_all(assets)
        await self.session.flush()

    async def total_bytes(self) -> int:
        return await self.session.scalar(select(func.coalesce(func.sum(Asset.file_size), 0))) or 0
