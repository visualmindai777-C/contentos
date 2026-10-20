import type { ComponentProps } from "react";

const base = { width: 22, height: 22, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true } as const;
const svg = (d: string) => (props: ComponentProps<"svg">) => (
  <svg {...base} {...props}>
    <path d={d} />
  </svg>
);

export const HomeIcon = svg("M3 11l9-8 9 8M5 10v10h14V10");
export const InboxIcon = svg("M4 13l2-8h12l2 8M4 13v6h16v-6M4 13h5l1 2h4l1-2h5");
export const FilmIcon = svg("M4 4h16v16H4zM8 4v16M16 4v16M4 9h4M4 15h4M16 9h4M16 15h4");
export const BulbIcon = svg("M9 18h6M10 21h4M12 3a6 6 0 00-4 10.5c.6.6 1 1.4 1 2.5h6c0-1.1.4-1.9 1-2.5A6 6 0 0012 3z");
export const MenuIcon = svg("M4 7h16M4 12h16M4 17h16");
