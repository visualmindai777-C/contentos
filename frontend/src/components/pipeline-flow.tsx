import Link from "next/link";
import { RunButton } from "@/components/run-button";
import type { DashboardStats } from "@/lib/types";
import { cn } from "@/lib/utils";

// El camino completo de un video, con cuántos hay en cada paso y qué hace el sistema ahora mismo.
export function PipelineFlow({ stats, generating }: { stats: DashboardStats; generating: boolean }) {
  const waiting = Math.max(0, stats.queued - stats.scripted);
  const steps = [
    { label: "En cola", n: waiting, href: "/review", tone: "amber" },
    { label: "Haciendo video", n: stats.scripted, href: "/review", tone: "amber" },
    { label: "Por revisar", n: stats.review, href: "/review", tone: "blue" },
    { label: "Aprobados", n: stats.approved, href: "/contents?status=aprobado", tone: "green" },
    { label: "Publicados", n: stats.published, href: "/contents?status=publicado", tone: "green" },
  ] as const;
  const colors = { amber: "bg-amber-100 text-amber-900", blue: "bg-blue-100 text-blue-900", green: "bg-green-100 text-green-900" };

  return (
    <section className="space-y-3 rounded-lg border bg-card p-4" aria-label="Cómo va todo">
      <h2 className="font-semibold">Cómo va todo</h2>
      <ol className="grid grid-cols-5 gap-1.5">
        {steps.map((s) => (
          <li key={s.label}>
            <Link href={s.href} className="flex h-full flex-col items-center gap-1 rounded-lg p-1 text-center active:bg-muted">
              <span className={cn("flex h-11 w-full items-center justify-center rounded-lg text-xl font-semibold", s.n ? colors[s.tone] : "bg-muted text-muted-foreground")}>
                {s.n}
              </span>
              <span className="text-[11px] leading-tight">{s.label}</span>
            </Link>
          </li>
        ))}
      </ol>

      {generating ? (
        <p className="flex items-center gap-2 text-sm font-medium" role="status">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-green-500" />
          Generando ahora… esta pantalla se actualiza sola.
        </p>
      ) : stats.queued > 0 ? (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            {stats.queued} {stats.queued === 1 ? "video espera" : "videos esperan"} su turno. Se generan solos cada pocos minutos.
          </p>
          <RunButton label="Generar ahora" />
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          {stats.failed ? "Hay contenidos con error: míralos en Revisar." : "Nada en proceso. Busca tendencias en Temas para crear más videos."}
        </p>
      )}
    </section>
  );
}
