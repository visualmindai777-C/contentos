import { cn } from "@/lib/utils";
import type { Status } from "@/lib/types";

const steps = ["Idea", "Guion", "Video", "Revisión", "Aprobado", "Publicado"];
const index: Record<Status, number> = { idea: 0, guion: 1, generado: 2, revisado: 3, aprobado: 4, publicado: 5, rechazado: -1 };

// Dónde va este contenido en el camino hasta publicarse. Los pasos hechos se rellenan; el actual se resalta.
export function Stepper({ status }: { status: Status }) {
  const current = index[status];
  if (current < 0) return null;
  return (
    <ol className="flex items-center gap-1" aria-label="Progreso del contenido">
      {steps.map((label, i) => {
        const done = i < current || status === "publicado";
        const active = i === current && status !== "publicado";
        return (
          <li key={label} className="flex min-w-0 flex-1 flex-col items-center gap-1">
            <span className={cn("h-1.5 w-full rounded-full", done ? "bg-green-500" : active ? "animate-pulse bg-amber-500" : "bg-muted")} />
            <span className={cn("truncate text-[10px] leading-none", active ? "font-semibold" : "text-muted-foreground")}>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
