import { serveArtifact, type ArtifactEnv } from "./artifacts.ts";
import { decide, type Trigger } from "./decide.ts";
import { dispatch, ensureEnabled, listRuns, type GithubEnv } from "./github.ts";

interface Env extends ArtifactEnv, GithubEnv {
  BACKEND_URL: string;
  API_KEY: string;
  FRESH_LIMIT?: string;
}

const FRESH_CRON = "17 */8 * * *"; // igual que el segundo cron de wrangler.toml

async function pendingInQueue(env: Env): Promise<number> {
  const res = await fetch(`${env.BACKEND_URL}/pipeline/queue`, {
    headers: { "x-api-key": env.API_KEY },
    signal: AbortSignal.timeout(90_000), // una API dormida (Render free) tarda en despertar
  });
  if (!res.ok) throw new Error(`backend /pipeline/queue: HTTP ${res.status}`);
  return ((await res.json()) as { data: { pending: number } }).data.pending;
}

async function tick(env: Env, trigger: Trigger): Promise<void> {
  // Consultar la cola no gasta Actions y, de paso, mantiene despiertos Render y Supabase.
  const pending = trigger === "queue" ? await pendingInQueue(env) : 0;
  if (trigger === "queue" && pending === 0) return console.log(JSON.stringify({ trigger, pending, dispatch: false, reason: "cola vacía" }));

  const plan = decide(trigger, pending, await listRuns(env), Date.now(), Number(env.FRESH_LIMIT ?? 3));
  console.log(JSON.stringify({ trigger, pending, ...plan }));
  if (plan.dispatch && plan.inputs) {
    await ensureEnabled(env);
    await dispatch(env, plan.inputs);
  }
}

function authorized(request: Request, env: Env): boolean {
  const given = new TextEncoder().encode(request.headers.get("x-api-key") ?? "");
  const expected = new TextEncoder().encode(env.API_KEY);
  return given.length === expected.length && crypto.subtle.timingSafeEqual(given, expected);
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(
      tick(env, event.cron === FRESH_CRON ? "fresh" : "queue").catch((e) => console.error(`tick falló: ${e}`)),
    );
  },

  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname.startsWith("/artifacts/")) return serveArtifact(request, env);

    // Estado del último run, para la tarjeta "Pipeline" del portal
    if (pathname === "/status") {
      if (!authorized(request, env)) return new Response("Unauthorized", { status: 401 });
      const runs = await listRuns(env).catch(() => null);
      if (!runs) return Response.json({ error: "GitHub no disponible" }, { status: 502 });
      const last = runs.find((r) => r.status === "completed");
      return Response.json({
        active: runs.some((r) => r.status !== "completed"),
        last: last && { conclusion: last.conclusion, updated_at: last.updated_at, url: last.html_url },
      });
    }

    // "Procesar ahora" desde el portal: lanza el pipeline sobre la cola sin esperar al cron
    if (pathname === "/run" && request.method === "POST") {
      if (!authorized(request, env)) return new Response("Unauthorized", { status: 401 });
      try {
        if ((await listRuns(env)).some((r) => r.status !== "completed")) {
          return Response.json({ started: false, message: "Ya se está generando algo ahora mismo." });
        }
        const pending = await pendingInQueue(env);
        if (pending === 0) return Response.json({ started: false, message: "No hay nada en cola." });
        await ensureEnabled(env);
        await dispatch(env, { limit: String(Math.min(pending, 3)), queue_only: "true" });
        return Response.json({ started: true, message: "Listo: empezó a generar. Tarda unos minutos." });
      } catch (e) {
        console.error(`/run falló: ${e}`);
        return Response.json({ started: false, message: "No se pudo iniciar. Reintenta en un momento." }, { status: 502 });
      }
    }
    return new Response("Not Found", { status: 404 });
  },
} satisfies ExportedHandler<Env>;
