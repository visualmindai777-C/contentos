import Link from "next/link";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Select } from "@/components/ui/input";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { api } from "@/lib/api";
import { statusLabel } from "@/lib/labels";
import { STATUSES } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

const PAGE = 25;

type Search = { status?: string; project_id?: string; page?: string };

export default async function ContentsPage({ searchParams }: { searchParams: Promise<Search> }) {
  const sp = await searchParams;
  const status = STATUSES.find((s) => s === sp.status);
  const page = Math.max(1, Number(sp.page) || 1);

  // Se pide una fila de más para saber si hay página siguiente sin endpoint de conteo.
  const [rows, projects] = await Promise.all([
    api.contents({ status, project_id: sp.project_id, limit: PAGE + 1, offset: (page - 1) * PAGE }),
    api.projects(),
  ]);
  const items = rows.slice(0, PAGE);
  const names = new Map(projects.map((p) => [p.id, p.name]));

  const href = (p: number) => {
    const q = new URLSearchParams({ page: String(p) });
    if (status) q.set("status", status);
    if (sp.project_id) q.set("project_id", sp.project_id);
    return `/contents?${q}`;
  };

  return (
    <>
      <h1 className="text-xl font-semibold">Contenidos</h1>
      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:px-0">
        {[["", "Todos"], ["generado", "Por revisar"], ["aprobado", "Aprobados"], ["publicado", "Publicados"], ["idea", "En cola"], ["rechazado", "Rechazados"]].map(([value, label]) => {
          const q = new URLSearchParams();
          if (value) q.set("status", value);
          if (sp.project_id) q.set("project_id", sp.project_id);
          const active = (status ?? "") === value;
          return (
            <Link
              key={value}
              href={`/contents?${q}`}
              className={cn("inline-flex h-10 shrink-0 items-center rounded-full border px-4 text-sm", active ? "bg-primary text-primary-foreground" : "bg-card hover:bg-muted")}
            >
              {label}
            </Link>
          );
        })}
      </div>
      <form className="hidden flex-wrap gap-2 md:flex">
        <Select name="status" defaultValue={status ?? ""}>
          <option value="">Todos los estados</option>
          {STATUSES.map((s) => <option key={s} value={s}>{statusLabel[s]} ({s})</option>)}
        </Select>
        <Select name="project_id" defaultValue={sp.project_id ?? ""}>
          <option value="">Todos los proyectos</option>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
        <Button type="submit" variant="outline">Filtrar</Button>
      </form>

      <div className="space-y-2 md:hidden">
        {items.map((c) => (
          <Link key={c.id} href={`/contents/${c.id}`} prefetch={false} className="block rounded-lg border bg-card p-3 active:bg-muted">
            <p className="line-clamp-2 font-medium">{c.title || "(pendiente de generar)"}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <StatusBadge status={c.status} />
              {c.last_error && <Badge variant="danger">error</Badge>}
              <span className="text-xs text-muted-foreground">{formatDate(c.created_at)}</span>
            </div>
          </Link>
        ))}
        {items.length === 0 && <p className="text-sm text-muted-foreground">Sin contenidos.</p>}
      </div>

      <div className="hidden md:block">
      <Table>
        <THead>
          <TR>
            <TH>Título</TH>
            <TH className="hidden md:table-cell">Proyecto</TH>
            <TH>Estado</TH>
            <TH className="hidden md:table-cell">Modelo IA</TH>
            <TH>Fecha</TH>
          </TR>
        </THead>
        <TBody>
          {items.map((c) => (
            <TR key={c.id}>
              <TD className="max-w-80 truncate font-medium">
                <Link href={`/contents/${c.id}`} prefetch={false} className="hover:underline">{c.title || "(pendiente de generar)"}</Link>
              </TD>
              <TD className="hidden md:table-cell">{names.get(c.project_id) ?? "—"}</TD>
              <TD className="space-x-1">
                <StatusBadge status={c.status} />
                {c.last_error && <Badge variant="danger" title={c.last_error}>error</Badge>}
              </TD>
              <TD className="hidden max-w-48 truncate md:table-cell">{c.model_name || "—"}</TD>
              <TD>{formatDate(c.created_at)}</TD>
            </TR>
          ))}
          {items.length === 0 && <TR><TD colSpan={5} className="text-muted-foreground">Sin contenidos.</TD></TR>}
        </TBody>
      </Table>
      </div>

      <div className="flex gap-2">
        {page > 1 && <Link href={href(page - 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>← Anterior</Link>}
        {rows.length > PAGE && <Link href={href(page + 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>Siguiente →</Link>}
      </div>
    </>
  );
}
