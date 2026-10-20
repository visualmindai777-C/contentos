import { IdeaForm } from "@/components/idea-form";
import { api } from "@/lib/api";

export default async function IdeaPage() {
  const projects = await api.projects();
  return (
    <>
      <h1 className="text-xl font-semibold">Mi idea</h1>
      <p className="text-sm text-muted-foreground">Pega una idea o prompt. La IA verifica si es viable y, si lo es, la pone en cola para generar el video.</p>
      <IdeaForm projects={projects.map((p) => ({ id: p.id, name: p.name }))} />
    </>
  );
}
