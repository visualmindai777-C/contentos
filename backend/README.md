---
title: Content OS API
emoji: 🎬
colorFrom: gray
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

API FastAPI de Content OS (generación de contenido para TikTok, Instagram, Threads y X).

Secrets del Space (Settings → Variables and secrets):

| Nombre | Valor |
|---|---|
| `DATABASE_URL` | cadena del **pooler** de Supabase (`postgresql+asyncpg://…:6543/postgres`) |
| `API_KEY` | clave compartida con el portal y el Worker (`X-API-Key`) |
| `ASSETS_BASE_URL` | `https://<worker>.workers.dev/artifacts` |
| `ARTIFACT_SECRET` | el mismo secreto que el Worker: firma las URLs de descarga |

`GET /health` no requiere clave. El resto de rutas, sí.
