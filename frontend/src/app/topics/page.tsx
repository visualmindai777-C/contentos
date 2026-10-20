import { createTopic } from "@/app/actions";
import { ActionForm } from "@/components/action-form";
import { ClearTopics } from "@/components/clear-topics";
import { TopicCard } from "@/components/topic-card";
import { TrendFinder } from "@/components/trend-finder";
import { Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api";

export default async function TopicsPage({ searchParams }: { searchParams: Promise<{ project_id?: string }> }) {
  const { project_id } = await searchParams;
  const [topics, projects] = await Promise.all([
    api.topics({ project_id, limit: 50, sort: "score", days: 7 }),
    api.projects(),
  ]);
  const clearFor = project_id ?? projects[0]?.id;

  return (
    <>
      <h1 className="text-xl font-semibold">Temas</h1>
      <TrendFinder projects={projects.map((p) => ({ id: p.id, name: p.name }))} />

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          {topics.length ? `${topics.length} tendencias de los últimos 7 días, de más a menos virales.` : "Sin tendencias en los últimos 7 días."}
          {" "}Tus propias ideas no aparecen aquí: van en «Mi idea».
        </p>
        {clearFor && topics.length > 0 && <ClearTopics projectId={clearFor} />}
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {topics.map((t) => <TopicCard key={t.id} topic={t} />)}
      </div>
      {topics.length === 0 && <p className="rounded-lg border bg-card p-6 text-center text-sm text-muted-foreground">Pulsa «Buscar tendencias» arriba para traer lo más viral de hoy.</p>}

      <details className="rounded-lg border bg-card p-4">
        <summary className="cursor-pointer text-sm font-medium">Añadir un tema a mano</summary>
        <ActionForm action={createTopic} submitLabel="Añadir tema" className="mt-3 flex-col items-stretch md:flex-row md:items-center">
          <Select name="project_id" required>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Select>
          <Input name="topic" placeholder="Tema" className="min-w-64" required />
        </ActionForm>
      </details>
    </>
  );
}
