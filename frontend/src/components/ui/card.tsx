import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export const Card = ({ className, ...props }: ComponentProps<"div">) => (
  <div className={cn("rounded-lg border bg-card", className)} {...props} />
);

export const CardTitle = ({ className, ...props }: ComponentProps<"h2">) => (
  <h2 className={cn("border-b px-4 py-2.5 text-sm font-semibold", className)} {...props} />
);

export const CardContent = ({ className, ...props }: ComponentProps<"div">) => (
  <div className={cn("p-4", className)} {...props} />
);
