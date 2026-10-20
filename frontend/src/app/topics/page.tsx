import { createContentFromTopic, createTopic } from "@/app/actions";
import { ActionButton } from "@/components/action-button";
import { ActionForm } from "@/components/action-form";
import { TrendFinder } from "@/components/trend-finder";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default async function TopicsPage({ searchParams }: { searchParams: Promise<{ project_id?: string }> }) {
  const { project_id } = await searchParams;
  const [topics, projects] = await Promise.all([api.topics({ project_id, limit: 50 }), api.projects()]);
  const names = new Map(projects.map((p) => [p.id, p.name]));

  return (
    <>
      <h1 className="text-xl font-semibold">Temas</h1>
      <TrendFinder projects={projects.map((p) => ({ id: p.id, name: p.name }))} />

      <form className="hidden gap-2 md:flex">
        <Select name="project_id" defaultValue={project_id ?? ""}>
          <option value="">Todos los proyectos</option>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
        <Button type="submit" variant="outline">Filtrar</Button>
      </form>

      <div className="space-y-2 md:hidden">
        {topics.map((t) => (
          <div key={t.id} className="space-y-2 rounded-lg border bg-card p-3">
            <p className="font-medium">{t.topic}</p>
            <p className="text-xs text-muted-foreground">{t.source} · puntaje {t.score} · {formatDate(t.created_at)}</p>
            <ActionButton className="w-full" variant="outline" action={createContentFromTopic.bind(null, t.project_id, t.id, t.topic)}>
              Crear video con este tema
            </ActionButton>
          </div>
        ))}
        {topics.length === 0 && <p className="text-sm text-muted-foreground">Sin tendencias todavía: pulsa uno de los botones de arriba.</p>}
      </div>

      <div className="hidden md:block">
      <Table>
        <THead>
          <TR><TH>Tema</TH><TH>Proyecto</TH><TH>Fuente</TH><TH>Puntaje</TH><TH>Keywords</TH><TH>Fecha</TH><TH /></TR>
        </THead>
        <TBody>
          {topics.map((t) => (
            <TR key={t.id}>
              <TD className="font-medium">{t.topic}</TD>
              <TD>{names.get(t.project_id) ?? "—"}</TD>
              <TD>{t.source}</TD>
              <TD>{t.score}</TD>
              <TD className="max-w-48 truncate">{t.keywords.join(", ") || "—"}</TD>
              <TD>{formatDate(t.created_at)}</TD>
              <TD>
                <ActionButton size="sm" variant="outline" action={createContentFromTopic.bind(null, t.project_id, t.id, t.topic)}>
                  Crear contenido
                </ActionButton>
              </TD>
            </TR>
          ))}
          {topics.length === 0 && <TR><TD colSpan={7} className="text-muted-foreground">Sin tendencias todavía.</TD></TR>}
        </TBody>
      </Table>
      </div>

      <ActionForm action={createTopic} submitLabel="Añadir tema" className="flex-col items-stretch md:flex-row md:items-center">
        <Select name="project_id" required>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
        <Input name="topic" placeholder="Tema manual" className="min-w-64" required />
      </ActionForm>
    </>
  );
}
