"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BulbIcon, FilmIcon, HomeIcon, InboxIcon, MenuIcon } from "@/components/icons";
import { cn } from "@/lib/utils";

const sidebar = [
  ["/dashboard", "Inicio"],
  ["/idea", "Mi idea"],
  ["/review", "Revisar"],
  ["/contents", "Contenidos"],
  ["/publications", "Publicaciones"],
  ["/topics", "Temas"],
  ["/projects", "Proyectos"],
  ["/settings", "Ajustes"],
] as const;

const tabs = [
  ["/dashboard", "Inicio", HomeIcon],
  ["/review", "Revisar", InboxIcon],
  ["/contents", "Contenidos", FilmIcon],
  ["/topics", "Temas", BulbIcon],
  ["/mas", "Más", MenuIcon],
] as const;

// "Más" también resalta en las páginas que cuelgan de él
const moreRoutes = ["/mas", "/idea", "/projects", "/publications", "/settings"];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <nav className="hidden flex-col gap-1 px-2 md:flex" aria-label="Principal">
      {sidebar.map(([href, label]) => (
        <Link
          key={href}
          href={href}
          className={cn("rounded-md px-3 py-1.5 text-sm hover:bg-muted", pathname.startsWith(href) && "bg-muted font-medium")}
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}

export function BottomNav({ badge }: { badge?: number }) {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Principal"
      className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t bg-card pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      {tabs.map(([href, label, Icon]) => {
        const active = href === "/mas" ? moreRoutes.some((r) => pathname.startsWith(r)) : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn("relative flex h-16 flex-col items-center justify-center gap-0.5 text-[11px]", active ? "font-semibold text-foreground" : "text-muted-foreground")}
          >
            <span className={cn("rounded-full px-4 py-1", active && "bg-muted")}>
              <Icon />
            </span>
            {label}
            {href === "/review" && badge ? (
              <span className="absolute top-1.5 left-1/2 ml-2 min-w-5 rounded-full bg-destructive px-1 text-center text-[11px] leading-5 font-semibold text-white">
                {badge}
              </span>
            ) : null}
          </Link>
        );
      })}
    </nav>
  );
}
