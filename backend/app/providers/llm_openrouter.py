import logging
from collections.abc import Sequence

import httpx

from app.core.interfaces import ProviderError, RateLimitError
from app.core.types import LLMResponse, Message
from app.providers.http_client import http_request

logger = logging.getLogger("app.pipeline")

URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS_URL = "https://openrouter.ai/api/v1/models"


async def missing_models(models: Sequence[str], *, transport: httpx.AsyncBaseTransport | None = None) -> list[str]:
    """IDs configurados que OpenRouter ya no publica. El catálogo es público: no consume cuota ni necesita clave."""
    resp = await http_request("openrouter", "GET", MODELS_URL, transport=transport, timeout=30.0)
    try:
        known = {m["id"] for m in resp.json()["data"]}
    except (ValueError, KeyError, TypeError) as e:
        raise ProviderError("openrouter: catálogo de modelos ilegible") from e
    return [m for m in models if m not in known]


class OpenRouterClient:
    """Prueba los modelos en orden de prioridad; cada intento es una petición contra la cuota diaria."""

    def __init__(
        self, api_key: str, models: Sequence[str], *, transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 90.0,
    ):
        self._api_key = api_key
        self._models = list(models)
        self._transport = transport
        self._timeout = timeout

    async def complete(
        self, messages: Sequence[Message], *, json_mode: bool = False, max_tokens: int = 1200
    ) -> LLMResponse:
        last: ProviderError | None = None
        limited: RateLimitError | None = None
        for model in self._models:
            try:
                return await self._call(model, messages, json_mode, max_tokens)
            except ProviderError as e:
                # Sin este rastro no se sabe por qué se cae al siguiente modelo (cuota, modelo retirado, JSON, vacío...)
                logger.warning("openrouter model failed", extra={"fields": {"model": model, "error": str(e)[:240]}})
                last = e
                if isinstance(e, RateLimitError):
                    limited = e
        # Si algún modelo estaba solo "temporalmente limitado", el fallo es transitorio y no del contenido: el llamador
        # lo trata como cuota agotada (se detiene el lote y se reintenta luego) en vez de marcar el contenido como fallido.
        if limited:
            raise RateLimitError(f"todos los modelos fallaron; alguno limitado: {limited}", limited.retry_after) from last
        raise last or ProviderError("openrouter: sin modelos configurados")

    async def _call(self, model: str, messages: Sequence[Message], json_mode: bool, max_tokens: int) -> LLMResponse:
        payload: dict = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        # Los modelos que razonan gastan max_tokens pensando y devuelven vacío; se pide poco razonamiento (los demás lo ignoran)
        payload["reasoning"] = {"effort": "low"}
        resp = await http_request(
            "openrouter", "POST", URL, transport=self._transport, timeout=self._timeout,
            headers={"Authorization": f"Bearer {self._api_key}", "X-Title": "Content OS"}, json=payload,
        )
        try:
            data = resp.json()
        except ValueError as e:
            raise ProviderError(f"openrouter({model}): respuesta no JSON") from e

        if "error" in data:  # OpenRouter a veces responde 200 con el error en el cuerpo
            err = data["error"] if isinstance(data["error"], dict) else {"message": str(data["error"])}
            if err.get("code") == 429:
                raise RateLimitError(f"openrouter({model}): {err.get('message', '429')}")
            raise ProviderError(f"openrouter({model}): {err.get('message', err)}")
        try:
            choice = data["choices"][0]
            text = choice["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"openrouter({model}): respuesta sin choices") from e
        if not text.strip():
            finish = choice.get("finish_reason")
            hint = " (agotó max_tokens razonando)" if finish == "length" else ""
            raise ProviderError(f"openrouter({model}): respuesta vacía, finish_reason={finish}{hint}")
        tokens = int((data.get("usage") or {}).get("total_tokens") or 0)
        return LLMResponse(text=text, provider="openrouter", model=model, tokens_used=tokens)
