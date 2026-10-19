import Link from "next/link";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Select } from "@/components/ui/input";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { api } from "@/lib/api";
import { STATUSES } from "@/lib/types";
import { formatDate } from "@/lib/utils";

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
      <h1 className="text-xl font-semibold">Contents</h1>
      <form className="flex flex-wrap gap-2">
        <Select name="status" defaultValue={status ?? ""}>
          <option value="">Todos los estados</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </Select>
        <Select name="project_id" defaultValue={sp.project_id ?? ""}>
          <option value="">Todos los proyectos</option>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
        <Button type="submit" variant="outline">Filtrar</Button>
      </form>

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

      <div className="flex gap-2">
        {page > 1 && <Link href={href(page - 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>← Anterior</Link>}
        {rows.length > PAGE && <Link href={href(page + 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>Siguiente →</Link>}
      </div>
    </>
  );
}
