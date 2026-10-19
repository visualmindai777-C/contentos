import { Meter } from "@/components/meter";
import { assess } from "@/lib/limits";
import type { SystemLimits } from "@/lib/types";
import { formatMB } from "@/lib/utils";

export function FreeTierMonitor({ limits }: { limits: SystemLimits | null }) {
  if (!limits) return <p className="text-xs text-muted-foreground">Límites no disponibles</p>;
  const a = assess(limits);

  return (
    <div className="space-y-3 rounded-lg border p-3 text-xs">
      <p className="font-semibold">Free tier</p>
      <div>
        <div className="flex justify-between">
          <span>Contenidos</span>
          <span className={a.contentsLevel === "ok" ? "" : "font-semibold text-amber-600"}>{limits.estimated_content_count}</span>
        </div>
      </div>
      <div className="space-y-1">
        <div className="flex justify-between">
          <span>R2</span>
          <span>{formatMB(limits.estimated_storage_mb)} / {formatMB(limits.storage_limit_mb)}</span>
        </div>
        <Meter ratio={a.storage} level={a.storageLevel} />
      </div>
      <div className="space-y-1">
        <div className="flex justify-between">
          <span>OpenRouter hoy</span>
          <span>~{limits.llm_calls_today} / {limits.llm_daily_limit}</span>
        </div>
        <Meter ratio={a.llm} level={a.llmLevel} />
      </div>
      {a.alerts.length > 0 && (
        <ul className="space-y-1 text-amber-700">
          {a.alerts.map((w) => (
            <li key={w}>⚠ {w}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
