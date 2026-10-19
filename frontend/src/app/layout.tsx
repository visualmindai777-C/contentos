import type { Metadata } from "next";
import { FreeTierMonitor } from "@/components/free-tier-monitor";
import { Header } from "@/components/header";
import { Nav } from "@/components/nav";
import { api, backendHealthy } from "@/lib/api";
import "./globals.css";

export const metadata: Metadata = { title: "Content OS" };

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Una vez por carga completa (los layouts no se re-renderizan al navegar); las acciones lo revalidan.
  const [healthy, limits] = await Promise.all([backendHealthy(), api.limits().catch(() => null)]);

  return (
    <html lang="es">
      <body>
        <div className="flex min-h-screen flex-col md:flex-row">
          <aside className="border-b bg-card md:flex md:w-56 md:shrink-0 md:flex-col md:border-r md:border-b-0">
            <div className="px-4 py-3 font-semibold">Content OS</div>
            <Nav />
            <div className="mt-auto hidden p-3 md:block">
              <FreeTierMonitor limits={limits} />
            </div>
          </aside>
          <div className="min-w-0 flex-1">
            <Header healthy={healthy} limits={limits} />
            <main className="space-y-4 p-4 md:p-6">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
