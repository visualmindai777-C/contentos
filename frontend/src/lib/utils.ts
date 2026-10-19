import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));

export const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString("es", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });

export function formatAgo(iso: string, now = Date.now()) {
  const minutes = Math.max(0, Math.round((now - Date.parse(iso)) / 60_000));
  if (minutes < 60) return `hace ${minutes} min`;
  return minutes < 1_440 ? `hace ${Math.round(minutes / 60)} h` : `hace ${Math.round(minutes / 1_440)} d`;
}

export const formatMB = (mb: number) => (mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(mb < 10 ? 1 : 0)} MB`);
