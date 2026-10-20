"use client";

import Link from "next/link";
import { useState, useTransition } from "react";
import { evaluateIdea } from "@/app/actions";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Select } from "@/components/ui/input";
import type { IdeaVerdict } from "@/lib/types";
import { cn } from "@/lib/utils";

export function IdeaForm({ projects }: { projects: { id: string; name: string }[] }) {
  const [projectId, setProjectId] = useState(projects[0]?.id ?? "");
  const [prompt, setPrompt] = useState("");
  const [verdict, setVerdict] = useState<IdeaVerdict>();
  const [error, setError] = useState<string>();
  const [pending, start] = useTransition();
  const tooShort = prompt.trim().length < 10;

  return (
    <div className="space-y-4">
      <div className="space-y-3 rounded-lg border bg-card p-4">
        {projects.length > 1 && (
          <Select value={projectId} onChange={(e) => setProjectId(e.target.value)} className="h-11 w-full md:h-9 md:w-auto" aria-label="Proyecto">
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Select>
        )}
        <label className="block space-y-1">
          <span className="text-sm font-medium">Tu idea o prompt</span>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            maxLength={1000}
            rows={6}
            placeholder="Ej: Una chica descubre que su mejor amiga lleva meses copiando sus ideas de negocio y se las vende a la competencia..."
            className="w-full rounded-md border bg-card p-3 text-base outline-none focus:ring-2 focus:ring-primary/30"
          />
          <span className="block text-right text-xs text-muted-foreground">{prompt.length}/1000</span>
        </label>
        <Button
          className="w-full"
          disabled={pending || tooShort || !projectId}
          onClick={() => {
            setVerdict(undefined);
            setError(undefined);
            start(async () => {
              const res = await evaluateIdea(projectId, prompt);
              setVerdict(res.verdict);
              setError(res.error);
            });
          }}
        >
          {pending ? "La IA está evaluando…" : "Verificar y crear"}
        </Button>
        <p className="text-xs text-muted-foreground">La IA revisa si es segura para las plataformas, si se puede contar en ~40 s y si tiene potencial. Solo si es viable se crea.</p>
      </div>

      {error && <p role="alert" className="rounded-lg border border-red-300 bg-card p-3 text-sm text-destructive">{error}</p>}

      {verdict && (
        <div className={cn("space-y-3 rounded-lg border bg-card p-4", verdict.viable ? "border-green-400" : "border-red-300")} role="status">
          <div className="flex items-center gap-2">
            <Badge variant={verdict.viable ? "success" : "danger"}>{verdict.viable ? "Viable" : "No viable"}</Badge>
            <span className="text-sm text-muted-foreground">Potencial {verdict.score}/100</span>
          </div>
          <p className="text-sm">{verdict.reason}</p>
          {verdict.risks.length > 0 && (
            <ul className="list-disc space-y-1 pl-5 text-sm text-amber-700">
              {verdict.risks.map((r) => <li key={r}>{r}</li>)}
            </ul>
          )}
          {verdict.improvement && (
            <p className="text-sm"><span className="font-medium">Sugerencia: </span>{verdict.improvement}</p>
          )}
          {verdict.viable && verdict.content_id && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Creado: «{verdict.title}» ya está en cola.</p>
              <Link href={`/contents/${verdict.content_id}`} className={cn(buttonVariants({ variant: "outline" }), "w-full")}>Ver en el portal</Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
