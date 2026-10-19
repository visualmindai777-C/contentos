import dataclasses
import json
import re

from app.core.interfaces import LLMClient, ProviderError
from app.core.types import ContentDraft, LLMResponse, Message, ProjectContext

WORDS_PER_SECOND = 3  # medido con Kokoro en español: ~55 palabras ≈ 18 s
MIN_SCRIPT_WORDS = 30

SYSTEM = (
    "Eres guionista de vídeos cortos verticales (TikTok, Instagram Reels, Threads, X). "
    "Respondes SOLO con un objeto JSON válido, sin texto adicional ni markdown."
)

USER = """Proyecto: {name} — nicho: {niche}. Idioma: {language}. Tono: {tone}.
Tema en tendencia: {topic}
Palabras clave: {keywords}

Crea un vídeo de unos {seconds} segundos (≈{words} palabras de narración) que conecte el tema con el nicho como una curiosidad.
Devuelve exactamente este JSON:
{{"title": "título breve y llamativo (máx. 70 caracteres)",
"hook": "primera frase, engancha en 3 segundos",
"script": "narración completa en prosa, sin emojis ni marcado, que empieza por el hook y termina con el CTA",
"caption": "descripción del post (máx. 200 caracteres)",
"hashtags": ["#uno", "#dos"],
"cta": "llamada a la acción final"}}
Reglas: de 5 a 8 hashtags; datos verificables, sin inventar cifras; sin afirmaciones médicas ni políticas."""


class InvalidDraft(ProviderError):
    """El LLM respondió, pero no con el JSON esperado."""


def parse_draft(text: str) -> ContentDraft:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)  # modelos que razonan en voz alta
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise InvalidDraft("la respuesta no contiene JSON")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise InvalidDraft(f"JSON inválido: {e}") from e

    def field(key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise InvalidDraft(f"falta el campo '{key}'")
        return value.strip()

    script = field("script")
    if len(script.split()) < MIN_SCRIPT_WORDS:
        raise InvalidDraft("guion demasiado corto")
    raw = data.get("hashtags")
    if not isinstance(raw, list):
        raise InvalidDraft("falta el campo 'hashtags'")
    tags = list(dict.fromkeys("#" + t.strip().lstrip("#").replace(" ", "") for t in raw if isinstance(t, str) and t.strip("# ")))
    if not tags:
        raise InvalidDraft("sin hashtags válidos")
    return ContentDraft(
        title=field("title")[:100], hook=field("hook"), script=script,
        caption=field("caption")[:2200], hashtags=tags[:8], cta=field("cta"),
    )


class ContentAgent:
    """Una llamada LLM por contenido. Solo si la respuesta es inválida se hace un segundo (y último) intento."""

    def __init__(self, llm: LLMClient, max_attempts: int = 2):
        self._llm = llm
        self._max_attempts = max_attempts

    async def run(self, project: ProjectContext, topic: str, keywords: list[str]) -> tuple[ContentDraft, LLMResponse]:
        seconds = int(project.config.get("target_seconds", 40))
        prompt = USER.format(
            name=project.name, niche=project.niche or "general", language=project.language,
            tone=project.config.get("tone", "curioso, directo y cercano"), topic=topic,
            keywords=", ".join(keywords) or "—", seconds=seconds, words=seconds * WORDS_PER_SECOND,
        )
        messages = [Message("system", SYSTEM), Message("user", prompt)]

        tokens, last = 0, InvalidDraft("sin intentos")
        for _ in range(self._max_attempts):
            response = await self._llm.complete(messages, json_mode=True)
            tokens += response.tokens_used
            try:
                return parse_draft(response.text), dataclasses.replace(response, tokens_used=tokens)
            except InvalidDraft as e:
                last = e
        raise last
