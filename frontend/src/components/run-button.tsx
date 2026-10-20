"use client";

import { useState, useTransition } from "react";
import { runPipeline } from "@/app/actions";
import { Button } from "@/components/ui/button";

export function RunButton({ disabled, label = "Generar ahora" }: { disabled?: boolean; label?: string }) {
  const [pending, start] = useTransition();
  const [message, setMessage] = useState<string>();
  return (
    <div className="space-y-1">
      <Button className="w-full sm:w-auto" disabled={disabled || pending} onClick={() => start(async () => setMessage(await runPipeline()))}>
        {pending ? "Iniciando…" : label}
      </Button>
      {message && <p role="status" className="text-sm font-medium">{message}</p>}
    </div>
  );
}
