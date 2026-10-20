"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export function CopyButton({ text, children }: { text: string; children: string }) {
  const [done, setDone] = useState(false);
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 2000);
        } catch {
          window.prompt("Copia el texto:", text);
        }
      }}
    >
      {done ? "¡Copiado!" : children}
    </Button>
  );
}
