import type { SystemLimits } from "./types";

export type Level = "ok" | "warn" | "danger";

const CONTENT_ALERT = 500;

export const ratioLevel = (ratio: number, warn: number, danger: number): Level =>
  ratio >= danger ? "danger" : ratio >= warn ? "warn" : "ok";

export function assess(l: SystemLimits) {
  const storage = l.estimated_storage_mb / l.storage_limit_mb;
  const llm = l.llm_calls_today / l.llm_daily_limit;
  const storageLevel = ratioLevel(storage, 0.7, 0.9);
  const llmLevel = ratioLevel(llm, 0.5, 0.8);
  const contentsLevel: Level = l.estimated_content_count > CONTENT_ALERT ? "warn" : "ok";

  const alerts = [...l.free_tier_warnings];
  if (storageLevel !== "ok" && !alerts.some((w) => w.startsWith("R2"))) {
    alerts.push(`R2 al ${Math.round(storage * 100)}% del límite gratuito`);
  }
  if (contentsLevel !== "ok") alerts.push(`Más de ${CONTENT_ALERT} contenidos: evalúa migrar a VPS`);

  const levels = [storageLevel, llmLevel, contentsLevel];
  const level: Level = levels.includes("danger") ? "danger" : levels.includes("warn") || alerts.length ? "warn" : "ok";
  return { storage, llm, storageLevel, llmLevel, contentsLevel, alerts, level };
}
