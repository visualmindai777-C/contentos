import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

const Row = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <div className="grid grid-cols-[11rem_1fr] gap-2 py-1 text-sm">
    <dt className="text-muted-foreground">{label}</dt>
    <dd>{children}</dd>
  </div>
);

export default async function SettingsPage() {
  const [config, projects] = await Promise.all([api.config(), api.projects()]);

  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-xl font-semibold">Settings <Badge>solo lectura</Badge></h1>

      <Card>
        <CardTitle>Proveedores</CardTitle>
        <CardContent>
          <dl>
            <Row label="Proveedor IA">{config.llm_provider}</Row>
            <Row label="Modelo por defecto">{config.llm_models[0] ?? "—"}</Row>
            <Row label="Fallbacks">{config.llm_models.slice(1).join(", ") || "—"}</Row>
            <Row label="Imágenes">{config.image_provider}</Row>
            <Row label="Voz">{config.tts_provider} · {config.tts_voice} ({config.tts_lang})</Row>
            <Row label="URL de artefactos">
              <Badge variant={config.assets_configured ? "success" : "warning"}>{config.assets_configured ? "configurada" : "sin configurar"}</Badge>
            </Row>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardTitle>Límites configurados</CardTitle>
        <CardContent>
          <dl>
            <Row label="OpenRouter / día">{config.openrouter_daily_limit} llamadas</Row>
            <Row label="R2">{config.r2_limit_mb} MB</Row>
            <Row label="Supabase">{config.db_limit_mb} MB</Row>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardTitle>Configuración de proyectos</CardTitle>
        <CardContent className="space-y-3">
          {projects.map((p) => (
            <div key={p.id}>
              <p className="text-sm font-medium">{p.name}</p>
              <pre className="mt-1 overflow-x-auto rounded-md bg-muted p-2 text-xs">{JSON.stringify(p.config, null, 2)}</pre>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
