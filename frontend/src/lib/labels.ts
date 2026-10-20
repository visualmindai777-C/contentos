import type { Status } from "@/lib/types";

// Lenguaje llano para el estado: el nombre técnico queda para filtros y base de datos.
export const statusLabel: Record<Status, string> = {
  idea: "En cola",
  guion: "En cola",
  generado: "Por revisar",
  revisado: "Por revisar",
  aprobado: "Aprobado",
  publicado: "Publicado",
  rechazado: "Rechazado",
};

export const statusHint: Record<Status, string> = {
  idea: "El pipeline lo generará en los próximos minutos.",
  guion: "El guion está listo; faltan imágenes, voz y video.",
  generado: "Mira el video y decide: aprobar o rechazar.",
  revisado: "Mira el video y decide: aprobar o rechazar.",
  aprobado: "Descárgalo, publícalo a mano y márcalo como publicado.",
  publicado: "Ya publicado.",
  rechazado: "Descartado. Puedes regenerarlo si quieres otra versión.",
};
