from dataclasses import replace
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.trend_agent import TrendAgent
from app.core.errors import NotFound
from app.core.types import ProjectContext
from app.models import Project
from app.providers.trends.google import GoogleTrendsSource
from app.providers.trends.hackernews import HackerNewsSource
from app.providers.trends.reddit import RedditSource
from app.providers.trends.wikipedia import WikipediaSource
from app.repositories.topics import TopicRepository

Mode = Literal["viral", "monetizable", "nicho"]

# viral: lo más visto hoy, sin filtrar por nicho. monetizable: nichos de CPM alto (finanzas, negocios, tecnología, salud, productividad).
SUBREDDITS: dict[str, list[str]] = {
    "viral": ["popular", "todayilearned", "interestingasfuck", "Damnthatsinteresting", "nextfuckinglevel"],
    "monetizable": ["personalfinance", "investing", "Entrepreneur", "technology", "productivity", "Fitness"],
}


def context_for(project: Project, mode: Mode) -> ProjectContext:
    """'nicho' respeta la configuración del proyecto; los otros modos ignoran su nicho para ampliar el alcance."""
    ctx = ProjectContext(project.id, project.name, project.niche, project.language, dict(project.config))
    if mode == "nicho":
        return ctx
    return replace(ctx, niche="", config={**ctx.config, "subreddits": SUBREDDITS[mode], "keywords": []})


class DiscoveryService:
    """Busca tendencias a demanda (sin LLM, sin credenciales) y guarda las nuevas como temas."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def discover(self, project_id: UUID, mode: Mode) -> dict[str, int]:
        project = await self.session.get(Project, project_id)
        if project is None:
            raise NotFound("Proyecto inexistente")
        # Google y Wikipedia traen deportes y famosos: solo sirven para "lo más visto"; Reddit puede limitar (429) y Hacker News lo cubre, no para temas que monetizan
        sources = [HackerNewsSource(), RedditSource()] if mode == "monetizable" else [GoogleTrendsSource(), RedditSource(), WikipediaSource()]
        agent = TrendAgent(sources, per_source=15, keep=25)
        found = await agent.discover(context_for(project, mode))
        added = await TopicRepository(self.session).add_new(project_id, found)
        await self.session.commit()
        return {"found": len(found), "added": added}
