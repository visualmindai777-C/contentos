import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export const Table = ({ className, ...props }: ComponentProps<"table">) => (
  <div className="overflow-x-auto rounded-lg border bg-card">
    <table className={cn("w-full text-left text-sm", className)} {...props} />
  </div>
);

export const THead = (props: ComponentProps<"thead">) => <thead className="border-b bg-muted text-xs uppercase text-muted-foreground" {...props} />;
export const TBody = (props: ComponentProps<"tbody">) => <tbody className="divide-y" {...props} />;
export const TR = (props: ComponentProps<"tr">) => <tr {...props} />;
export const TH = ({ className, ...props }: ComponentProps<"th">) => <th className={cn("px-3 py-2 font-medium", className)} {...props} />;
export const TD = ({ className, ...props }: ComponentProps<"td">) => <td className={cn("px-3 py-2", className)} {...props} />;
