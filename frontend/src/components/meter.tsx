import type { Level } from "@/lib/limits";
import { cn } from "@/lib/utils";

const bar: Record<Level, string> = { ok: "bg-green-500", warn: "bg-amber-500", danger: "bg-red-500" };

export function Meter({ ratio, level }: { ratio: number; level: Level }) {
  return (
    <div className="h-2 w-full rounded-full bg-muted">
      <div className={cn("h-2 rounded-full", bar[level])} style={{ width: `${Math.min(100, ratio * 100)}%` }} />
    </div>
  );
}
