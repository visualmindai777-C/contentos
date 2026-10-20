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
          <span className="text-sm font-medium">Tu guion o instrucciones</span>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            maxLength={4000}
            rows={6}
            placeholder={"Pega tu guion ya listo (PERSONAJES / ESCENA / diálogos) o tus instrucciones exactas.\n\nSi pegas el guion, se usa tal cual: la IA solo lo revisa y el sistema genera imágenes, voz y video."}
            className="w-full rounded-md border bg-card p-3 text-base outline-none focus:ring-2 focus:ring-primary/30"
          />
          <span className="block text-right text-xs text-muted-foreground">{prompt.length}/4000</span>
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
        <p className="text-xs text-muted-foreground">La IA revisa que sea segura para las plataformas y que tenga potencial. Un guion se usa tal cual; unas instrucciones se siguen al pie de la letra. Solo se crea si es viable, y no aparece en Temas.</p>
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
              <p className="text-sm font-medium">{verdict.mode === "guion"
                  ? `Creado: «${verdict.title}». Se usó tu guion tal cual; ya está en cola para imágenes, voz y video.`
                  : `Creado: «${verdict.title}». Ya está en cola: se escribirá siguiendo tus instrucciones.`}</p>
              <Link href={`/contents/${verdict.content_id}`} className={cn(buttonVariants({ variant: "outline" }), "w-full")}>Ver en el portal</Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
