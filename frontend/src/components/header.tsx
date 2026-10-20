import { Badge } from "@/components/ui/badge";
import { levelVariant } from "@/components/status-badge";
import { assess } from "@/lib/limits";
import type { SystemLimits } from "@/lib/types";

export function Header({ healthy, limits }: { healthy: boolean; limits: SystemLimits | null }) {
  const a = limits ? assess(limits) : null;
  return (
    <header className="flex items-center gap-2 border-b bg-card px-4 py-2.5">
      <span className="mr-auto font-semibold md:hidden">Content OS</span>
      <Badge variant={healthy ? "success" : "danger"}>{healthy ? "Conectado" : "Sin conexión"}</Badge>
      {a && limits && (
        <>
          <Badge variant={levelVariant[a.storageLevel]} className="hidden sm:inline-flex">Almacenamiento {Math.round(a.storage * 100)}%</Badge>
          <Badge variant={a.alerts.length ? "warning" : "success"} title={a.alerts.join("\n")}>
            {a.alerts.length ? `${a.alerts.length} aviso(s)` : "Sin avisos"}
          </Badge>
        </>
      )}
    </header>
  );
}
