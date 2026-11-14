import { createRequire } from 'module';
import { writeFileSync } from 'fs';
const require = createRequire('/Users/toka/code/toms_gym/frontend/package.json');
const { chromium } = require('playwright');
const PROD_API = 'https://my-python-backend-quyiiugyoq-ue.a.run.app';
const LOCAL = 'http://localhost:5199';
const CID = '32ca7bad-a970-4a09-acec-02b768793063';
const DIR = '/Users/toka/code/toms_gym/docs/sessions/2026-11-13-caleb-feedback/';
const b = await chromium.launch();
for (const [label, uid] of [['anon', null], ['reporter', 'b7bb417c-9407-42c5-9cee-be7816d03f13'], ['control-unknown-id', '00000000-0000-0000-0000-000000000000']]) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  if (uid) await ctx.addInitScript((id) => localStorage.setItem('userId', id), uid);
  const page = await ctx.newPage();
  await page.unrouteAll();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  let apiGets = 0, blocked = 0;
  await page.route((u) => !u.href.startsWith(LOCAL), async (r) => {
    const req = r.request();
    if (req.method() !== 'GET') { blocked++; console.log('stubbed', req.method(), req.url()); return r.fulfill({ status: 200, contentType: 'application/json', body: '{}' }); }
    const u = new URL(req.url());
    if (u.host.startsWith('localhost:5000') || u.host.startsWith('127.0.0.1:5000')) {
      apiGets++;
      const resp = await r.fetch({ url: PROD_API + u.pathname + u.search });
      return r.fulfill({ response: resp, headers: { ...resp.headers(), 'access-control-allow-origin': '*' } });
    }
    return r.continue();
  });
  await page.goto(`${LOCAL}/challenges/${CID}`);
  await page.waitForTimeout(1500);
  await page.waitForSelector('[data-testid="podium"]', { timeout: 30000 }).catch(() => {});
  const pick = async (sel) => { const el = page.locator(sel).first(); return (await el.count()) ? await el.innerText() : '(absent)'; };
  const youRow = await pick('[data-testid="you-row"]');
  const unknown = await pick('[data-testid="you-row-unknown"]');
  const unknownHref = (await page.locator('[data-testid="you-row-unknown"]').count()) ? await page.locator('[data-testid="you-row-unknown"]').first().getAttribute('href') : '(absent)';
  const ring = await pick('[data-testid="consistency-ring-count"]');
  const podium = await pick('[data-testid="podium"]');
  const note = await pick('[data-testid="scoring-note"]');
  const bonus = await pick('[data-testid="consistency-bonus-note"]');
  const notLogged = await page.getByText('Not logged yet').count();
  const out = [
    `local ${LOCAL} (vite dev, HEAD build), 390x844, userId=${uid ?? '(empty storage)'}, innerWidth ${await page.evaluate(() => window.innerWidth)}`,
    `api GETs proxied to prod: ${apiGets}; non-GETs fulfilled with stub: ${blocked}; page errors: ${errors.length} ${errors.join(' | ')}`,
    `podium present: ${podium !== '(absent)'}`,
    `YOU-ROW (data-testid=you-row): ${youRow}`,
    `YOU-ROW-UNKNOWN (data-testid=you-row-unknown): ${unknown}`,
    `you-row-unknown href: ${unknownHref}`,
    `"Not logged yet" occurrences: ${notLogged}`,
    `hero ring count: ${ring}`,
    `scoring note: ${note}`,
    `bonus note: ${bonus}`,
  ].join('\n') + '\n';
  writeFileSync(`${DIR}local-you-row-${label}.txt`, out);
  console.log(out);
  await page.screenshot({ path: `${DIR}local-you-row-${label}.png`, fullPage: true });
  for (const sel of ['you-row-unknown', 'you-row']) {
    const el = page.locator(`[data-testid="${sel}"]`).first();
    if (await el.count()) {
      await el.screenshot({ path: `${DIR}local-${sel}-${label}-el.png` });
      const clipped = await el.evaluate((n) => [...n.querySelectorAll('.truncate')].map((t) => t.scrollWidth > t.clientWidth));
      console.log(`${sel} truncated children: ${JSON.stringify(clipped)}`);
    }
  }
  if (label === 'anon' && unknownHref !== '(absent)') {
    await page.locator('[data-testid="you-row-unknown"]').first().click();
    await page.waitForTimeout(800);
    console.log('after click:', page.url());
  }
  await ctx.close();
}
await b.close();
