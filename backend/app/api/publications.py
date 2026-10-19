from uuid import UUID

from fastapi import APIRouter

from app.api.deps import Limit, Offset, Publications
from app.schemas.common import ApiResponse, ok
from app.schemas.entities import PublicationCreate, PublicationOut

router = APIRouter(prefix="/publications", tags=["publications"])


@router.get("", response_model=ApiResponse[list[PublicationOut]])
async def list_publications(svc: Publications, content_id: UUID | None = None, limit: Limit = 50, offset: Offset = 0):
    return ok(await svc.list(content_id, limit, offset))


@router.post("", response_model=ApiResponse[PublicationOut], status_code=201)
async def create_publication(data: PublicationCreate, svc: Publications):
    return ok(await svc.register(data))
