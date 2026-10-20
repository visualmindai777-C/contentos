import Link from "next/link";
import { Card } from "@/components/ui/card";

const items = [
  ["/idea", "Mi idea", "Pega un prompt y la IA verifica si es viable"],
  ["/publications", "Publicaciones", "Lo que ya publicaste y dónde"],
  ["/projects", "Proyectos", "Nichos y configuración"],
  ["/settings", "Ajustes", "Límites gratuitos y proveedores"],
] as const;

export default function MorePage() {
  return (
    <>
      <h1 className="text-xl font-semibold">Más</h1>
      <Card className="divide-y">
        {items.map(([href, title, hint]) => (
          <Link key={href} href={href} className="flex min-h-14 flex-col justify-center px-4 py-2 hover:bg-muted">
            <span className="font-medium">{title}</span>
            <span className="text-sm text-muted-foreground">{hint}</span>
          </Link>
        ))}
      </Card>
    </>
  );
}
