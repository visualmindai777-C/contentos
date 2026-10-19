import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from app.agents.content_agent import ContentAgent
from app.agents.media_agent import MediaAgent
from app.agents.state import PipelineState
from app.agents.storage_agent import StorageAgent
from app.agents.trend_agent import TrendAgent
from app.core.interfaces import RateLimitError

logger = logging.getLogger("app.pipeline")


@dataclass(frozen=True, slots=True)
class Agents:
    trend: TrendAgent
    content: ContentAgent
    media: MediaAgent
    storage: StorageAgent


def build_graph(agents: Agents):
    """load → [trend → intake →] content → media → store.

    contents.status decide dónde se entra: 'idea' empieza en content, 'guion' (ya tiene guion) salta a media,
    y sin contenido se parte de las tendencias (reutilizando temas ya guardados antes de volver a consultar fuentes).
    """
    storage = agents.storage

    def guarded(name: str, fn):
        async def node(state: PipelineState) -> dict:
            try:
                return await fn(state)
            except Exception as e:
                logger.warning(
                    "node failed",
                    extra={"fields": {"node": name, "content_id": str(state.get("content_id")), "error": repr(e)[:300]}},
                    exc_info=not isinstance(e, RateLimitError),
                )
                message = f"{name}: {e}"
                # La cuota agotada no es culpa del contenido: sigue en cola y el run queda en rojo (exit 3).
                # Marcarlo fallido vaciaría la cola uno por ciclo mientras dure el límite diario.
                if state.get("content_id") and not isinstance(e, RateLimitError):
                    await storage.mark_failed(state["content_id"], message)
                return {"error": message, "halt": name == "content" and isinstance(e, RateLimitError)}

        return node

    async def load(state: PipelineState) -> dict:
        if content_id := state.get("content_id"):
            job = await storage.load_job(content_id)
            update = {"project": job.project, "status": job.status, "topic": job.topic, "keywords": job.keywords}
            return update | ({"draft": job.draft} if job.draft else {})
        return {"has_unused": await storage.has_unused_topic(state["project"].id)}

    async def trend(state: PipelineState) -> dict:
        return {"candidates": await agents.trend.discover(state["project"])}

    async def intake(state: PipelineState) -> dict:
        project = state["project"]
        if candidates := state.get("candidates"):
            await storage.save_topics(project.id, candidates)
        opened = await storage.open_idea(project.id)
        if opened is None:
            return {"error": "intake: no hay temas disponibles"}
        content_id, topic, keywords = opened
        return {"content_id": content_id, "status": "idea", "topic": topic, "keywords": keywords}

    async def content(state: PipelineState) -> dict:
        draft, llm = await agents.content.run(state["project"], state["topic"], state["keywords"])
        await storage.save_draft(state["content_id"], draft, llm)
        return {"draft": draft, "llm": llm, "status": "guion"}

    async def media(state: PipelineState) -> dict:
        workdir = Path(tempfile.mkdtemp(prefix="contentos-"))
        try:
            bundle = await agents.media.run(state["project"], state["topic"], state["draft"], workdir)
        except BaseException:
            shutil.rmtree(workdir, ignore_errors=True)
            raise
        return {"media": bundle, "workdir": workdir}

    async def store(state: PipelineState) -> dict:
        try:
            await storage.save_media(state["content_id"], state["media"], state["topic"])
        finally:
            shutil.rmtree(state["workdir"], ignore_errors=True)
        return {"status": "generado"}

    def route_load(state: PipelineState) -> str:
        if state.get("error"):
            return END
        if state.get("content_id"):
            return "media" if state["status"] == "guion" else "content"
        return "intake" if state.get("has_unused") else "trend"

    def proceed(target: str):
        return lambda state: END if state.get("error") else target

    graph = StateGraph(PipelineState)
    for name, fn in [("load", load), ("trend", trend), ("intake", intake), ("content", content), ("media", media), ("store", store)]:
        graph.add_node(name, guarded(name, fn))
    graph.add_edge(START, "load")
    graph.add_conditional_edges("load", route_load, ["trend", "intake", "content", "media", END])
    graph.add_conditional_edges("trend", proceed("intake"), ["intake", END])
    graph.add_conditional_edges("intake", proceed("content"), ["content", END])
    graph.add_conditional_edges("content", proceed("media"), ["media", END])
    graph.add_conditional_edges("media", proceed("store"), ["store", END])
    graph.add_edge("store", END)
    return graph.compile()
