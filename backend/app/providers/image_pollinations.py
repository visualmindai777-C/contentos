from urllib.parse import quote

import httpx

from app.core.interfaces import ProviderError, RateLimitError
from app.core.types import GeneratedImage
from app.providers.http_client import http_request

BASE_URL = "https://image.pollinations.ai/prompt"
ANONYMOUS_WINDOW = 45.0


class PollinationsProvider:
    def __init__(
        self, token: str = "", *, model: str = "flux", base_url: str = BASE_URL,
        transport: httpx.AsyncBaseTransport | None = None, timeout: float = 120.0,
    ):
        self._token = token
        self._model = model
        self.base_url = base_url
        self._transport = transport
        self._timeout = timeout

    async def generate(
        self, prompt: str, *, width: int = 1080, height: int = 1920, seed: int | None = None
    ) -> GeneratedImage:
        params: dict = {"width": width, "height": height, "model": self._model, "nologo": "true"}
        if seed is not None:
            params["seed"] = seed
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        try:
            resp = await http_request(
                "pollinations", "GET", f"{self.base_url}/{quote(prompt[:500], safe='')}",
                transport=self._transport, timeout=self._timeout, params=params, headers=headers,
                rate_limit_statuses=(402, 429),  # sin clave: 1 imagen cada 45 s por IP, avisado con 402 FREE_LIMIT
            )
        except RateLimitError as e:
            if self._token:
                raise
            # Su "Retry after 1s" no es fiable (sigue bloqueando segundos después): se respeta la ventana real.
            raise RateLimitError(str(e), max(e.retry_after or 0.0, ANONYMOUS_WINDOW)) from e
        mime = resp.headers.get("content-type", "").split(";")[0].strip()
        if not mime.startswith("image/") or not resp.content:
            raise ProviderError(f"pollinations: respuesta no es una imagen ({mime or 'sin content-type'})")
        return GeneratedImage(data=resp.content, mime_type=mime)
