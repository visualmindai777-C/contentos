import { Badge } from "@/components/ui/badge";
import { levelVariant } from "@/components/status-badge";
import { assess } from "@/lib/limits";
import type { SystemLimits } from "@/lib/types";

export function Header({ healthy, limits }: { healthy: boolean; limits: SystemLimits | null }) {
  const a = limits ? assess(limits) : null;
  return (
    <header className="flex items-center gap-2 border-b border-brand/30 bg-primary px-4 py-2.5 text-primary-foreground">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/logo-horizontal.png" alt="VisualMind AI·777" width={720} height={102} className="mr-auto h-7 w-auto md:hidden" />
      <span className="mr-auto hidden text-sm text-primary-foreground/70 md:block">Panel de producción</span>
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
