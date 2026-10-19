import { notFound } from "next/navigation";
import { approve, publish, regenerate, reject, retry } from "@/app/actions";
import { ActionButton } from "@/components/action-button";
import { ActionForm } from "@/components/action-form";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { PLATFORMS } from "@/lib/types";
import { formatDate, formatMB } from "@/lib/utils";

// Las URLs vienen firmadas por el backend (?exp=&sig=); dl=1 hace que el Worker responda como descarga.
const download = (url: string) => `${url}${url.includes("?") ? "&" : "?"}dl=1`;

const field = (label: string, value: string) =>
  value && (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="whitespace-pre-wrap text-sm">{value}</p>
    </div>
  );

export default async function ContentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let content, assets, publications;
  try {
    [content, assets, publications] = await Promise.all([
      api.content(id),
      api.assets(id),
      api.publications({ content_id: id }),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }

  const { status } = content;
  const video = assets.find((a) => a.kind === "video");
  const images = assets.filter((a) => a.kind === "image");
  const downloads = assets.filter((a) => a.url);
  const words = content.script.split(/\s+/).filter(Boolean).length;

  return (
    <div className="max-w-4xl space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">{content.title || "(pendiente de generar)"}</h1>
        <StatusBadge status={status} />
      </div>
      <p className="text-xs text-muted-foreground">
        {content.model_name || "sin modelo"} · {content.tokens_used} tokens · {content.duration_seconds}s · creado {formatDate(content.created_at)}
      </p>

      {content.last_error && (
        <Card className="border-red-300">
          <CardContent className="flex flex-wrap items-center gap-3 text-sm">
            <Badge variant="danger">Error</Badge>
            <span className="min-w-0 flex-1 break-words">{content.last_error}</span>
            <ActionButton action={retry.bind(null, id)}>Reintentar</ActionButton>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="flex flex-wrap items-center gap-2">
          {["generado", "revisado"].includes(status) && <ActionButton action={approve.bind(null, id)}>Aprobar</ActionButton>}
          {["idea", "guion", "generado", "revisado", "aprobado"].includes(status) && (
            <ActionButton variant="destructive" confirm="¿Rechazar este contenido?" action={reject.bind(null, id)}>Rechazar</ActionButton>
          )}
          {!["idea", "publicado"].includes(status) && (
            <ActionButton variant="outline" confirm="Se volverá a generar y se sobrescribirá el contenido actual." action={regenerate.bind(null, id)}>
              Regenerar
            </ActionButton>
          )}
          {["idea", "guion"].includes(status) && !content.last_error && (
            <span className="text-sm text-muted-foreground">En cola: el pipeline lo procesará en unos minutos.</span>
          )}
        </CardContent>
      </Card>

      {(video || images.length > 0) && (
        <Card>
          <CardTitle>Media</CardTitle>
          <CardContent className="space-y-3">
            {!assets.some((a) => a.url) && (
              <p className="text-sm text-amber-700">Define ASSETS_BASE_URL en el backend para ver y descargar los archivos.</p>
            )}
            {video?.url && <video controls preload="metadata" src={video.url} className="w-full max-w-xs rounded-md bg-black" />}
            <div className="grid grid-cols-3 gap-2 md:grid-cols-6">
              {images.map((img) =>
                img.url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img key={img.id} src={img.url} alt="" loading="lazy" className="aspect-[9/16] rounded-md object-cover" />
                ) : null,
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {content.script && (
        <Card>
          <CardTitle>Contenido</CardTitle>
          <CardContent className="space-y-3">
            {field("Hook", content.hook)}
            <details>
              <summary className="cursor-pointer text-sm font-medium">Guion ({words} palabras)</summary>
              <p className="mt-2 whitespace-pre-wrap text-sm">{content.script}</p>
            </details>
            {field("Caption", content.caption)}
            {content.hashtags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {content.hashtags.map((h) => <Badge key={h} variant="info">{h}</Badge>)}
              </div>
            )}
            {field("CTA", content.cta)}
          </CardContent>
        </Card>
      )}

      {downloads.length > 0 && (
        <Card>
          <CardTitle>Descargas</CardTitle>
          <CardContent className="flex flex-col gap-1 text-sm">
            {downloads.map((a) => (
              <a key={a.id} href={download(a.url!)} download className="text-blue-700 hover:underline">
                {a.storage_key.split("/").pop()} <span className="text-muted-foreground">({formatMB(a.file_size / 1_048_576)})</span>
              </a>
            ))}
          </CardContent>
        </Card>
      )}

      {["aprobado", "publicado"].includes(status) && (
        <Card>
          <CardTitle>Publicación manual</CardTitle>
          <CardContent className="space-y-3">
            {publications.map((p) => (
              <p key={p.id} className="text-sm">
                <Badge variant="default">{p.platform}</Badge> {formatDate(p.published_at)} {p.notes && `· ${p.notes}`}
              </p>
            ))}
            <ActionForm action={publish.bind(null, id)} submitLabel="Marcar publicado">
              <Select name="platform">
                {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
              </Select>
              <Input name="date" type="date" />
              <Input name="notes" placeholder="Notas" className="min-w-48" />
            </ActionForm>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
