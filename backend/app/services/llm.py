from app.core.errors import AppError
from app.core.interfaces import LLMClient
from app.core.settings import get_settings


def make_llm() -> LLMClient:
    """Cliente del LLM de la API (la clave llega por variable de entorno). httpx solo se carga si hace falta."""
    s = get_settings()
    if not s.openrouter_api_key:
        raise AppError("La API no tiene configurada la clave de la IA")
    from app.providers.llm_openrouter import OpenRouterClient

    return OpenRouterClient(s.openrouter_api_key, s.openrouter_model_list)
