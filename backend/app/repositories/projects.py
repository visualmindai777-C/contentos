from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.models import Project, User
from app.repositories.base import Repository


class ProjectRepository(Repository):
    async def find(self) -> Sequence[Project]:
        return (await self.session.scalars(select(Project).order_by(Project.created_at))).all()

    async def get(self, project_id: UUID) -> Project | None:
        return await self.session.get(Project, project_id)

    async def find_active(self) -> Sequence[Project]:
        query = select(Project).where(Project.is_active).order_by(Project.created_at)
        return (await self.session.scalars(query)).all()

    async def default_user_id(self, email: str) -> UUID | None:
        return await self.session.scalar(select(User.id).where(User.email == email))
