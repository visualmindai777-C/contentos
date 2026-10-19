import { createProject } from "@/app/actions";
import { ActionForm } from "@/components/action-form";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { api } from "@/lib/api";

export default async function ProjectsPage() {
  const projects = await api.projects();

  return (
    <>
      <h1 className="text-xl font-semibold">Projects</h1>
      <Table>
        <THead>
          <TR><TH>Nombre</TH><TH>Slug</TH><TH>Nicho</TH><TH>Idioma</TH><TH>Estado</TH></TR>
        </THead>
        <TBody>
          {projects.map((p) => (
            <TR key={p.id}>
              <TD className="font-medium">{p.name}</TD>
              <TD>{p.slug}</TD>
              <TD>{p.niche || "—"}</TD>
              <TD>{p.language}</TD>
              <TD><Badge variant={p.is_active ? "success" : "muted"}>{p.is_active ? "activo" : "inactivo"}</Badge></TD>
            </TR>
          ))}
        </TBody>
      </Table>

      <ActionForm action={createProject} submitLabel="Crear proyecto">
        <Input name="name" placeholder="Nombre" required />
        <Input name="slug" placeholder="slug-en-minusculas" pattern="[a-z0-9\-]+" required />
        <Input name="niche" placeholder="Nicho" className="min-w-64" />
      </ActionForm>
    </>
  );
}
