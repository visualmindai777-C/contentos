import asyncio
import html
import re
import xml.etree.ElementTree as ET

import httpx

from app.core.interfaces import ProviderError
from app.core.types import ProjectContext, TrendCandidate
from app.providers.http_client import http_request
from app.providers.trends import extract_keywords

SPACING = 1.5  # segundos entre subreddits
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
        for i, sub in enumerate(project.config.get("subreddits", [])):
            if i:
                await asyncio.sleep(SPACING)  # Reddit responde 429 a ráfagas de peticiones sin credenciales
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
            entries = [
                ((e.findtext(f"{ATOM}title") or "").strip(), e.findtext(f"{ATOM}content") or "")
                for e in ET.fromstring(resp.text).iter(f"{ATOM}entry")
            ]
        except ET.ParseError as e:
            raise ProviderError(f"reddit: feed inválido de r/{sub}") from e
        entries = [(t, c) for t, c in entries if t]
        return [
            TrendCandidate(
                topic=t, score=round(100 * (1 - i / len(entries)), 1), keywords=extract_keywords(t), source=self.name,
                summary=self._summary(sub, c),
            )
            for i, (t, c) in enumerate(entries)
        ]

    @staticmethod
    def _summary(sub: str, content: str) -> str:
        """Texto del post si lo tiene (los enlaces solo traen 'submitted by'); si no, de dónde viene."""
        text = html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(content)))
        text = re.sub(r"submitted by.*$|\[link\]|\[comments\]", " ", text, flags=re.DOTALL)
        text = re.sub(r"\s+", " ", text).strip()
        return f"{text[:240]} (r/{sub})" if len(text) >= 25 else f"Entre lo más votado hoy en r/{sub}"
