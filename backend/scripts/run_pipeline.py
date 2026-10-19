"""Entrypoint del pipeline (lo ejecuta el workflow de GitHub Actions): python scripts/run_pipeline.py --limit 3"""

import argparse
import asyncio
import json
import os
import sys
import time

from sqlalchemy import make_url, text

from app.agents.runner import BatchResult, run_batch
from app.container import build_agents, build_providers
from app.core.database import SessionLocal, engine
from app.core.logging import setup_logging
from app.core.interfaces import ProviderError
from app.core.settings import Settings, get_settings
from app.providers.llm_openrouter import missing_models


def write_summary(result: BatchResult) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    rows = [("Procesados", result.processed), ("Generados", result.generated), ("Fallidos", result.failed),
            ("Detenido por cuota LLM", "sí" if result.halted else "no")]
    lines = ["| | |", "|---|---|", *(f"| {k} | {v} |" for k, v in rows)]
    lines += ["", *(f"- {e}" for e in result.errors)]
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


async def drop_dead_models(settings: Settings) -> Settings:
    """Los modelos :free se retiran sin avisar: un ID muerto costaría una petición fallida en cada contenido."""
    try:
        dead = await missing_models(settings.openrouter_model_list)
    except ProviderError as e:  # sin catálogo no se puede comprobar: se sigue con la lista tal cual
        print(f"::warning::No se pudo comprobar el catálogo de OpenRouter: {e}", file=sys.stderr)
        return settings
    if dead:
        print(f"::warning::Modelos inexistentes en OpenRouter, descartados: {', '.join(dead)}", file=sys.stderr)
    alive = [m for m in settings.openrouter_model_list if m not in dead]
    return settings.model_copy(update={"openrouter_models": ",".join(alive)})


async def database_problem() -> str | None:
    """Comprueba la conexión antes de gastar nada. Nunca muestra la contraseña, solo a dónde y como quién se intenta entrar."""
    url = make_url(get_settings().database_url)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("select 1"))
    except Exception as e:
        detail = str(e).strip().splitlines()[0][:200] if str(e).strip() else type(e).__name__
        return (
            f"No se pudo conectar a la base de datos (usuario={url.username}, host={url.host}, puerto={url.port}, "
            f"base={url.database}). Con el pooler de Supabase el usuario debe ser postgres.<ref-del-proyecto> y la "
            f"contraseña la del proyecto. Detalle: {detail}"
        )
    return None


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3, help="contenidos por ejecución")
    parser.add_argument("--max-minutes", type=float, default=45, help="no empezar contenidos nuevos pasado este tiempo")
    parser.add_argument("--queue-only", action="store_true", help="solo la cola; no crear ideas nuevas desde tendencias")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging(settings.log_level)
    if problem := await database_problem():
        print(f"::error::{problem}", file=sys.stderr)
        await engine.dispose()
        return 2
    settings = await drop_dead_models(settings)
    if not settings.openrouter_model_list:
        print("::error::Ninguno de los modelos de OPENROUTER_MODELS existe ya en OpenRouter", file=sys.stderr)
        return 2
    try:
        agents = build_agents(build_providers(settings), SessionLocal, settings)
    except RuntimeError as e:  # credenciales ausentes
        print(f"::error::{e}", file=sys.stderr)
        return 2
    try:
        result = await run_batch(
            agents, limit=args.limit, deadline=time.monotonic() + args.max_minutes * 60, new_ideas=not args.queue_only
        )
    finally:
        await engine.dispose()

    write_summary(result)
    print(json.dumps(vars(result), ensure_ascii=False))
    # Rojo en Actions si la cuota del LLM se agotó o si se intentó trabajo y nada salió bien. El Worker de Cloudflare
    # no relanza el pipeline durante un rato tras un run rojo.
    if result.halted:
        return 3
    return 1 if result.processed and not result.generated else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
