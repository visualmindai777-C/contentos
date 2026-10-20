"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { ApiError, api } from "@/lib/api";

// Devuelven el mensaje de error del backend (o undefined/"" si todo fue bien): en producción
// Next oculta los errores lanzados desde server actions.
const message = (e: unknown) => (e instanceof ApiError ? e.message : "Error inesperado");
const refresh = () => revalidatePath("/", "layout");

async function run(fn: () => Promise<unknown>): Promise<string | undefined> {
  try {
    await fn();
  } catch (e) {
    return message(e);
  }
  refresh();
}

export async function approve(id: string) {
  return run(() => api.approve(id));
}

export async function reject(id: string) {
  return run(() => api.reject(id));
}

export async function purge(id: string) {
  try {
    await api.purge(id);
  } catch (e) {
    return message(e);
  }
  refresh();
  redirect("/contents?status=rechazado");
}

export async function regenerate(id: string) {
  return run(() => api.regenerate(id));
}

export async function retry(id: string) {
  return run(() => api.retry(id));
}

export async function discoverTrends(projectId: string, mode: string): Promise<string> {
  try {
    const { found, added } = await api.discoverTopics({ project_id: projectId, mode });
    refresh();
    return added ? `${added} tendencias nuevas (de ${found} encontradas)` : `Sin novedades: ya tenías las ${found} tendencias encontradas`;
  } catch (e) {
    return message(e);
  }
}

export async function createContentFromTopic(projectId: string, topicId: string, title: string) {
  let id: string;
  try {
    id = (await api.createContent({ project_id: projectId, topic_id: topicId, title })).id;
  } catch (e) {
    return message(e);
  }
  refresh();
  redirect(`/contents/${id}`);
}

export async function publish(id: string, _prev: string, form: FormData): Promise<string> {
  const date = String(form.get("date") ?? "");
  const error = await run(() =>
    api.publish(id, {
      platform: String(form.get("platform")),
      published_at: date ? `${date}T12:00:00Z` : undefined,
      notes: String(form.get("notes") ?? ""),
    }),
  );
  return error ?? "";
}

export async function createTopic(_prev: string, form: FormData): Promise<string> {
  const error = await run(() =>
    api.createTopic({ project_id: String(form.get("project_id")), topic: String(form.get("topic")).trim() }),
  );
  return error ?? "";
}

export async function createProject(_prev: string, form: FormData): Promise<string> {
  const error = await run(() =>
    api.createProject({
      slug: String(form.get("slug")).trim(),
      name: String(form.get("name")).trim(),
      niche: String(form.get("niche") ?? "").trim(),
    }),
  );
  return error ?? "";
}
