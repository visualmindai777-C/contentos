"use client";

import { useState, useTransition } from "react";
import { discoverTrends } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const modes = [
  ["viral", "Lo más visto", "Lo que más se ve hoy en Reddit, Google y Wikipedia, de cualquier tema."],
  ["monetizable", "Monetizan", "Finanzas, negocios, tecnología, salud y productividad: nichos con mejores anuncios."],
  ["nicho", "Mi nicho", "Solo lo relacionado con el nicho del proyecto."],
] as const;

export function TrendFinder({ projects }: { projects: { id: string; name: string }[] }) {
  const [projectId, setProjectId] = useState(projects[0]?.id ?? "");
  const [mode, setMode] = useState<(typeof modes)[number][0]>("viral");
  const [result, setResult] = useState<string>();
  const [pending, start] = useTransition();
  const current = modes.find(([m]) => m === mode)!;

  return (
    <section className="space-y-3 rounded-lg border bg-card p-4" aria-label="Buscar tendencias">
      <div role="radiogroup" aria-label="Qué buscar" className="grid grid-cols-3 gap-2">
        {modes.map(([m, label]) => (
          <button
            key={m}
            type="button"
            role="radio"
            aria-checked={mode === m}
            onClick={() => setMode(m)}
            className={cn("h-11 rounded-md border text-sm font-medium", mode === m ? "border-primary bg-primary text-primary-foreground" : "bg-card hover:bg-muted")}
          >
            {label}
          </button>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">{current[2]}</p>
      {projects.length > 1 && (
        <Select value={projectId} onChange={(e) => setProjectId(e.target.value)} className="h-11 w-full md:h-9 md:w-auto" aria-label="Proyecto">
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
      )}
      <Button
        className="w-full"
        disabled={pending || !projectId}
        onClick={() => {
          setResult(undefined);
          start(async () => setResult(await discoverTrends(projectId, mode)));
        }}
      >
        {pending ? "Buscando… (unos segundos)" : "Buscar tendencias"}
      </Button>
      {result && <p role="status" className="text-sm font-medium">{result}</p>}
    </section>
  );
}
