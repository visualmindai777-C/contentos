from datetime import UTC, datetime, timedelta

import httpx

from app.core.interfaces import ProviderError
from app.core.types import ProjectContext, TrendCandidate
from app.providers.http_client import http_request
from app.providers.trends import extract_keywords, log_score

URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{lang}.wikipedia/all-access/{day:%Y/%m/%d}"
USER_AGENT = "ContentOS/0.1 (trend research; open source)"


class WikipediaSource:
    """Artículos más vistos de Wikipedia en el idioma del proyecto (API abierta, sin clave)."""

    name = "wikipedia"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    async def fetch(self, project: ProjectContext, limit: int) -> list[TrendCandidate]:
        day = datetime.now(UTC) - timedelta(days=2)  # el día anterior aún no siempre está publicado
        resp = await http_request(
            "wikipedia", "GET", URL.format(lang=project.language, day=day),
            transport=self._transport, headers={"User-Agent": USER_AGENT},
        )
        try:
            articles = resp.json()["items"][0]["articles"]
        except (ValueError, KeyError, IndexError) as e:
            raise ProviderError("wikipedia: respuesta inesperada") from e

        found = []
        for a in articles:
            title = a["article"].replace("_", " ")
            if ":" in a["article"] or a["article"] in {"Portada", "Main_Page", "-"}:  # páginas especiales
                continue
            found.append(TrendCandidate(
                topic=title, score=log_score(a["views"], 1_000, 500_000), keywords=extract_keywords(title), source=self.name,
            ))
        return found[:limit]
