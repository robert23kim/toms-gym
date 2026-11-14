import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire("/Users/toka/code/toms_gym/frontend/package.json");
const { chromium } = require("playwright");
const here = path.dirname(new URL(import.meta.url).pathname);
const FIX = "/Users/toka/code/bowling-app/perf-fixtures-2026-11-13";
const PORT = 47613;
const roots = { "/fx/": FIX + "/", "/media/": here + "/media/" };
let telemetry = []; let puts = [];
const readBody = (req) => new Promise((r) => { let n = 0; const chunks = []; req.on("data", (c) => { n += c.length; if (n < 100000) chunks.push(c); }); req.on("end", () => r({ n, text: n < 100000 ? Buffer.concat(chunks).toString() : "" })); });
const json = (res, o) => { res.setHeader("content-type", "application/json"); res.end(JSON.stringify(o)); };
const server = http.createServer(async (req, res) => {
  const u = decodeURIComponent(req.url.split("?")[0]);
  const base = `http://127.0.0.1:${PORT}`;
  if (u === "/") { res.setHeader("content-type", "text/html"); return res.end('<!doctype html><script src="/bundle2.js"></script>'); }
  if (u === "/bundle2.js") { res.setHeader("content-type", "text/javascript"); return fs.createReadStream(here + "/bundle2.js").pipe(res); }
  if (u === "/api/log-error") { const b = await readBody(req); telemetry.push({ bytes: b.n, contentType: req.headers["content-type"], body: JSON.parse(b.text) }); res.statusCode = 204; return res.end(); }
  if (u === "/api/upload/signed-url") { await readBody(req); return json(res, { upload_url: `${base}/gcs/single`, object_name: "videos/perf-bench-local.mp4", public_url: `${base}/gcs/single`, content_type: "video/mp4" }); }
  if (u === "/api/upload/composite/sign") { const b = JSON.parse((await readBody(req)).text); return json(res, { final_object: "videos/perf-bench-local.mp4", public_url: `${base}/gcs/final`, content_type: b.content_type, parts: Array.from({ length: b.parts }, (_, i) => ({ part_number: i + 1, object_name: `p${i + 1}`, upload_url: `${base}/gcs/part${i + 1}` })) }); }
  if (u === "/api/upload/composite/complete") { await readBody(req); return json(res, { public_url: `${base}/gcs/final` }); }
  if (u === "/api/upload/finalize") { await readBody(req); return json(res, { url: `${base}/gcs/final`, attempt_id: "perf-bench-local-attempt" }); }
  if (u.startsWith("/gcs/") && req.method === "PUT") { const b = await readBody(req); puts.push({ target: u, bytes: b.n }); return res.end(); }
  for (const [pre, dir] of Object.entries(roots)) {
    if (u.startsWith(pre)) { const p = path.join(dir, path.basename(u)); if (fs.existsSync(p)) { res.setHeader("content-type", "video/mp4"); res.setHeader("content-length", fs.statSync(p).size); return fs.createReadStream(p).pipe(res); } }
  }
  res.statusCode = 404; res.end("nope");
});
await new Promise((r) => server.listen(PORT, "127.0.0.1", r));
const cases = JSON.parse(process.argv[2]); const outPath = process.argv[3];
const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--autoplay-policy=no-user-gesture-required"] });
const results = [];
try {
  for (const c of cases) {
    telemetry = []; puts = [];
    const page = await browser.newPage();
    const outside = [];
    page.on("request", (rq) => { if (!rq.url().startsWith(`http://127.0.0.1:${PORT}/`)) outside.push(rq.url()); });
    await page.goto(`http://127.0.0.1:${PORT}/`);
    let r;
    try { r = await page.evaluate(([url, name, lift, comp]) => window.runUpload(url, name, lift, comp), [c.url, c.name, c.lift, c.compression]); }
    catch (e) { r = { error: String(e).slice(0, 300) }; }
    await page.waitForTimeout(300);
    const row = { label: c.label, chrome: browser.version(), ...r, puts, requestsOutsideLocalhost: outside, telemetry: telemetry.filter((t) => t.body.action === "upload-timing") };
    results.push(row); console.log(JSON.stringify(row));
    fs.writeFileSync(outPath, JSON.stringify(results, null, 1));
    await page.close();
  }
} finally { await browser.close(); server.close(); }
