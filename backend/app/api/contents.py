from uuid import UUID

from fastapi import APIRouter

from app.api.deps import Assets, Contents, Limit, Offset, Publications
from app.core.enums import ContentStatus
from app.schemas.common import ApiResponse, ok
from app.schemas.entities import (
    AssetOut,
    ContentCreate,
    ContentOut,
    ContentSummary,
    PublicationCreate,
    PublicationOut,
    PublishIn,
    StatusUpdate,
)

router = APIRouter(prefix="/contents", tags=["contents"])


@router.get("", response_model=ApiResponse[list[ContentSummary]])
async def list_contents(
    svc: Contents,
    project_id: UUID | None = None,
    status: ContentStatus | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    return ok(await svc.list(project_id, status, limit, offset))


@router.post("", response_model=ApiResponse[ContentOut], status_code=201)
async def create_content(data: ContentCreate, svc: Contents):
    return ok(await svc.create(data))


@router.get("/{content_id}", response_model=ApiResponse[ContentOut])
async def get_content(content_id: UUID, svc: Contents):
    return ok(await svc.get(content_id))


@router.get("/{content_id}/assets", response_model=ApiResponse[list[AssetOut]])
async def list_assets(content_id: UUID, svc: Assets):
    return ok(await svc.list_for_content(content_id))


@router.patch("/{content_id}/status", response_model=ApiResponse[ContentOut])
async def update_status(content_id: UUID, data: StatusUpdate, svc: Contents):
    return ok(await svc.transition(content_id, data.status))


@router.patch("/{content_id}/approve", response_model=ApiResponse[ContentOut])
async def approve(content_id: UUID, svc: Contents):
    return ok(await svc.transition(content_id, ContentStatus.APROBADO))


@router.patch("/{content_id}/reject", response_model=ApiResponse[ContentOut])
async def reject(content_id: UUID, svc: Contents):
    return ok(await svc.transition(content_id, ContentStatus.RECHAZADO))


@router.patch("/{content_id}/publish", response_model=ApiResponse[PublicationOut])
async def publish(content_id: UUID, data: PublishIn, svc: Publications):
    return ok(await svc.register(PublicationCreate(content_id=content_id, **data.model_dump())))


@router.patch("/{content_id}/retry", response_model=ApiResponse[ContentOut])
async def retry(content_id: UUID, svc: Contents):
    return ok(await svc.retry(content_id))


@router.patch("/{content_id}/regenerate", response_model=ApiResponse[ContentOut])
async def regenerate(content_id: UUID, svc: Contents):
    return ok(await svc.regenerate(content_id))
