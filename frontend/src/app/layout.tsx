import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import { FreeTierMonitor } from "@/components/free-tier-monitor";
import { Header } from "@/components/header";
import { BottomNav, Sidebar } from "@/components/nav";
import { api, backendHealthy } from "@/lib/api";
import "./globals.css";

export const metadata: Metadata = { title: "Content OS" };
export const viewport: Viewport = { themeColor: "#ffffff" };

// Cabecera y globo de "Revisar" cargan en streaming: la página ya se ve y reacciona mientras llegan.
async function HeaderLoader() {
  const [healthy, limits] = await Promise.all([backendHealthy(), api.limits().catch(() => null)]);
  return <Header healthy={healthy} limits={limits} />;
}

async function SidebarMonitor() {
  return <FreeTierMonitor limits={await api.limits().catch(() => null)} />;
}

async function BottomNavLoader() {
  const stats = await api.stats().catch(() => null);
  return <BottomNav badge={stats?.review} />;
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <div className="flex min-h-screen flex-col md:flex-row">
          <aside className="hidden bg-card md:flex md:w-56 md:shrink-0 md:flex-col md:border-r">
            <div className="px-4 py-3 font-semibold">Content OS</div>
            <Sidebar />
            <div className="mt-auto p-3">
              <Suspense>
                <SidebarMonitor />
              </Suspense>
            </div>
          </aside>
          <div className="min-w-0 flex-1">
            <Suspense fallback={<header className="flex h-12 items-center border-b bg-card px-4 font-semibold md:hidden">Content OS</header>}>
              <HeaderLoader />
            </Suspense>
            <main className="space-y-4 p-4 pb-28 md:p-6 md:pb-6">{children}</main>
          </div>
        </div>
        <Suspense fallback={<BottomNav />}>
          <BottomNavLoader />
        </Suspense>
      </body>
    </html>
  );
}
