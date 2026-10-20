"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

// Mientras algo se esté generando, la pantalla se actualiza sola (solo con la pestaña visible, para no gastar API ni batería).
export function AutoRefresh({ active, seconds = 30 }: { active: boolean; seconds?: number }) {
  const router = useRouter();
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => {
      if (document.visibilityState === "visible") router.refresh();
    }, seconds * 1000);
    return () => clearInterval(id);
  }, [active, seconds, router]);
  return null;
}
