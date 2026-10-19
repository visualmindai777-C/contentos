"use client";

import { startTransition } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  const router = useRouter();
  return (
    <div className="space-y-3">
      <h1 className="text-lg font-semibold">No se pudo cargar la página</h1>
      <p className="text-sm text-muted-foreground">
        El backend puede estar dormido (Render free) o caído. Reintenta en unos segundos.
      </p>
      <Button
        onClick={() =>
          startTransition(() => {
            router.refresh();
            reset();
          })
        }
      >
        Reintentar
      </Button>
    </div>
  );
}
