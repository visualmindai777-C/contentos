import { verify } from "./signing.ts";

export interface ArtifactEnv {
  ARTIFACTS: R2Bucket;
  ARTIFACT_SECRET: string;
}

const PREFIX = "/artifacts/";

/** GET /artifacts/<key>?exp=&sig=[&dl=1] — sirve desde R2 solo con una URL firmada vigente (soporta Range para el vídeo). */
export async function serveArtifact(request: Request, env: ArtifactEnv): Promise<Response> {
  if (request.method !== "GET") return new Response("Method Not Allowed", { status: 405 });
  if (!env.ARTIFACT_SECRET) return new Response("ARTIFACT_SECRET no configurado", { status: 500 });

  const url = new URL(request.url);
  const key = decodeURIComponent(url.pathname.slice(PREFIX.length));
  const exp = Number(url.searchParams.get("exp"));
  const sig = url.searchParams.get("sig") ?? "";
  if (!key.startsWith("contents/") || !(await verify(env.ARTIFACT_SECRET, key, exp, sig, Date.now() / 1000))) {
    return new Response("Forbidden", { status: 403 });
  }

  const object = await env.ARTIFACTS.get(key, { range: request.headers });
  if (!object) return new Response("Not Found", { status: 404 });

  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set("etag", object.httpEtag);
  headers.set("accept-ranges", "bytes");
  headers.set("cache-control", "private, max-age=600");

  let status = 200;
  let length = object.size;
  const range = object.range as { offset?: number; length?: number } | undefined;
  if (range && request.headers.has("range")) { // R2 informa `range` también en lecturas completas
    const start = range.offset ?? 0;
    length = range.length ?? object.size - start;
    headers.set("content-range", `bytes ${start}-${start + length - 1}/${object.size}`);
    status = 206;
  }
  headers.set("content-length", String(length));

  if (url.searchParams.get("dl") === "1") {
    const [, id, ...rest] = key.split("/");
    headers.set("content-disposition", `attachment; filename="${id.slice(0, 8)}-${rest[rest.length - 1]}"`);
  }
  return new Response(object.body, { status, headers });
}
