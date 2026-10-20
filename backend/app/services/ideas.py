import json
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFound, TooManyRequests
from app.core.interfaces import LLMClient, ProviderError, RateLimitError
from app.core.settings import get_settings
from app.core.screenplay import parse_screenplay
from app.core.types import Message
from app.models import Content, Project, Topic

MIN_SCORE = 50  # por debajo, aunque el modelo diga que sí, no se crea: el score manda
MAX_PROMPT = 4000

SYSTEM = (
    "Eres productor de videos cortos verticales (TikTok, Instagram Reels, YouTube Shorts) y evalúas ideas antes de "
    "producirlas. Respondes SOLO con un objeto JSON válido, sin texto adicional."
)

USER = """Proyecto: {name} (formato: {format}, idioma: {language}).
Idea del usuario (puede ser una idea suelta, instrucciones o un guion ya escrito con PERSONAJES / ESCENA / diálogos):
\"\"\"{prompt}\"\"\"

Evalúa si es VIABLE producirla como un video de ~40 segundos con estas herramientas: guion con diálogos de 1 a 3 personajes
ficticios, una imagen por escena en estilo caricatura 3D y voz sintética. Criterios:
- Seguridad de plataforma: sin odio, acoso, violencia gráfica, contenido sexual, desinformación médica o política, ni
  difamación de personas reales o marcas. Sin personajes ni obras con derechos de autor.
- Producible: se puede contar en 4 escenas con un gancho en 3 segundos y un final que invite a ver más.
- Potencial: interesa a una audiencia amplia y puede monetizarse (retención, comentarios, serie).
Responde exactamente este JSON:
{{"viable": true o false,
"score": entero de 0 a 100 (potencial de audiencia y monetización si es seguro; bajo si no es viable),
"reason": "1 o 2 frases claras para el usuario, en español",
"risks": ["riesgos o problemas concretos, vacío si no hay"],
"title": "título llamativo de máx. 70 caracteres (si es viable)",
"hook": "la primera frase que se dice en el video (si es viable)",
"caption": "descripción del post, máx. 200 caracteres, con pregunta para comentar (si es viable)",
"hashtags": ["#uno", "#dos"],
"improvement": "cómo reformularla para que funcione mejor (si no es viable, o una mejora si lo es)"}}"""


def parse_verdict(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    start, end = text.find("{"), text.rfind("}")
    try:
        data = json.loads(text[start : end + 1])
        viable = bool(data["viable"])
        score = max(0, min(100, int(data.get("score", 0))))
    except (ValueError, KeyError, TypeError) as e:
        raise ProviderError("la IA no devolvió una evaluación válida") from e
    risks = [str(r) for r in data.get("risks") or [] if r]
    tags = data.get("hashtags") if isinstance(data.get("hashtags"), list) else []
    hashtags = list(dict.fromkeys("#" + str(t).strip().lstrip("#").replace(" ", "") for t in tags if str(t).strip("# ")))[:8]
    return {
        "hook": str(data.get("hook", "")).strip(), "caption": str(data.get("caption", "")).strip()[:2200], "hashtags": hashtags,
        "viable": viable and score >= MIN_SCORE, "score": score, "reason": str(data.get("reason", "")).strip(),
        "risks": risks[:5], "title": str(data.get("title", "")).strip()[:100], "improvement": str(data.get("improvement", "")).strip(),
    }


class IdeaService:
    """Evalúa la idea de un usuario con el LLM y, solo si es viable, la deja en la cola de producción."""

    def __init__(self, session: AsyncSession, llm: LLMClient | None = None):
        self.session = session
        self._llm = llm

    def _client(self) -> LLMClient:
        if self._llm is None:
            s = get_settings()
            if not s.openrouter_api_key:
                raise AppError("La API no tiene configurada la clave de la IA")
            from app.providers.llm_openrouter import OpenRouterClient  # httpx solo se carga si hace falta

            self._llm = OpenRouterClient(s.openrouter_api_key, s.openrouter_model_list)
        return self._llm

    async def evaluate(self, project_id: UUID, prompt: str) -> dict:
        prompt = prompt.strip()[:MAX_PROMPT]
        project = await self.session.get(Project, project_id)
        if project is None:
            raise NotFound("Proyecto inexistente")
        message = USER.format(
            name=project.name, format=(project.config or {}).get("format", "narración"), language=project.language, prompt=prompt,
        )
        try:
            response = await self._client().complete(
                [Message("system", SYSTEM), Message("user", message)], json_mode=True, max_tokens=2000,
            )
            verdict = parse_verdict(response.text)
        except RateLimitError as e:
            raise TooManyRequests("La IA gratuita está saturada ahora mismo. Intenta de nuevo en unos minutos.") from e
        except ProviderError as e:
            raise AppError(f"No se pudo evaluar la idea: {e}") from e

        verdict["content_id"], verdict["mode"] = None, "guion" if parse_screenplay(prompt) else "idea"
        if verdict["viable"]:
            verdict["content_id"] = str(await self._enqueue(project_id, prompt, verdict, response))
        # Estos campos solo sirven para crear el contenido
        for key in ("hook", "caption", "hashtags"):
            verdict.pop(key)
        return verdict

    async def _enqueue(self, project_id: UUID, prompt: str, verdict: dict, response) -> UUID:
        """Un guion ya escrito va directo a imágenes, voz y video. Una idea o instrucciones entran como tema oculto
        (source='idea', no aparece en Temas) y el pipeline escribe el guion siguiéndolas al pie de la letra."""
        if parse_screenplay(prompt):
            content = Content(
                project_id=project_id, title=verdict["title"], hook=verdict["hook"], script=prompt,
                caption=verdict["caption"], hashtags=verdict["hashtags"], cta="Sígueme para ver la siguiente parte",
                status="guion", llm_provider=response.provider, model_name=response.model, tokens_used=response.tokens_used,
            )
        else:
            topic = await self.session.scalar(select(Topic).where(Topic.project_id == project_id, Topic.topic == prompt))
            if topic is None:
                topic = Topic(project_id=project_id, topic=prompt, keywords=[], source="idea", score=100)
                self.session.add(topic)
                await self.session.flush()
            content = Content(project_id=project_id, topic_id=topic.id, title=verdict["title"])
        self.session.add(content)
        await self.session.commit()
        return content.id
