from fastapi import APIRouter, Depends

from app.api import contents, health, monitoring, projects, publications, topics
from app.core.security import require_api_key

protected = APIRouter(dependencies=[Depends(require_api_key)])
for module in (monitoring, projects, topics, contents, publications):
    protected.include_router(module.router)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(protected)
