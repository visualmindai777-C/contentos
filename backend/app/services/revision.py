import re
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Conflict, NotFound, TooManyRequests
from app.core.interfaces import LLMClient, ProviderError, RateLimitError
from app.core.screenplay import parse_screenplay
from app.core.types import Message
from app.models import Content, Project
from app.services.llm import make_llm

SYSTEM = "Eres editor de guiones de videos cortos. Corriges guiones con precisión y devuelves solo el guion, sin explicaciones."

USER = """Guion actual (idioma de los diálogos: {language}):
\"\"\"
{script}
\"\"\"

Instrucción del usuario:
\"\"\"{instruction}\"\"\"

Aplica la instrucción cambiando SOLO lo necesario y deja igual todo lo demás. Conserva exactamente el formato del guion
(si tiene bloques PERSONAJES / ESCENA y líneas "NOMBRE: texto", mantenlos tal cual). Devuelve únicamente el guion completo corregido,
sin comillas, sin markdown y sin comentarios."""


def clean(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return re.sub(r"^```\w*\n|\n```$", "", text).strip()


class RevisionService:
    """Propone el guion corregido según una instrucción en lenguaje natural. No guarda nada: el usuario lo revisa y lo aplica."""

    def __init__(self, session: AsyncSession, llm: LLMClient | None = None):
        self.session = session
        self._llm = llm

    async def propose(self, content_id: UUID, instruction: str) -> dict[str, str]:
        content = await self.session.get(Content, content_id)
        if content is None:
            raise NotFound("Contenido no encontrado")
        if not content.script:
            raise Conflict("Este contenido todavía no tiene guion")
        project = await self.session.get(Project, content.project_id)
        message = USER.format(language=project.language, script=content.script, instruction=instruction.strip())
        try:
            response = await (self._llm or make_llm()).complete(
                [Message("system", SYSTEM), Message("user", message)], max_tokens=4000,
            )
        except RateLimitError as e:
            raise TooManyRequests("La IA gratuita está saturada ahora mismo. Intenta de nuevo en unos minutos.") from e
        except ProviderError as e:
            raise AppError(f"No se pudo corregir el guion: {e}") from e
        script = clean(response.text)
        if len(script.split()) < 10:
            raise AppError("La IA no devolvió un guion válido: reformula la instrucción")
        if (project.config or {}).get("format") == "novela" and parse_screenplay(script) is None:
            raise AppError("La IA rompió el formato del guion (PERSONAJES / ESCENA / diálogos): reformula la instrucción")
        return {"script": script}
