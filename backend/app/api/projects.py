from fastapi import APIRouter

from app.api.deps import Projects
from app.schemas.common import ApiResponse, ok
from app.schemas.entities import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ApiResponse[list[ProjectOut]])
async def list_projects(svc: Projects):
    return ok(await svc.list())


@router.post("", response_model=ApiResponse[ProjectOut], status_code=201)
async def create_project(data: ProjectCreate, svc: Projects):
    return ok(await svc.create(data))
