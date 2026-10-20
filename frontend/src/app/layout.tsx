import type { Metadata, Viewport } from "next";
import { FreeTierMonitor } from "@/components/free-tier-monitor";
import { Header } from "@/components/header";
import { BottomNav, Sidebar } from "@/components/nav";
import { api, backendHealthy } from "@/lib/api";
import "./globals.css";

export const metadata: Metadata = { title: "Content OS" };
export const viewport: Viewport = { themeColor: "#ffffff" };

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Una vez por carga completa (los layouts no se re-renderizan al navegar); las acciones lo revalidan.
  const [healthy, limits, stats] = await Promise.all([
    backendHealthy(),
    api.limits().catch(() => null),
    api.stats().catch(() => null),
  ]);

  return (
    <html lang="es">
      <body>
        <div className="flex min-h-screen flex-col md:flex-row">
          <aside className="hidden bg-card md:flex md:w-56 md:shrink-0 md:flex-col md:border-r">
            <div className="px-4 py-3 font-semibold">Content OS</div>
            <Sidebar />
            <div className="mt-auto p-3">
              <FreeTierMonitor limits={limits} />
            </div>
          </aside>
          <div className="min-w-0 flex-1">
            <Header healthy={healthy} limits={limits} />
            <main className="space-y-4 p-4 pb-28 md:p-6 md:pb-6">{children}</main>
          </div>
        </div>
        <BottomNav badge={stats?.pending} />
      </body>
    </html>
  );
}
