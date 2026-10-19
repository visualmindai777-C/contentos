"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  ["/dashboard", "Dashboard"],
  ["/projects", "Projects"],
  ["/topics", "Topics"],
  ["/contents", "Contents"],
  ["/publications", "Publications"],
  ["/settings", "Settings"],
] as const;

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-col md:pb-0">
      {links.map(([href, label]) => (
        <Link
          key={href}
          href={href}
          className={cn(
            "whitespace-nowrap rounded-md px-3 py-1.5 text-sm hover:bg-muted",
            pathname.startsWith(href) && "bg-muted font-medium",
          )}
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}
