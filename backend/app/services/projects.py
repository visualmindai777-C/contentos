from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.core.settings import get_settings
from app.models import Project
from app.repositories.projects import ProjectRepository
from app.schemas.entities import ProjectCreate


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ProjectRepository(session)

    async def list(self) -> Sequence[Project]:
        return await self.repo.find()

    async def create(self, data: ProjectCreate) -> Project:
        user_id = await self.repo.default_user_id(get_settings().default_user_email)
        if user_id is None:
            raise NotFound("Usuario por defecto inexistente: aplica db/schema.sql")
        project = await self.repo.save(Project(user_id=user_id, **data.model_dump()))
        await self.session.commit()
        return project
