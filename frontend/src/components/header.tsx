import { Badge } from "@/components/ui/badge";
import { levelVariant } from "@/components/status-badge";
import { assess } from "@/lib/limits";
import type { SystemLimits } from "@/lib/types";

export function Header({ healthy, limits }: { healthy: boolean; limits: SystemLimits | null }) {
  const a = limits ? assess(limits) : null;
  return (
    <header className="flex flex-wrap items-center gap-2 border-b bg-card px-4 py-2">
      <Badge variant={healthy ? "success" : "danger"}>Backend {healthy ? "activo" : "no responde"}</Badge>
      {a && limits ? (
        <>
          <Badge variant={levelVariant[a.storageLevel]}>R2 {Math.round(a.storage * 100)}%</Badge>
          <Badge variant={a.alerts.length ? "warning" : "success"} title={a.alerts.join("\n")}>
            {a.alerts.length ? `${a.alerts.length} advertencia(s)` : "Sin advertencias"}
          </Badge>
        </>
      ) : (
        <Badge variant="muted">Límites no disponibles</Badge>
      )}
    </header>
  );
}
