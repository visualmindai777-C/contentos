import Link from "next/link";
import { AutoRefresh } from "@/components/auto-refresh";
import { RunButton } from "@/components/run-button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatAgo } from "@/lib/utils";

export default async function ReviewPage() {
  const [generated, reviewed, ideas, scripts] = await Promise.all([
    api.contents({ status: "generado", limit: 50 }),
    api.contents({ status: "revisado", limit: 50 }),
    api.contents({ status: "idea", limit: 50 }),
    api.contents({ status: "guion", limit: 50 }),
  ]);
  const toReview = [...generated, ...reviewed].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  const failed = [...ideas, ...scripts].filter((c) => c.last_error);
  const cooking = [...ideas, ...scripts].filter((c) => !c.last_error);
  const progress = (status: string) => (status === "guion" ? 60 : 20);

  return (
    <>
      <h1 className="text-xl font-semibold">Revisar</h1>
      <AutoRefresh active={cooking.length > 0} />

      {failed.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-destructive">Necesitan atención ({failed.length})</h2>
          <Card className="divide-y border-red-300">
            {failed.map((c) => (
              <Link key={c.id} href={`/contents/${c.id}`} className="block px-4 py-3 hover:bg-muted">
                <p className="truncate font-medium">{c.title || "(pendiente de generar)"}</p>
                <p className="line-clamp-2 text-sm text-muted-foreground">{c.last_error}</p>
                <p className="mt-1 text-xs font-medium text-destructive">Toca para reintentar →</p>
              </Link>
            ))}
          </Card>
        </section>
      )}

      {cooking.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold">En proceso ({cooking.length}) · aún no se pueden revisar</h2>
          <Card className="divide-y">
            {cooking.map((c) => (
              <Link key={c.id} href={`/contents/${c.id}`} className="block space-y-2 px-4 py-3 hover:bg-muted">
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate font-medium">{c.title || "Tema en cola"}</p>
                  <Badge variant="info">{c.status === "guion" ? "Haciendo video" : "En cola"}</Badge>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={progress(c.status)} aria-valuemin={0} aria-valuemax={100}>
                  <div className="h-full animate-pulse rounded-full bg-amber-500" style={{ width: `${progress(c.status)}%` }} />
                </div>
              </Link>
            ))}
          </Card>
          <RunButton label="Generar ahora" />
        </section>
      )}

      <section className="space-y-2">
        <h2 className="text-sm font-semibold">Por revisar ({toReview.length})</h2>
        {toReview.length === 0 ? (
          <Card className="p-6 text-center">
            <p className="font-medium">{cooking.length ? "Aún no hay videos terminados" : "Todo al día"}</p>
            <p className="text-sm text-muted-foreground">{cooking.length ? "Los de arriba se están preparando; aparecerán aquí al terminar." : "Cuando se termine un video nuevo aparecerá aquí."}</p>
          </Card>
        ) : (
          <Card className="divide-y">
            {toReview.map((c) => (
              <Link key={c.id} href={`/contents/${c.id}`} className="flex min-h-16 items-center gap-3 px-4 py-3 hover:bg-muted">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{c.title}</p>
                  <p className="text-xs text-muted-foreground">{c.duration_seconds}s · {formatAgo(c.updated_at)}</p>
                </div>
                <Badge variant="warning">Ver y decidir</Badge>
              </Link>
            ))}
          </Card>
        )}
      </section>
    </>
  );
}
