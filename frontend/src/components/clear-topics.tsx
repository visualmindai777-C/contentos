"use client";

import { useState, useTransition } from "react";
import { clearTopics } from "@/app/actions";
import { Button } from "@/components/ui/button";

export function ClearTopics({ projectId }: { projectId: string }) {
  const [pending, start] = useTransition();
  const [message, setMessage] = useState<string>();
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        disabled={pending}
        onClick={() => {
          if (!window.confirm("¿Descartar todas las tendencias que no usaste? Los videos ya creados no se tocan.")) return;
          start(async () => setMessage(await clearTopics(projectId)));
        }}
      >
        {pending ? "Limpiando…" : "Descartar las que no usé"}
      </Button>
      {message && <span role="status" className="text-sm text-muted-foreground">{message}</span>}
    </div>
  );
}
