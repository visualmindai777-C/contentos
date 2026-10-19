import type { Run } from "./decide.ts";

export interface GithubEnv {
  GITHUB_TOKEN: string;
  GITHUB_REPO: string;
  GITHUB_REF: string;
  GITHUB_API?: string; // solo para pruebas / GitHub Enterprise
}

const WORKFLOW = "pipeline.yml";

function call(env: GithubEnv, path: string, init: RequestInit = {}): Promise<Response> {
  const base = env.GITHUB_API ?? "https://api.github.com";
  return fetch(`${base}/repos/${env.GITHUB_REPO}/actions/workflows/${WORKFLOW}${path}`, {
    ...init,
    signal: AbortSignal.timeout(15_000),
    headers: {
      authorization: `Bearer ${env.GITHUB_TOKEN}`,
      accept: "application/vnd.github+json",
      "x-github-api-version": "2022-11-28",
      "user-agent": "contentos-worker",
    },
  });
}

async function check(res: Response, what: string): Promise<Response> {
  if (!res.ok) throw new Error(`GitHub ${what}: HTTP ${res.status} ${(await res.text()).slice(0, 200)}`);
  return res;
}

export async function listRuns(env: GithubEnv): Promise<Run[]> {
  const res = await check(await call(env, "/runs?per_page=5"), "listar runs");
  return ((await res.json()) as { workflow_runs: Run[] }).workflow_runs;
}

/** GitHub desactiva los workflows tras 60 días sin actividad en el repo; se reactiva antes de lanzarlo. */
export async function ensureEnabled(env: GithubEnv): Promise<void> {
  const workflow = (await (await check(await call(env, ""), "leer workflow")).json()) as { state: string };
  if (workflow.state.startsWith("disabled_inactivity")) {
    await check(await call(env, "/enable", { method: "PUT" }), "reactivar workflow");
  }
}

export async function dispatch(env: GithubEnv, inputs: { limit: string; queue_only: string }): Promise<void> {
  await check(
    await call(env, "/dispatches", {
      method: "POST",
      body: JSON.stringify({ ref: env.GITHUB_REF, inputs }),
    }),
    "lanzar workflow",
  );
}
