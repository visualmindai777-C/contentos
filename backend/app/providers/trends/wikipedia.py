import asyncio
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import httpx

from dataclasses import replace

from app.core.interfaces import ProviderError
from app.core.types import ProjectContext, TrendCandidate
from app.providers.http_client import http_request
from app.providers.trends import extract_keywords, log_score

URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{lang}.wikipedia/all-access/{day:%Y/%m/%d}"
# Wikimedia exige un User-Agent descriptivo con datos de contacto (https://w.wiki/4wJS); sin ellos responde 403
USER_AGENT = "ContentOS/0.1 (https://github.com/visualmindai777-C/contentos; trend research) httpx"


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
        top = found[:limit]
        summaries = await asyncio.gather(*(self._extract(project.language, c.topic) for c in top))
        return [replace(c, summary=s) for c, s in zip(top, summaries)]

    async def _extract(self, lang: str, title: str) -> str:
        """Primer párrafo del artículo. Si falla, el tema se queda sin resumen: no es motivo para perder la tendencia."""
        try:
            resp = await http_request(
                "wikipedia", "GET", f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'), safe='')}",
                transport=self._transport, headers={"User-Agent": USER_AGENT},
            )
            text = str(resp.json().get("extract", "")).strip()
        except (ProviderError, ValueError):
            return ""
        return text if len(text) <= 260 else text[:260].rsplit(" ", 1)[0] + "…"
