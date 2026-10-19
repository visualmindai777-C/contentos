import type { ComponentProps } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:opacity-90",
        outline: "border bg-card hover:bg-muted",
        destructive: "bg-destructive text-white hover:opacity-90",
      },
      // En móvil los objetivos táctiles miden ~44 px; en escritorio vuelven al tamaño compacto
      size: { default: "h-11 px-4 md:h-9", sm: "h-10 px-3 text-xs md:h-8" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export function Button({ className, variant, size, ...props }: ComponentProps<"button"> & VariantProps<typeof buttonVariants>) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
