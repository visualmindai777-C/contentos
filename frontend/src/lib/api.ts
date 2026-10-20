import { cache } from "react";
import type {
  Asset, Content, ContentSummary, DashboardStats, PipelineStatus, Project, Publication, SystemConfig, SystemLimits, Topic,
} from "./types";

// Solo se importa desde componentes de servidor y server actions: la API key nunca llega al navegador.
const BASE = process.env.BACKEND_URL ?? "http://localhost:7860";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

type Query = Record<string, string | number | undefined>;

const qs = (q: Query) => {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) if (v !== undefined && v !== "") params.set(k, String(v));
  const s = params.toString();
  return s ? `?${s}` : "";
};

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method,
    cache: "no-store",
    signal: AbortSignal.timeout(10_000),
    headers: { "content-type": "application/json", "x-api-key": process.env.API_KEY ?? "" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const json = await res.json().catch(() => null);
  if (!res.ok || !json?.success) throw new ApiError(json?.error ?? `HTTP ${res.status}`, res.status);
  return json.data as T;
}

const get = <T>(path: string) => request<T>("GET", path);
const patch = <T>(path: string, body?: unknown) => request<T>("PATCH", path, body);

export async function backendHealthy(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/health`, { cache: "no-store", signal: AbortSignal.timeout(4_000) });
    return res.ok;
  } catch {
    return false;
  }
}

// Estado del último run de GitHub Actions, vía el Worker de Cloudflare. Opcional: sin WORKER_URL o si falla, null.
async function pipelineStatus(): Promise<PipelineStatus | null> {
  const base = process.env.WORKER_URL;
  if (!base) return null;
  try {
    const res = await fetch(`${base}/status`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5_000),
      headers: { "x-api-key": process.env.API_KEY ?? "" },
    });
    return res.ok ? ((await res.json()) as PipelineStatus) : null;
  } catch {
    return null;
  }
}

// cache() de React deduplica llamadas repetidas dentro de una misma petición (layout + página).
export const api = {
  stats: cache(() => get<DashboardStats>("/dashboard/stats")),
  limits: cache(() => get<SystemLimits>("/system/limits")),
  projects: cache(() => get<Project[]>("/projects")),
  config: () => get<SystemConfig>("/system/config"),
  pipeline: cache(pipelineStatus),

  createProject: (b: { slug: string; name: string; niche: string }) => request<Project>("POST", "/projects", b),
  topics: (q: Query) => get<Topic[]>(`/topics${qs(q)}`),
  discoverTopics: (b: { project_id: string; mode: string }) => request<{ found: number; added: number }>("POST", "/topics/discover", b),
  createTopic: (b: { project_id: string; topic: string }) => request<Topic>("POST", "/topics", b),

  contents: (q: Query) => get<ContentSummary[]>(`/contents${qs(q)}`),
  content: (id: string) => get<Content>(`/contents/${id}`),
  assets: (id: string) => get<Asset[]>(`/contents/${id}/assets`),
  createContent: (b: { project_id: string; topic_id: string; title: string }) => request<Content>("POST", "/contents", b),
  approve: (id: string) => patch<Content>(`/contents/${id}/approve`),
  reject: (id: string) => patch<Content>(`/contents/${id}/reject`),
  regenerate: (id: string) => patch<Content>(`/contents/${id}/regenerate`),
  retry: (id: string) => patch<Content>(`/contents/${id}/retry`),
  publish: (id: string, b: { platform: string; published_at?: string; notes: string }) =>
    patch<Publication>(`/contents/${id}/publish`, b),

  publications: (q: Query) => get<Publication[]>(`/publications${qs(q)}`),
};
