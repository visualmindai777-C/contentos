import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

const field = "h-9 rounded-md border bg-card px-2 text-sm outline-none focus:ring-2 focus:ring-primary/30";

export const Input = ({ className, ...props }: ComponentProps<"input">) => <input className={cn(field, className)} {...props} />;
export const Select = ({ className, ...props }: ComponentProps<"select">) => <select className={cn(field, className)} {...props} />;
