import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire("/Users/toka/code/toms_gym/frontend/package.json");
const { chromium } = require("playwright");

const here = path.dirname(new URL(import.meta.url).pathname);
const FIX = "/Users/toka/code/bowling-app/perf-fixtures-2026-11-13";
const roots = { "/fx/": FIX + "/", "/media/": here + "/media/" };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split("?")[0]);
  if (u === "/") { res.setHeader("content-type", "text/html"); res.end('<!doctype html><script src="/bundle.js"></script>'); return; }
  if (u === "/bundle.js") { res.setHeader("content-type", "text/javascript"); fs.createReadStream(here + "/bundle.js").pipe(res); return; }
  for (const [pre, dir] of Object.entries(roots)) {
    if (u.startsWith(pre)) {
      const p = path.join(dir, path.basename(u));
      if (fs.existsSync(p)) { res.setHeader("content-type", "video/mp4"); res.setHeader("content-length", fs.statSync(p).size); fs.createReadStream(p).pipe(res); return; }
    }
  }
  res.statusCode = 404; res.end("nope");
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const port = server.address().port;
const cases = JSON.parse(process.argv[2]);
const outPath = process.argv[3];
const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--autoplay-policy=no-user-gesture-required"] });
const results = [];
try {
  const version = browser.version();
  for (const c of cases) {
    const page = await browser.newPage();
    await page.goto(`http://127.0.0.1:${port}/`);
    const t0 = Date.now();
    let r;
    try {
      r = await page.evaluate(([url, name, fast]) => window.runCompress(url, name, fast), [c.url, c.name, c.fast]);
    } catch (e) { r = { name: c.name, error: String(e).slice(0, 300) }; }
    r.label = c.label; r.wallMs = Date.now() - t0; r.chrome = version; r.clipSeconds = c.dur;
    results.push(r);
    console.log(JSON.stringify(r));
    fs.writeFileSync(outPath, JSON.stringify(results, null, 1));
    await page.close();
  }
} finally { await browser.close(); server.close(); }
