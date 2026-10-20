from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query

from pydantic import BaseModel

from app.api.deps import Discovery, Limit, Offset, Topics
from app.schemas.common import ApiResponse, ok
from app.services.discovery import Mode
from app.schemas.entities import TopicCreate, TopicOut

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=ApiResponse[list[TopicOut]])
async def list_topics(
    svc: Topics, project_id: UUID | None = None, limit: Limit = 50, offset: Offset = 0,
    sort: Literal["recent", "score"] = "recent", days: int | None = Query(default=None, ge=1, le=90),
):
    return ok(await svc.list(project_id, limit, offset, sort, days))


@router.post("", response_model=ApiResponse[TopicOut], status_code=201)
async def create_topic(data: TopicCreate, svc: Topics):
    return ok(await svc.create(data))


@router.delete("/{topic_id}", response_model=ApiResponse[dict[str, bool]])
async def delete_topic(topic_id: UUID, svc: Topics):
    await svc.delete(topic_id)
    return ok({"deleted": True})


class ClearRequest(BaseModel):
    project_id: UUID


@router.post("/clear", response_model=ApiResponse[dict[str, int]])
async def clear_topics(data: ClearRequest, svc: Topics):
    """Descarta de una vez las tendencias que no usaste."""
    return ok({"removed": await svc.clear_unused(data.project_id)})


class DiscoverRequest(BaseModel):
    project_id: UUID
    mode: Mode = "viral"


@router.post("/discover", response_model=ApiResponse[dict[str, int]])
async def discover_topics(data: DiscoverRequest, svc: Discovery):
    return ok(await svc.discover(data.project_id, data.mode))
