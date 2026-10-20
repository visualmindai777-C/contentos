import Link from "next/link";
import { AutoRefresh } from "@/components/auto-refresh";
import { PipelineFlow } from "@/components/pipeline-flow";
import { Meter } from "@/components/meter";
import { levelVariant } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { assess } from "@/lib/limits";
import { formatAgo, formatMB } from "@/lib/utils";

const semaphore = { ok: "Verde", warn: "Amarillo", danger: "Rojo" } as const;

export default async function DashboardPage() {
  // Si /system/limits responde, Supabase está conectado (la consulta pasa por la BD).
  const [stats, limits, pipeline] = await Promise.all([api.stats(), api.limits(), api.pipeline()]);
  const a = assess(limits);
  const last = pipeline?.last;

  const cards = [
    ["Temas", stats.topics],
    ["Generados", stats.total],
    ["En cola", stats.queued],
    ["Con error", stats.failed],
    ["Por revisar", stats.review],
    ["Aprobados", stats.approved],
    ["Publicados", stats.published],
    ["Rechazados", stats.rejected],
  ];

  return (
    <>
      <h1 className="text-xl font-semibold">Inicio</h1>
      <AutoRefresh active={!!pipeline?.active || stats.queued > 0} />
      <PipelineFlow stats={stats} generating={!!pipeline?.active} />
      <div className="grid gap-3 sm:grid-cols-2">
        <Link href="/review" className="rounded-lg border bg-card p-4 hover:bg-muted">
          <p className="text-3xl font-semibold">{stats.review}</p>
          <p className="font-medium">{stats.review === 1 ? "video listo para revisar" : "videos listos para revisar"}</p>
          <p className="text-sm text-muted-foreground">{stats.review ? "Toca para verlos y decidir →" : "Aún no hay videos terminados"}</p>
        </Link>
        <Link href="/review" className={`rounded-lg border bg-card p-4 hover:bg-muted ${stats.failed ? "border-red-300" : ""}`}>
          <p className="text-3xl font-semibold">{stats.failed}</p>
          <p className="font-medium">con error</p>
          <p className="text-sm text-muted-foreground">{stats.failed ? "Toca para reintentar →" : "Todo funcionando"}</p>
        </Link>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
        {cards.map(([label, value]) => (
          <Card key={label}>
            <CardContent>
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-2xl font-semibold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardTitle>Generación de videos</CardTitle>
          <CardContent className="space-y-2 text-sm">
            {!pipeline ? (
              <p className="text-muted-foreground">Sin datos (define WORKER_URL y revisa el Worker).</p>
            ) : (
              <>
                {pipeline.active && <Badge variant="info">En ejecución</Badge>}
                {last ? (
                  <p>
                    <Badge variant={last.conclusion === "success" ? "success" : last.conclusion === "failure" ? "danger" : "warning"}>
                      {last.conclusion === "success" ? "Correcto" : last.conclusion === "failure" ? "Falló" : (last.conclusion ?? "—")}
                    </Badge>{" "}
                    {formatAgo(last.updated_at)} ·{" "}
                    <a href={last.url} className="text-blue-700 hover:underline" target="_blank" rel="noreferrer">ver detalle</a>
                  </p>
                ) : (
                  <p className="text-muted-foreground">Aún no hay runs.</p>
                )}
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardTitle>IA de guiones</CardTitle>
          <CardContent className="space-y-2 text-sm">
            <Badge variant={levelVariant[a.llmLevel]}>{semaphore[a.llmLevel]}</Badge>
            <p>~{limits.llm_calls_today} / {limits.llm_daily_limit} llamadas hoy (estimado)</p>
            <Meter ratio={a.llm} level={a.llmLevel} />
            <p className="text-xs text-muted-foreground">{limits.estimated_tokens_used.toLocaleString("es")} tokens acumulados</p>
          </CardContent>
        </Card>
        <Card>
          <CardTitle>Almacenamiento de videos</CardTitle>
          <CardContent className="space-y-2 text-sm">
            <Badge variant={levelVariant[a.storageLevel]}>{Math.round(a.storage * 100)}% usado</Badge>
            <p>{formatMB(limits.estimated_storage_mb)} / {formatMB(limits.storage_limit_mb)}</p>
            <Meter ratio={a.storage} level={a.storageLevel} />
          </CardContent>
        </Card>
        <Card>
          <CardTitle>Base de datos</CardTitle>
          <CardContent className="space-y-2 text-sm">
            <Badge variant="success">Conectado</Badge>
            <p>{limits.estimated_content_count} contenidos en base de datos</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardTitle>Avisos de límites gratuitos</CardTitle>
        <CardContent className="text-sm">
          {a.alerts.length === 0 ? (
            <p className="text-muted-foreground">Sin advertencias activas.</p>
          ) : (
            <ul className="list-disc space-y-1 pl-5 text-amber-700">
              {a.alerts.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </>
  );
}
