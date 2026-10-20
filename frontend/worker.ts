// Punto de entrada del portal en Cloudflare: exige usuario y contraseña (Basic) antes de delegar en OpenNext.
// Los navegadores móviles muestran el diálogo nativo y pueden recordar la contraseña.
import { basicAuthOk } from "./auth.ts";
// @ts-expect-error el fichero lo genera `opennextjs-cloudflare build`
import openNext from "./.open-next/worker.js";

interface Env {
  PORTAL_USER?: string;
  PORTAL_PASSWORD?: string;
}

const PUBLIC_PATHS = new Set(["/manifest.webmanifest", "/icon-192.png", "/icon-512.png", "/icon.png", "/apple-icon.png", "/favicon.ico"]);

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    // Sin contraseña configurada el portal NO se abre: es preferible que falle a que quede público.
    if (!env.PORTAL_PASSWORD) return new Response("Portal sin contraseña configurada", { status: 503 });

    // El navegador pide el manifest y los íconos sin credenciales; no contienen nada sensible
    if (PUBLIC_PATHS.has(new URL(request.url).pathname)) return openNext.fetch(request, env, ctx);

    if (!(await basicAuthOk(request.headers.get("authorization"), env.PORTAL_USER ?? "admin", env.PORTAL_PASSWORD))) {
      return new Response("Autenticación requerida", {
        status: 401,
        headers: { "www-authenticate": 'Basic realm="Content OS", charset="UTF-8"' },
      });
    }
    return openNext.fetch(request, env, ctx);
  },
};
