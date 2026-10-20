"use client";

import { useState, useTransition } from "react";
import { discoverTrends } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/input";

const modes = [
  ["viral", "Lo más visto hoy", "Lo que más se ve ahora en Reddit, Google y Wikipedia, de cualquier tema."],
  ["monetizable", "Temas que monetizan", "Finanzas, negocios, tecnología, salud y productividad: nichos con mejores anuncios."],
  ["nicho", "De mi nicho", "Solo lo relacionado con el nicho configurado en el proyecto."],
] as const;

export function TrendFinder({ projects }: { projects: { id: string; name: string }[] }) {
  const [projectId, setProjectId] = useState(projects[0]?.id ?? "");
  const [running, setRunning] = useState<string>();
  const [result, setResult] = useState<string>();
  const [pending, start] = useTransition();

  return (
    <div className="space-y-3 rounded-lg border bg-card p-4">
      <div>
        <h2 className="font-semibold">Buscar tendencias</h2>
        <p className="text-sm text-muted-foreground">Elige qué buscar. Tarda unos segundos y los temas nuevos aparecen abajo.</p>
      </div>
      {projects.length > 1 && (
        <Select value={projectId} onChange={(e) => setProjectId(e.target.value)} className="h-11 w-full md:h-9 md:w-auto" aria-label="Proyecto">
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
      )}
      <div className="grid gap-2 md:grid-cols-3">
        {modes.map(([mode, label, hint]) => (
          <div key={mode} className="space-y-1">
            <Button
              className="w-full"
              variant={mode === "viral" ? "default" : "outline"}
              disabled={pending || !projectId}
              onClick={() => {
                setRunning(mode);
                setResult(undefined);
                start(async () => setResult(await discoverTrends(projectId, mode)));
              }}
            >
              {pending && running === mode ? "Buscando…" : label}
            </Button>
            <p className="text-xs text-muted-foreground">{hint}</p>
          </div>
        ))}
      </div>
      {result && <p role="status" className="text-sm font-medium">{result}</p>}
    </div>
  );
}
