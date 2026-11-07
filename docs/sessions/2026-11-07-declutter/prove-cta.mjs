import { createRequire } from "module";
const require = createRequire("/Users/toka/code/toms_gym/frontend/package.json");
const { chromium } = require("playwright");
const FRONT = "https://my-frontend-quyiiugyoq-ue.a.run.app";
const ID = "32ca7bad-a970-4a09-acec-02b768793063";
const OWNER = "7844e26d-e65c-4e9e-a4f6-9678041e61b4";
const browser = await chromium.launch();
const results = [];
const check = (name, ok, detail) => { results.push({ name, ok, detail }); console.log(`${ok ? "PASS" : "FAIL"} ${name} ${detail ?? ""}`); };
for (const [label, userId] of [["anonymous", null], ["owner", OWNER]]) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  if (userId) await ctx.addInitScript((id) => localStorage.setItem("userId", id), userId);
  const page = await ctx.newPage();
  await page.unrouteAll();
  const writes = [];
  await page.route((u) => true, (route) => {
    const r = route.request();
    if (r.method() !== "GET" && r.method() !== "HEAD" && r.method() !== "OPTIONS") { writes.push(`${r.method()} ${r.url()}`); return route.fulfill({ status: 204 }); }
    return route.continue();
  });
  await page.goto(`${FRONT}/challenges/${ID}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  const stamp = await page.locator('meta[name="build-timestamp"]').getAttribute("content").catch(() => null);
  const cta = page.locator("div.fixed.inset-x-0").filter({ has: page.locator("button") }).first();
  await cta.waitFor({ state: "visible", timeout: 15000 });
  const btn = cta.locator("button");
  const tab = page.locator("nav").filter({ hasText: "Home" }).last();
  const b = await btn.boundingBox();
  const t = await tab.boundingBox();
  const vh = await page.evaluate(() => window.innerHeight);
  const vw = await page.evaluate(() => window.innerWidth);
  check(`${label}: viewport is phone`, vw === 390, `${vw}x${vh}`);
  check(`${label}: upload button visible`, !!b && b.height > 30, JSON.stringify(b));
  check(`${label}: tab bar at bottom`, !!t && Math.round(t.y + t.height) >= vh - 1, JSON.stringify(t));
  check(`${label}: button bottom above tab bar top`, !!b && !!t && b.y + b.height <= t.y + 0.5, `btn bottom ${b && (b.y + b.height)} tab top ${t && t.y}`);
  const hit = await page.evaluate(() => { const el = document.querySelector('div.fixed.inset-x-0 button'); const r = el.getBoundingClientRect(); const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return el.contains(top) || top === el; });
  check(`${label}: tap at button centre hits the button`, hit);
  check(`${label}: only boot telemetry tried to write, all answered locally`, writes.every((w) => w.includes("/log-error")), writes.join(" | "));
  await page.screenshot({ path: `docs/sessions/2026-11-07-declutter/prove-cta-${label}.png` });
  results.push({ name: `${label}: build stamp`, ok: true, detail: stamp });
  await ctx.close();
}
await browser.close();
const fails = results.filter((r) => !r.ok).length;
console.log(`${results.length - fails}/${results.length} passed`);
process.exit(fails ? 1 : 0);
