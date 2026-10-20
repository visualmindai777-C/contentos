import dataclasses
import json
import re

from app.core.interfaces import LLMClient, ProviderError
from app.core.blocklist import banned_terms, find_banned
from app.core.screenplay import parse_screenplay
from app.core.types import ContentDraft, LLMResponse, Message, ProjectContext

WORDS_PER_SECOND = 3  # medido con Kokoro en español: ~55 palabras ≈ 18 s
MIN_SCRIPT_WORDS = 30
MAX_TOKENS = 4000  # el JSON ocupa ~400; el resto es margen para modelos que razonan antes de responder

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


NOVELA_USER = """Proyecto: {name}. Idioma de los diálogos: {language}. Tono: {tone}.
Tema en tendencia: {topic}
Palabras clave: {keywords}

Escribe el guion de una MINI NOVELA de unos {seconds} segundos (≈{words} palabras en total entre todos los diálogos) para TikTok, Reels y Shorts, inspirada en el tema, con personajes ficticios.
Reglas:
- La primera línea es un gancho que impacta en 3 segundos (una revelación, una acusación, un secreto).
- 4 escenas. Un giro dentro de la historia y un final abierto (cliffhanger) que deje con ganas de la parte 2.
- Frases cortas y naturales, como se habla (máx. 18 palabras por línea). Máx. 3 personajes, más un NARRADOR opcional.
- Sin datos reales de personas ni marcas. Sin violencia gráfica ni contenido sexual.

El campo "script" es texto con saltos de línea y este formato EXACTO:
PERSONAJES
NOMBRE | f | aspecto físico y ropa en inglés (pelo, edad, ropa de un color)
NOMBRE | m | aspecto físico y ropa en inglés
ESCENA | descripción visual en inglés de UN solo personaje, plano medio, con su aspecto completo, el lugar y la emoción
NOMBRE: lo que dice
NOMBRE: lo que dice
ESCENA | otra descripción visual en inglés
NOMBRE: lo que dice
(la letra f o m indica la voz: f femenina, m masculina)

Devuelve exactamente este JSON:
{{"title": "título llamativo que termine en (Parte 1), máx. 70 caracteres",
"hook": "la primera frase de la historia",
"script": "el guion con el formato indicado",
"caption": "descripción del post, máx. 200 caracteres, con pregunta para comentar",
"hashtags": ["#uno", "#dos"],
"cta": "Sígueme para ver la parte 2"}}
5 a 8 hashtags."""


NOVELA_NEXT_USER = """Proyecto: {name}. Idioma de los diálogos: {language}. Tono: {tone}.
Estás escribiendo una SERIE de mini novelas para TikTok, Reels y Shorts. Esto es lo que ya pasó:

{previous}

Escribe la PARTE {part} (≈{words} palabras en total entre todos los diálogos, unos {seconds} segundos).
Reglas:
- Continúa EXACTAMENTE donde terminó la parte anterior, con los mismos personajes. Copia sus descripciones del bloque PERSONAJES tal cual, para que se vean igual.
- La primera línea es un gancho que recapitula en 3 segundos lo último que pasó y engancha ("Anoche descubrí que...").
- 4 escenas. Resuelve el final abierto anterior, y {ending}
- Frases cortas y naturales (máx. 18 palabras por línea). Máx. 3 personajes, más un NARRADOR opcional.
- Sin datos reales de personas ni marcas. Sin violencia gráfica ni contenido sexual.

El campo "script" es texto con saltos de línea y este formato EXACTO:
PERSONAJES
NOMBRE | f | aspecto físico y ropa en inglés (el mismo de las partes anteriores)
ESCENA | descripción visual en inglés de UN solo personaje, plano medio, con su aspecto completo, el lugar y la emoción
NOMBRE: lo que dice
(la letra f o m indica la voz: f femenina, m masculina)

Devuelve exactamente este JSON:
{{"title": "título de la serie que termine en (Parte {part}), máx. 70 caracteres",
"hook": "la primera frase de esta parte",
"script": "el guion con el formato indicado",
"caption": "descripción del post, máx. 200 caracteres, con pregunta para comentar",
"hashtags": ["#uno", "#dos"],
"cta": "{cta}"}}
5 a 8 hashtags."""

DEFAULT_MAX_PARTS = 5

USER_INSTRUCTIONS = """INSTRUCCIONES DEL USUARIO (tienen prioridad sobre cualquier regla de abajo sobre personajes, escenas, tono, duración o formato; síguelas al pie de la letra y conserva sus nombres, hechos y orden):
\"\"\"{topic}\"\"\"

"""


class InvalidDraft(ProviderError):
    """El LLM respondió, pero no con el JSON esperado."""


def parse_draft(text: str, novela: bool = False, banned: tuple[str, ...] = ()) -> ContentDraft:
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
    if novela and parse_screenplay(script) is None:
        raise InvalidDraft("el guion no sigue el formato de novela (PERSONAJES / ESCENA / diálogos)")
    if hit := find_banned(" ".join(str(data.get(k, "")) for k in ("title", "hook", "script", "caption")), banned):
        raise InvalidDraft(f"menciona «{hit}», un término vetado")
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

    async def run(
        self, project: ProjectContext, topic: str, keywords: list[str], *, previous: str = "", part: int = 1, instructions: bool = False,
        recent: tuple[str, ...] = (),
    ) -> tuple[ContentDraft, LLMResponse]:
        seconds = int(project.config.get("target_seconds", 40))
        novela = project.config.get("format") == "novela"
        if novela and previous:
            final = part >= int(project.config.get("series_parts", DEFAULT_MAX_PARTS))
            prompt = NOVELA_NEXT_USER.format(
                name=project.name, language=project.language, previous=previous[-6000:], part=part,
                tone=project.config.get("tone", "dramático, intrigante y emocional"), seconds=seconds, words=seconds * WORDS_PER_SECOND,
                ending="CIERRA la historia con un final satisfactorio: es la última parte." if final
                else "termina con un nuevo final abierto (cliffhanger) que deje con ganas de la parte siguiente.",
                cta="Gracias por seguir la serie" if final else "Sígueme para ver la siguiente parte",
            )
            messages = [Message("system", SYSTEM), Message("user", prompt + self._guard(recent))]
            return await self._complete(messages, novela, banned_terms(project.config))
        prompt = (NOVELA_USER if novela else USER).format(
            name=project.name, niche=project.niche or "general", language=project.language,
            tone=project.config.get("tone", "curioso, directo y cercano"), topic=topic,
            keywords=", ".join(keywords) or "—", seconds=seconds, words=seconds * WORDS_PER_SECOND,
        )
        if instructions:
            prompt = USER_INSTRUCTIONS.format(topic=topic) + prompt
        prompt += self._guard(recent)
        messages = [Message("system", SYSTEM), Message("user", prompt)]
        return await self._complete(messages, novela, () if instructions else banned_terms(project.config))

    @staticmethod
    def _guard(recent: tuple[str, ...]) -> str:
        """Reglas finales contra el sesgo del modelo: nada de obras ajenas y nada de repetirse."""
        text = "\n\nAdemás: no menciones ni imites series, películas, libros, videojuegos, marcas ni personajes existentes (por ejemplo Mr. Robot); inventa personajes, nombres y situaciones propios."
        if recent:
            text += " Ya hicimos estos videos, así que NO repitas sus personajes, nombres, giros ni escenarios: " + "; ".join(recent) + "."
        return text

    async def _complete(
        self, messages: list[Message], novela: bool, banned: tuple[str, ...] = (),
    ) -> tuple[ContentDraft, LLMResponse]:
        tokens, last = 0, InvalidDraft("sin intentos")
        for _ in range(self._max_attempts):
            response = await self._llm.complete(messages, json_mode=True, max_tokens=MAX_TOKENS)
            tokens += response.tokens_used
            try:
                return parse_draft(response.text, novela, banned), dataclasses.replace(response, tokens_used=tokens)
            except InvalidDraft as e:
                last = e
        raise last
