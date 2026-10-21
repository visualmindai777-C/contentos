// Renderiza los fotogramas de los personajes 3D (PNG con transparencia) a partir de una línea de tiempo.
// Uso: node render.mjs timeline.json carpeta_salida [ancho] [alto]
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = path.dirname(fileURLToPath(import.meta.url));
const [, , timelinePath, outDir, w = "720", h = "1280"] = process.argv;
const width = Number(w);
const height = Number(h);
const timeline = JSON.parse(fs.readFileSync(timelinePath, "utf8"));
fs.mkdirSync(outDir, { recursive: true });

const types = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript" };
const roots = [
  ["/three/", path.join(here, "node_modules", "three") + path.sep],
  ["/", path.join(here, "web") + path.sep],
];

// Servidor local mínimo: los módulos ES no se cargan desde file://
const server = http.createServer((req, res) => {
  const url = decodeURIComponent(new URL(req.url, "http://x").pathname);
  const [prefix, root] = roots.find(([p]) => url.startsWith(p));
  const file = path.normalize(path.join(root, url === "/" ? "index.html" : url.slice(prefix.length)));
  if (!file.startsWith(root) || !fs.existsSync(file)) return void res.writeHead(404).end();
  res.writeHead(200, { "content-type": types[path.extname(file)] ?? "application/octet-stream" }).end(fs.readFileSync(file));
});
await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
const base = `http://127.0.0.1:${server.address().port}`;

const t0 = Date.now();
const browser = await chromium.launch({
  args: ["--use-angle=swiftshader", "--use-gl=angle", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
page.on("pageerror", (e) => console.error("página:", e.message));
await page.goto(`${base}/index.html`);
await page.waitForFunction(() => window.moduleReady === true);
await page.evaluate((opts) => window.initStage(opts), { width, height, characters: timeline.characters });
console.log(`escenario listo en ${((Date.now() - t0) / 1000).toFixed(1)} s`);

const t1 = Date.now();
for (let i = 0; i < timeline.frames.length; i++) {
  await page.evaluate((frame) => window.applyFrame(frame), timeline.frames[i]);
  const png = await page.screenshot({ type: "png", omitBackground: true });
  fs.writeFileSync(path.join(outDir, `f_${String(i).padStart(5, "0")}.png`), png);
  if (i % 100 === 0) console.log(`fotograma ${i}/${timeline.frames.length}`);
}
const seconds = (Date.now() - t1) / 1000;
console.log(`${timeline.frames.length} fotogramas en ${seconds.toFixed(1)} s (${((seconds / timeline.frames.length) * 1000).toFixed(0)} ms cada uno)`);
await browser.close();
server.close();
