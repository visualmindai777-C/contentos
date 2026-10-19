from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.core.signing import signed_url
from app.repositories.assets import AssetRepository
from app.schemas.entities import AssetOut
from app.services.contents import ContentService


class AssetService:
    def __init__(self, session: AsyncSession):
        self.contents = ContentService(session)
        self.repo = AssetRepository(session)

    async def list_for_content(self, content_id: UUID) -> list[AssetOut]:
        await self.contents.get(content_id)
        s = get_settings()
        assets = await self.repo.find_for_content(content_id)
        return [
            AssetOut.model_validate(a).model_copy(update={
                "url": signed_url(s.assets_base_url, a.storage_key, s.artifact_secret, s.artifact_url_ttl)
                if s.assets_base_url else None
            })
            for a in assets
        ]
