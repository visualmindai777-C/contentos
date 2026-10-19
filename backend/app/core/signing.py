"""URLs firmadas de artefactos. El Worker de Cloudflare valida la misma firma (HMAC-SHA256) antes de servir desde R2."""

import hashlib
import hmac
import time


def signature(secret: str, key: str, exp: int) -> str:
    return hmac.new(secret.encode(), f"{key}\n{exp}".encode(), hashlib.sha256).hexdigest()


def signed_url(base: str, key: str, secret: str, ttl: int, now: float | None = None) -> str:
    """Sin secreto devuelve la URL sin firmar (solo desarrollo: el Worker rechazará la petición)."""
    url = f"{base.rstrip('/')}/{key}"
    if not secret:
        return url
    exp = int((time.time() if now is None else now) + ttl)
    return f"{url}?exp={exp}&sig={signature(secret, key, exp)}"
