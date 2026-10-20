"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { reviseScript, updateScript } from "@/app/actions";
import { Button } from "@/components/ui/button";

export function ScriptEditor({ id, script }: { id: string; script: string }) {
  const router = useRouter();
  const [draft, setDraft] = useState(script);
  const [instruction, setInstruction] = useState("");
  const [error, setError] = useState<string>();
  const [note, setNote] = useState<string>();
  const [asking, startAsking] = useTransition();
  const [saving, startSaving] = useTransition();
  const changed = draft.trim() !== script.trim();

  return (
    <details className="rounded-lg border bg-card">
      <summary className="cursor-pointer px-4 py-3 text-sm font-semibold">Corregir el texto (sin regenerar las imágenes)</summary>
      <div className="space-y-3 border-t p-4">
        <p className="text-sm text-muted-foreground">
          Cambia el guion a mano o dile a la IA qué corregir. Al guardar se conservan las imágenes: solo se rehacen la voz y el video (unos minutos).
        </p>

        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="instruction">Dile a la IA qué cambiar</label>
          <textarea
            id="instruction"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            rows={2}
            maxLength={1000}
            placeholder="Ej: la frase de la llamada quedó mal traducida; que suene natural en español"
            className="w-full rounded-md border bg-card p-3 text-base outline-none focus:ring-2 focus:ring-primary/30"
          />
          <Button
            variant="outline"
            className="w-full"
            disabled={asking || instruction.trim().length < 5}
            onClick={() => {
              setError(undefined);
              setNote(undefined);
              startAsking(async () => {
                const res = await reviseScript(id, instruction);
                if (res.error) setError(res.error);
                else if (res.script) {
                  setDraft(res.script);
                  setNote("La IA propuso este texto. Revísalo y, si está bien, guarda.");
                }
              });
            }}
          >
            {asking ? "La IA está corrigiendo…" : "Proponer corrección"}
          </Button>
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="script">Guion (editable)</label>
          <textarea
            id="script"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={14}
            maxLength={6000}
            className="w-full rounded-md border bg-card p-3 font-mono text-sm outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>

        {note && <p role="status" className="text-sm font-medium">{note}</p>}
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}

        <Button
          className="w-full"
          disabled={saving || !changed}
          onClick={() => {
            if (!window.confirm("Se rehacen la voz y el video con este texto (las imágenes se conservan). El video actual se reemplaza al terminar. ¿Seguir?")) return;
            setError(undefined);
            startSaving(async () => {
              const err = await updateScript(id, draft);
              if (err) setError(err);
              else router.refresh();
            });
          }}
        >
          {saving ? "Guardando…" : "Guardar y rehacer voz y video"}
        </Button>
      </div>
    </details>
  );
}
