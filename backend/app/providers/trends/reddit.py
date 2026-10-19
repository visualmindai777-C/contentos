import xml.etree.ElementTree as ET

import httpx

from app.core.interfaces import ProviderError
from app.core.types import ProjectContext, TrendCandidate
from app.providers.http_client import http_request
from app.providers.trends import extract_keywords

ATOM = "{http://www.w3.org/2005/Atom}"
# El JSON público de Reddit devuelve 403; el feed Atom de /top sí responde sin credenciales.
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


class RedditSource:
    """Top del día de los subreddits de project.config['subreddits']. El feed no trae votos: el score sale del ranking."""

    name = "reddit"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    async def fetch(self, project: ProjectContext, limit: int) -> list[TrendCandidate]:
        found: list[TrendCandidate] = []
        error: ProviderError | None = None
        for sub in project.config.get("subreddits", []):
            try:
                found += await self._top(sub, limit)
            except ProviderError as e:  # un subreddit caído no invalida el resto
                error = e
        if not found and error:
            raise error
        return sorted(found, key=lambda t: t.score, reverse=True)[:limit]

    async def _top(self, sub: str, limit: int) -> list[TrendCandidate]:
        resp = await http_request(
            "reddit", "GET", f"https://www.reddit.com/r/{sub}/top/.rss", transport=self._transport,
            params={"t": "day", "limit": limit}, headers={"User-Agent": USER_AGENT},
        )
        try:
            titles = [(e.findtext(f"{ATOM}title") or "").strip() for e in ET.fromstring(resp.text).iter(f"{ATOM}entry")]
        except ET.ParseError as e:
            raise ProviderError(f"reddit: feed inválido de r/{sub}") from e
        titles = [t for t in titles if t]
        return [
            TrendCandidate(topic=t, score=round(100 * (1 - i / len(titles)), 1), keywords=extract_keywords(t), source=self.name)
            for i, t in enumerate(titles)
        ]
