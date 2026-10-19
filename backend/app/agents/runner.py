import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from app.agents.graph import Agents, build_graph

logger = logging.getLogger("app.pipeline")


@dataclass
class BatchResult:
    processed: int = 0
    generated: int = 0
    failed: int = 0
    halted: bool = False
    errors: list[str] = field(default_factory=list)


async def run_batch(
    agents: Agents, *, limit: int, project_ids: Sequence[UUID] | None = None, deadline: float | None = None,
    new_ideas: bool = True,
) -> BatchResult:
    """Procesa hasta `limit` contenidos en una sola ejecución (el arranque en frío de Actions se amortiza).

    Primero la cola (regeneraciones, ideas manuales, guiones pendientes de media) y, si sobra cupo y
    new_ideas=True, ideas nuevas repartidas entre los proyectos activos. Con new_ideas=False solo se atiende
    lo que alguien pidió, sin gastar cuota de LLM en contenido no solicitado. `deadline` es un instante de time.monotonic().
    """
    result = BatchResult()
    projects = await agents.storage.active_projects(project_ids)
    if not projects:
        return result

    jobs: list[dict] = [{"content_id": cid} for cid in await agents.storage.queue(limit, project_ids)]
    if new_ideas:
        jobs += [{"project": projects[i % len(projects)]} for i in range(max(0, limit - len(jobs)))]

    graph = build_graph(agents)
    for job in jobs:
        if deadline is not None and time.monotonic() > deadline:
            logger.info("deadline reached, stopping batch")
            break
        final = await graph.ainvoke(job)
        result.processed += 1
        if final.get("status") == "generado" and not final.get("error"):
            result.generated += 1
        else:
            result.failed += 1
            result.errors.append(final.get("error", "sin estado final"))
        if final.get("halt"):
            result.halted = True
            break
    return result
