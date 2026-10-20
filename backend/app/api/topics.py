from uuid import UUID

from fastapi import APIRouter

from pydantic import BaseModel

from app.api.deps import Discovery, Limit, Offset, Topics
from app.schemas.common import ApiResponse, ok
from app.services.discovery import Mode
from app.schemas.entities import TopicCreate, TopicOut

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=ApiResponse[list[TopicOut]])
async def list_topics(svc: Topics, project_id: UUID | None = None, limit: Limit = 50, offset: Offset = 0):
    return ok(await svc.list(project_id, limit, offset))


@router.post("", response_model=ApiResponse[TopicOut], status_code=201)
async def create_topic(data: TopicCreate, svc: Topics):
    return ok(await svc.create(data))


class DiscoverRequest(BaseModel):
    project_id: UUID
    mode: Mode = "viral"


@router.post("/discover", response_model=ApiResponse[dict[str, int]])
async def discover_topics(data: DiscoverRequest, svc: Discovery):
    return ok(await svc.discover(data.project_id, data.mode))
