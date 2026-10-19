import hmac

from fastapi import Header

from app.core.errors import Unauthorized
from app.core.settings import get_settings


async def require_api_key(x_api_key: str = Header(default="")) -> None:
    expected = get_settings().api_key
    if expected and not hmac.compare_digest(x_api_key.encode(), expected.encode()):
        raise Unauthorized("API key inválida")
