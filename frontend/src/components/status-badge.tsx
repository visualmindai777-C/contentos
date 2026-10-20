import { Badge } from "@/components/ui/badge";
import type { Level } from "@/lib/limits";
import { statusLabel } from "@/lib/labels";
import type { Status } from "@/lib/types";

const byStatus: Record<Status, "muted" | "info" | "warning" | "success" | "default" | "danger"> = {
  idea: "muted",
  guion: "info",
  generado: "info",
  revisado: "warning",
  aprobado: "success",
  publicado: "default",
  rechazado: "danger",
};

export const levelVariant: Record<Level, "success" | "warning" | "danger"> = { ok: "success", warn: "warning", danger: "danger" };

export const StatusBadge = ({ status }: { status: Status }) => <Badge variant={byStatus[status]}>{statusLabel[status]}</Badge>;
