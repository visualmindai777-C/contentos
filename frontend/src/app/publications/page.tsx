import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default async function PublicationsPage() {
  const [publications, contents] = await Promise.all([api.publications({ limit: 50 }), api.contents({ status: "publicado", limit: 100 })]);
  const titles = new Map(contents.map((c) => [c.id, c.title]));

  return (
    <>
      <h1 className="text-xl font-semibold">Publications</h1>
      <Table>
        <THead>
          <TR><TH>Fecha</TH><TH>Plataforma</TH><TH>Contenido</TH><TH>Notas</TH></TR>
        </THead>
        <TBody>
          {publications.map((p) => (
            <TR key={p.id}>
              <TD>{formatDate(p.published_at)}</TD>
              <TD><Badge variant="default">{p.platform}</Badge></TD>
              <TD>
                <Link href={`/contents/${p.content_id}`} className="hover:underline">
                  {titles.get(p.content_id) || p.content_id.slice(0, 8)}
                </Link>
              </TD>
              <TD>{p.notes || "—"}</TD>
            </TR>
          ))}
          {publications.length === 0 && <TR><TD colSpan={4} className="text-muted-foreground">Aún no hay publicaciones registradas.</TD></TR>}
        </TBody>
      </Table>
    </>
  );
}
