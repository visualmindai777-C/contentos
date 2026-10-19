"use client";

import { useState, useTransition, type ComponentProps, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

export function ActionButton({
  action, children, confirm, ...props
}: {
  action: () => Promise<string | undefined | void>;
  children: ReactNode;
  confirm?: string;
} & Omit<ComponentProps<typeof Button>, "onClick">) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string>();

  return (
    <span className="inline-flex items-center gap-2">
      <Button
        {...props}
        disabled={pending}
        onClick={() => {
          if (confirm && !window.confirm(confirm)) return;
          start(async () => setError((await action()) || undefined));
        }}
      >
        {pending ? "…" : children}
      </Button>
      {error && <span className="text-xs text-destructive">{error}</span>}
    </span>
  );
}
