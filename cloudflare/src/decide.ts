export interface Run {
  status: string;
  conclusion: string | null;
  updated_at: string;
  html_url: string;
}

export type Trigger = "queue" | "fresh";

export interface Plan {
  dispatch: boolean;
  reason: string;
  inputs?: { limit: string; queue_only: string };
}

export const COOLDOWN_MS = 3 * 3600_000; // tras un run rojo (p. ej. cuota de OpenRouter agotada) no se relanza durante 3 h
export const MAX_PER_RUN = 3;

const ACTIVE = new Set(["queued", "in_progress", "waiting", "requested", "pending"]);
const FAILED = new Set(["failure", "timed_out"]);

/** Decide si lanzar el pipeline. Pura: `runs` son los últimos runs del workflow, el más reciente primero. */
export function decide(trigger: Trigger, pending: number, runs: Run[], now: number, freshLimit: number): Plan {
  if (runs.some((r) => ACTIVE.has(r.status))) return { dispatch: false, reason: "hay un run activo" };

  const last = runs.find((r) => r.status === "completed");
  if (last && FAILED.has(last.conclusion ?? "") && now - Date.parse(last.updated_at) < COOLDOWN_MS) {
    return { dispatch: false, reason: "enfriamiento tras un run fallido" };
  }

  if (trigger === "queue") {
    if (pending <= 0) return { dispatch: false, reason: "cola vacía" };
    return {
      dispatch: true,
      reason: `${pending} contenido(s) en cola`,
      inputs: { limit: String(Math.min(pending, MAX_PER_RUN)), queue_only: "true" },
    };
  }
  return {
    dispatch: true,
    reason: "contenido nuevo programado",
    inputs: { limit: String(freshLimit), queue_only: "false" },
  };
}
