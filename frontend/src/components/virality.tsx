import { Badge } from "@/components/ui/badge";

// El puntaje (0-100) combina el ranking en cada fuente y su peso; se traduce a una etiqueta fácil de leer.
export function viralityLabel(score: number): { label: string; variant: "success" | "warning" | "muted" } {
  if (score >= 70) return { label: "Alta", variant: "success" };
  if (score >= 40) return { label: "Media", variant: "warning" };
  return { label: "Baja", variant: "muted" };
}

export function Virality({ score }: { score: number }) {
  const { label, variant } = viralityLabel(score);
  return (
    <span className="inline-flex items-center gap-2">
      <Badge variant={variant}>{label}</Badge>
      <span className="text-xs text-muted-foreground">{Math.round(score)}/100</span>
    </span>
  );
}
