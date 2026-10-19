from fastapi import APIRouter

from app.api.deps import Dashboard, Usage
from app.schemas.common import ApiResponse, ok
from app.schemas.entities import DashboardStats, QueueStatus, SystemConfig, SystemLimits

router = APIRouter(tags=["monitoring"])


@router.get("/dashboard/stats", response_model=ApiResponse[DashboardStats])
async def dashboard_stats(svc: Dashboard):
    return ok(await svc.stats())


@router.get("/pipeline/queue", response_model=ApiResponse[QueueStatus])
async def pipeline_queue(svc: Dashboard):
    return ok(await svc.queue())


@router.get("/system/limits", response_model=ApiResponse[SystemLimits])
async def system_limits(svc: Usage):
    return ok(await svc.limits())


@router.get("/system/config", response_model=ApiResponse[SystemConfig])
async def system_config(svc: Usage):
    return ok(svc.config())
