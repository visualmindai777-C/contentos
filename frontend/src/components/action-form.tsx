"use client";

import { useActionState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ActionForm({
  action, submitLabel, className, children,
}: {
  action: (prev: string, form: FormData) => Promise<string>;
  submitLabel: string;
  className?: string;
  children: ReactNode;
}) {
  const [error, formAction, pending] = useActionState(action, "");

  return (
    <form action={formAction} className={cn("flex flex-wrap items-center gap-2", className)}>
      {children}
      <Button type="submit" disabled={pending}>
        {pending ? "…" : submitLabel}
      </Button>
      {error && <span className="text-sm text-destructive">{error}</span>}
    </form>
  );
}
