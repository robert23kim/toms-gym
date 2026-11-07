import { createRequire } from "module";
const require = createRequire("/Users/toka/code/toms_gym/frontend/package.json");
const { chromium } = require("playwright");
const FRONT = "https://my-frontend-quyiiugyoq-ue.a.run.app";
const API = "https://my-python-backend-quyiiugyoq-ue.a.run.app";
const ID = "32ca7bad-a970-4a09-acec-02b768793063";
const OWNER = "7844e26d-e65c-4e9e-a4f6-9678041e61b4";
const OTHER = "b7bb417c-9407-42c5-9cee-be7816d03f13";

const board = await (await fetch(`${API}/competitions/${ID}/leaderboard`)).json();
const lifts = (await (await fetch(`${API}/competitions/${ID}/lifts`)).json()).lifts;
const rules = board.consistency.rules;
const weekIdx = board.consistency.week_index;
const weekOf = (iso) => {
  const local = new Intl.DateTimeFormat("en-CA", { timeZone: rules.tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(iso));
  return Math.floor((Date.parse(`${local}T00:00:00Z`) - Date.parse(`${rules.week_start}T00:00:00Z`)) / (7 * 86400000)) + 1;
};
const fmt = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

const results = [];
const check = (name, ok, detail) => { results.push({ name, ok, detail }); console.log(`${ok ? "PASS" : "FAIL"} ${name} ${detail ?? ""}`); };
const browser = await chromium.launch();

for (const [label, userId] of [["owner", OWNER], ["other", OTHER], ["anonymous", null]]) {
  const row = userId ? board.rows.find((r) => r.user_id === userId) : null;
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  if (userId) await ctx.addInitScript((id) => localStorage.setItem("userId", id), userId);
  const page = await ctx.newPage();
  await page.unrouteAll();
  const writes = [];
  await page.route(() => true, (route) => {
    const r = route.request();
    if (!["GET", "HEAD", "OPTIONS"].includes(r.method())) { writes.push(`${r.method()} ${r.url()}`); return route.fulfill({ status: 204 }); }
    return route.continue();
  });
  await page.goto(`${FRONT}/challenges/${ID}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  const stamp = await page.locator('meta[name="build-timestamp"]').getAttribute("content").catch(() => null);
  check(`${label}: build stamp present`, !!stamp, stamp);
  await page.getByTestId("consistency-hero").waitFor({ timeout: 15000 });

  if (!row) {
    check(`${label}: no ring, legend or receipt`, (await page.getByTestId("consistency-legend").count()) === 0 && (await page.getByTestId("consistency-receipt").count()) === 0 && (await page.getByTestId("consistency-ring-count").count()) === 0);
    check(`${label}: no uploads toggle`, (await page.getByTestId("consistency-uploads-toggle").count()) === 0);
  } else {
    const w = row.this_week;
    const quota = w.quota, lifted = w.lifts;
    check(`${label}: ring count matches board`, (await page.getByTestId("consistency-ring-count").textContent()).replace(/\s+/g, " ").trim() === `${fmt(lifted)} / ${quota}`, await page.getByTestId("consistency-ring-count").textContent());
    const expectTypes = board.lift_types.filter((t) => (w.by_type[t] ?? 0) > 0);
    const segs = await page.locator('[data-testid^="consistency-ring-seg-"]').evaluateAll((els) => els.map((e) => [e.dataset.testid.replace("consistency-ring-seg-", ""), Number(e.dataset.fraction)]));
    check(`${label}: one ring segment per type with lifts`, segs.map((s) => s[0]).join(",") === expectTypes.join(","), JSON.stringify(segs));
    const denom = Math.max(quota, lifted);
    check(`${label}: segment fractions are by_type / max(quota, lifts)`, segs.length > 0 && segs.every(([t, f]) => Math.abs(f - w.by_type[t] / denom) < 1e-6), `denominator ${denom}`);
    for (const t of board.lift_types) {
      const txt = (await page.getByTestId(`consistency-legend-${t}`).textContent()).replace(/\s+/g, "");
      const want = `${t}${fmt(w.by_type[t] ?? 0)}`;
      check(`${label}: legend ${t} reads board value`, txt.startsWith(want), txt);
      if (t === "Plank" && (w.by_type.Plank ?? 0) > 0) check(`${label}: legend Plank shows seconds`, txt.includes(`·${fmt(Number(w.plank_seconds.toFixed(1)))}s`), txt);
      const hasLead = txt.toLowerCase().includes("lead");
      check(`${label}: legend ${t} lead badge iff leading`, hasLead === w.leading.includes(t), `leading=${w.leading.join("/")}`);
    }
    const banked = Math.min(lifted, quota);
    const total = banked + (w.met ? rules.quota_bonus : 0);
    const receipt = (await page.getByTestId("consistency-receipt").textContent()).replace(/\s+/g, "");
    check(`${label}: receipt banked line`, receipt.includes(`Liftsbanked${fmt(banked)}of${quota}+${fmt(banked)}`), receipt.slice(0, 160));
    check(`${label}: receipt quota bonus ${w.met ? "earned" : "withheld"}`, (await page.getByTestId("receipt-quota").getAttribute("data-earned")) === String(w.met));
    for (const t of w.leading) check(`${label}: receipt pending lead ${t}`, (await page.getByTestId(`receipt-lead-${t}`).textContent()).includes("locks Sun"));
    check(`${label}: receipt total ${total} pts`, (await page.getByTestId("receipt-total").textContent()).includes(`${fmt(total)} pts this week`), await page.getByTestId("receipt-total").textContent());
    check(`${label}: receipt total equals board score this week`, total === row.score || row.weeks.length > 1, `score ${row.score}`);
    if (w.leading.length) check(`${label}: projection if leads hold`, (await page.getByTestId("receipt-total").textContent()).includes(`${fmt(total + w.leading.length * rules.type_bonus)} if the`));

    const mine = lifts.filter((l) => l.participant_id === userId && weekOf(l.created_at) === weekIdx);
    const toggle = page.getByTestId("consistency-uploads-toggle");
    await toggle.waitFor({ timeout: 10000 });
    check(`${label}: uploads toggle counts this week's uploads`, (await toggle.textContent()).includes(`· ${mine.length}`), await toggle.textContent());
    check(`${label}: uploads collapsed by default`, (await toggle.getAttribute("aria-expanded")) === "false" && (await page.getByTestId("consistency-uploads").count()) === 0);
    await toggle.click();
    const list = page.getByTestId("consistency-uploads");
    await list.waitFor();
    const rows = await list.locator('[data-testid^="consistency-upload-"]:not([data-testid="consistency-upload-day"])').evaluateAll((els) => els.map((e) => [e.dataset.testid.replace("consistency-upload-", ""), e.textContent.replace(/\s+/g, " ").trim(), e.getAttribute("href")]));
    const wantIds = [...mine].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)).map((l) => l.id);
    check(`${label}: upload rows are this week's attempts newest first`, rows.map((r) => r[0]).join(",") === wantIds.join(","), rows.map((r) => r[0]).join(","));
    check(`${label}: every row links to its video`, rows.every((r) => r[2] === `/challenges/${ID}/participants/${userId}/video/${r[0]}`));
    const sum = rows.reduce((n, r) => { const m = r[1].match(/\+(\d+(?:\.\d+)?)$/); return n + (m ? Number(m[1]) : 0); }, 0);
    check(`${label}: upload lifts sum to the board's week total`, Math.abs(sum - lifted) < 1e-6 && !rows.some((r) => /analysing|failed/.test(r[1])), `rows sum ${sum} vs board ${lifted}`);
    const tapOk = await page.evaluate(() => { const el = document.querySelector('[data-testid="consistency-uploads-toggle"]'); const r = el.getBoundingClientRect(); return r.height >= 44; });
    check(`${label}: toggle is a 44px target`, tapOk);
    await page.screenshot({ path: `docs/sessions/2026-11-07-declutter/prove-breakdown-${label}.png`, fullPage: true });
  }
  check(`${label}: only boot telemetry tried to write, all answered locally`, writes.every((x) => x.includes("/log-error")), writes.join(" | "));
  await ctx.close();
}
await browser.close();
const fails = results.filter((r) => !r.ok).length;
console.log(`${results.length - fails}/${results.length} passed`);
process.exit(fails ? 1 : 0);
