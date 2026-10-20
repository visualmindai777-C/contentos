import { IdeaForm } from "@/components/idea-form";
import { api } from "@/lib/api";

export default async function IdeaPage() {
  const projects = await api.projects();
  return (
    <>
      <h1 className="text-xl font-semibold">Mi idea</h1>
      <p className="text-sm text-muted-foreground">Pega tu guion ya listo o tus instrucciones. La IA verifica que sea viable y, si lo es, lo pone en cola para generar el video. No aparece en Temas.</p>
      <IdeaForm projects={projects.map((p) => ({ id: p.id, name: p.name }))} />
    </>
  );
}
