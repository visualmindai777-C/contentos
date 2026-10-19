import re
import xml.etree.ElementTree as ET

import httpx

from app.core.interfaces import ProviderError
from app.core.types import ProjectContext, TrendCandidate
from app.providers.http_client import http_request
from app.providers.trends import extract_keywords, log_score

URL = "https://trends.google.com/trending/rss"
NS = {"ht": "https://trends.google.com/trending/rss"}
DEFAULT_GEO = {"es": "ES", "en": "US"}
_TRAFFIC = re.compile(r"([\d.,]+)\s*([KkMm]?)")


def _traffic(text: str) -> float:
    m = _TRAFFIC.search(text or "")
    if not m:
        return 0.0
    digits = re.sub(r"\D", "", m.group(1))
    return float(digits or 0) * {"": 1, "k": 1_000, "m": 1_000_000}[m.group(2).lower()]


class GoogleTrendsSource:
    """Búsquedas en tendencia del día (feed RSS oficial: no usa pytrends, que Google limita con 429)."""

    name = "google_trends"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    async def fetch(self, project: ProjectContext, limit: int) -> list[TrendCandidate]:
        geo = project.config.get("geo") or DEFAULT_GEO.get(project.language, "US")
        resp = await http_request("google_trends", "GET", URL, transport=self._transport, params={"geo": geo})
        try:
            items = ET.fromstring(resp.text).findall("./channel/item")
        except ET.ParseError as e:
            raise ProviderError("google_trends: RSS inválido") from e

        found = []
        for item in items:
            topic = (item.findtext("title") or "").strip()
            if not topic:
                continue
            news = item.findtext("ht:news_item/ht:news_item_title", default="", namespaces=NS)
            found.append(TrendCandidate(
                topic=topic,
                score=log_score(_traffic(item.findtext("ht:approx_traffic", default="", namespaces=NS)), 100, 1_000_000),
                keywords=extract_keywords(f"{topic} {news}"),
                source=self.name,
            ))
        return sorted(found, key=lambda t: t.score, reverse=True)[:limit]
