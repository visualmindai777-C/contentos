import asyncio
import logging
from collections.abc import Sequence

from app.core.interfaces import ProviderError, TrendSource
from app.core.text import extract_keywords
from app.core.types import ProjectContext, TrendCandidate

logger = logging.getLogger("app.pipeline")

# Wikipedia y Google no distinguen nichos: pesan menos que una fuente que el proyecto eligió (subreddits).
DEFAULT_WEIGHTS = {"reddit": 1.0, "google_trends": 0.9, "wikipedia": 0.5, "hackernews": 0.8}
RELEVANCE_BONUS = 10  # por palabra clave del proyecto presente en el tema (máx. 3)


class TrendAgent:
    """Detecta tendencias sin LLM: consulta las fuentes en paralelo, tolera fallos y ordena por score ponderado."""

    def __init__(self, sources: Sequence[TrendSource], per_source: int = 10, keep: int = 20):
        self._sources = sources
        self._per_source = per_source
        self._keep = keep

    async def discover(self, project: ProjectContext) -> list[TrendCandidate]:
        results = await asyncio.gather(
            *(s.fetch(project, self._per_source) for s in self._sources), return_exceptions=True
        )
        found: list[TrendCandidate] = []
        for source, result in zip(self._sources, results):
            if isinstance(result, BaseException):
                logger.warning("trend source failed", extra={"fields": {"source": source.name, "error": repr(result)[:200]}})
            else:
                found += result
        if not found and all(isinstance(r, BaseException) for r in results):
            raise ProviderError("todas las fuentes de tendencias fallaron")
        return self._rank(project, found)

    def _rank(self, project: ProjectContext, candidates: list[TrendCandidate]) -> list[TrendCandidate]:
        weights = {**DEFAULT_WEIGHTS, **project.config.get("source_weights", {})}
        terms = set(extract_keywords(" ".join([project.niche, *project.config.get("keywords", [])]), limit=50))
        best: dict[str, TrendCandidate] = {}
        for c in candidates:
            bonus = min(3, len(terms & set(c.keywords))) * RELEVANCE_BONUS
            score = min(100.0, round(c.score * weights.get(c.source, 1.0) + bonus, 1))
            key = c.topic.casefold()
            if key not in best or score > best[key].score:
                best[key] = TrendCandidate(c.topic, score, c.keywords, c.source, c.summary)
        return sorted(best.values(), key=lambda c: c.score, reverse=True)[: self._keep]
