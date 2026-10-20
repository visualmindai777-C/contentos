from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.assets import AssetService
from app.services.contents import ContentService
from app.services.dashboard import DashboardService
from app.services.discovery import DiscoveryService
from app.services.ideas import IdeaService
from app.services.projects import ProjectService
from app.services.revision import RevisionService
from app.services.publications import PublicationService
from app.services.topics import TopicService
from app.services.usage import UsageService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def provide(service_cls):
    def dependency(session: SessionDep):
        return service_cls(session)

    return Depends(dependency)


Projects = Annotated[ProjectService, provide(ProjectService)]
Topics = Annotated[TopicService, provide(TopicService)]
Contents = Annotated[ContentService, provide(ContentService)]
Assets = Annotated[AssetService, provide(AssetService)]
Publications = Annotated[PublicationService, provide(PublicationService)]
Dashboard = Annotated[DashboardService, provide(DashboardService)]
Discovery = Annotated[DiscoveryService, provide(DiscoveryService)]
Ideas = Annotated[IdeaService, provide(IdeaService)]
Revisions = Annotated[RevisionService, provide(RevisionService)]
Usage = Annotated[UsageService, provide(UsageService)]

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
