import re

import httpx

from app.core.interfaces import ProviderError, RateLimitError

_BODY_RETRY = re.compile(r"retry after (\d+(?:\.\d+)?)\s*s", re.IGNORECASE)


def _retry_after(resp: httpx.Response) -> float | None:
    # El cuerpo manda: Pollinations envía "Retry-After: 1" en la cabecera pero pide esperar decenas de segundos.
    if match := _BODY_RETRY.search(resp.text):
        return float(match.group(1))
    try:
        return float(resp.headers["retry-after"])
    except (KeyError, ValueError):
        return None


async def http_request(
    provider: str, method: str, url: str, *, transport: httpx.AsyncBaseTransport | None = None,
    timeout: float = 60.0, rate_limit_statuses: tuple[int, ...] = (429,), **kwargs,
) -> httpx.Response:
    """Una petición HTTP con el mapeo de errores común a todos los providers (429 → RateLimitError).

    rate_limit_statuses permite a un provider declarar otros códigos de cuota (Pollinations usa 402).
    """
    try:
        async with httpx.AsyncClient(transport=transport, timeout=timeout, follow_redirects=True) as client:
            resp = await client.request(method, url, **kwargs)
    except httpx.HTTPError as e:
        raise ProviderError(f"{provider}: {e!r}") from e
    if resp.status_code in rate_limit_statuses:
        raise RateLimitError(f"{provider}: HTTP {resp.status_code} {resp.text[:120]}", _retry_after(resp))
    if resp.is_error:
        raise ProviderError(f"{provider}: HTTP {resp.status_code} {resp.text[:200]}")
    return resp
