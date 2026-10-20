from urllib.parse import urlparse

import httpx

from app.core.interfaces import ProviderError
from app.core.types import ProjectContext, TrendCandidate
from app.providers.http_client import http_request
from app.providers.trends import extract_keywords, log_score

URL = "https://hn.algolia.com/api/v1/search"


class HackerNewsSource:
    """Portada de Hacker News (tecnología, negocios, finanzas). API abierta sin clave y de una sola petición."""

    name = "hackernews"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    async def fetch(self, project: ProjectContext, limit: int) -> list[TrendCandidate]:
        resp = await http_request(
            "hackernews", "GET", URL, transport=self._transport, params={"tags": "front_page", "hitsPerPage": limit},
        )
        try:
            hits = resp.json()["hits"]
        except (ValueError, KeyError) as e:
            raise ProviderError("hackernews: respuesta inesperada") from e
        return [
            TrendCandidate(
                topic=h["title"].strip(), score=log_score(h.get("points") or 0, 10, 1_000),
                keywords=extract_keywords(h["title"]), source=self.name,
                summary=f"{h.get('points') or 0} puntos y {h.get('num_comments') or 0} comentarios en Hacker News"
                + (f" · {urlparse(h['url']).netloc.removeprefix('www.')}" if h.get("url") else ""),
            )
            for h in hits if h.get("title")
        ]
