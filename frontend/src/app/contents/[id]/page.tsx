import { notFound } from "next/navigation";
import { approve, publish, purge, regenerate, reject, retry } from "@/app/actions";
import { ActionButton } from "@/components/action-button";
import { ActionForm } from "@/components/action-form";
import { CopyButton } from "@/components/copy-button";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { statusHint } from "@/lib/labels";
import { PLATFORMS } from "@/lib/types";
import { cn, formatDate, formatMB } from "@/lib/utils";

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

  const canApprove = ["generado", "revisado"].includes(status);
  const canReject = ["idea", "guion", "generado", "revisado", "aprobado"].includes(status);
  const canRegenerate = !["idea", "publicado"].includes(status);
  const canPurge = status === "rechazado";
  const hasActions = canApprove || canReject || canRegenerate || canPurge;
  const caption = [content.caption, content.hashtags.join(" ")].filter(Boolean).join("\n\n");

  return (
    <div className="max-w-4xl space-y-4">
      <div className="space-y-1">
        <h1 className="text-xl font-semibold">{content.title || "(pendiente de generar)"}</h1>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={status} />
          <span className="text-sm text-muted-foreground">{statusHint[status]}</span>
        </div>
      </div>

      {content.last_error && (
        <Card className="border-red-300">
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center gap-2">
              <Badge variant="danger">Error</Badge>
              <span className="font-medium">No se pudo generar</span>
            </div>
            <p className="break-words text-muted-foreground">{content.last_error}</p>
            <ActionButton action={retry.bind(null, id)}>Reintentar</ActionButton>
          </CardContent>
        </Card>
      )}

      {(video || images.length > 0) && (
        <div className="space-y-3">
          {!assets.some((a) => a.url) && (
            <p className="text-sm text-amber-700">Define ASSETS_BASE_URL en el backend para ver y descargar los archivos.</p>
          )}
          {video?.url && (
            <video controls playsInline preload="metadata" src={video.url} className="mx-auto max-h-[70vh] w-full max-w-sm rounded-lg bg-black" />
          )}
          {video?.url && (
            <a href={download(video.url)} download className={cn(buttonVariants({ variant: "outline" }), "mx-auto flex w-full max-w-sm")}>
              Descargar video ({formatMB(video.file_size / 1_048_576)})
            </a>
          )}
        </div>
      )}

      {hasActions && (
        <div className="fixed inset-x-0 bottom-16 z-20 border-t bg-card p-3 md:static md:border-0 md:bg-transparent md:p-0">
          <div className="mx-auto flex max-w-4xl flex-wrap gap-2 [&>span]:flex [&>span]:flex-1 [&>span>button]:flex-1 md:[&>span]:flex-none md:[&>span>button]:flex-none">
            {canApprove && <ActionButton action={approve.bind(null, id)}>Aprobar</ActionButton>}
            {canReject && (
              <ActionButton variant="destructive" confirm="¿Rechazar este contenido?" action={reject.bind(null, id)}>Rechazar</ActionButton>
            )}
            {canPurge && (
              <ActionButton
                variant="destructive"
                confirm="¿Eliminar definitivamente? Se borran el video, las imágenes y el registro. No se puede deshacer."
                action={purge.bind(null, id)}
              >
                Eliminar definitivamente
              </ActionButton>
            )}
            {canRegenerate && (
              <ActionButton variant="outline" confirm="Se volverá a generar y se sobrescribirá el contenido actual." action={regenerate.bind(null, id)}>
                Regenerar
              </ActionButton>
            )}
          </div>
        </div>
      )}

      {content.script && (
        <Card>
          <CardTitle>Texto y guion</CardTitle>
          <CardContent className="space-y-3">
            {field("Hook", content.hook)}
            <details>
              <summary className="cursor-pointer text-sm font-medium">Guion ({words} palabras)</summary>
              <p className="mt-2 whitespace-pre-wrap text-sm">{content.script}</p>
            </details>
            {field("Texto del post", content.caption)}
            {caption && <CopyButton text={caption}>Copiar texto y hashtags</CopyButton>}
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
          <CardTitle>Todos los archivos</CardTitle>
          <CardContent className="flex flex-col gap-1 text-sm">
            {downloads.map((a) => (
              <a key={a.id} href={download(a.url!)} download className="text-blue-700 hover:underline">
                {a.storage_key.split("/").pop()} <span className="text-muted-foreground">({formatMB(a.file_size / 1_048_576)})</span>
              </a>
            ))}
          </CardContent>
        </Card>
      )}

      <p className="text-xs text-muted-foreground">
        {content.model_name || "sin modelo"} · {content.tokens_used} tokens · {content.duration_seconds}s · creado {formatDate(content.created_at)}
      </p>

      {["aprobado", "publicado"].includes(status) && (
        <Card>
          <CardTitle>Ya lo publiqué</CardTitle>
          <CardContent className="space-y-3">
            {publications.map((p) => (
              <p key={p.id} className="text-sm">
                <Badge variant="default">{p.platform}</Badge> {formatDate(p.published_at)} {p.notes && `· ${p.notes}`}
              </p>
            ))}
            <ActionForm action={publish.bind(null, id)} submitLabel="Marcar como publicado">
              <Select name="platform">
                {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
              </Select>
              <Input name="date" type="date" />
              <Input name="notes" placeholder="Notas (opcional)" className="min-w-48" />
            </ActionForm>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
