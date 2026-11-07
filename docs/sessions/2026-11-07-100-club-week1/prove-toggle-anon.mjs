import { createRequire } from 'module';
const require = createRequire('/Users/toka/code/toms_gym/frontend/package.json');
const { chromium } = require('playwright');
const url = 'https://my-frontend-quyiiugyoq-ue.a.run.app/challenges/32ca7bad-a970-4a09-acec-02b768793063';
const b = await chromium.launch({ headless: true });
for (const [w, h] of [[500, 723], [1280, 800]]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h } });
  const page = await ctx.newPage();
  await page.unrouteAll();
  await page.route((u) => true, (r) => ['PUT', 'POST', 'DELETE', 'PATCH'].includes(r.request().method()) ? r.fulfill({ status: 204, body: '' }) : r.continue());
  await page.goto(url, { waitUntil: 'load' }); await page.waitForTimeout(1500);
  await page.goto(url, { waitUntil: 'load' }); await page.waitForTimeout(3000);
  const anon = (await page.evaluate(() => document.body.innerText)).includes('Not logged yet');
  for (const who of ['caleb.li.larson', 'Toka']) {
    const btn = page.locator('button', { hasText: new RegExp(`${who.replace('.', '\\.')}\\s*·\\s*weeks`) }).first();
    const box = await btn.boundingBox();
    const hit = await page.evaluate(({ x, y }) => { const e = document.elementFromPoint(x, y); return e ? `${e.tagName}.${(e.className || '').toString().slice(0, 40)} "${(e.textContent || '').slice(0, 30)}"` : null; }, { x: box.x + box.width / 2, y: box.y + box.height / 2 });
    await btn.click({ trial: false });
    await page.waitForTimeout(500);
    const exp = await btn.getAttribute('aria-expanded');
    const t = await page.locator('[data-testid="week-table"]').count();
    console.log(w, 'anon=', anon, who, 'hit=', hit, 'aria-expanded=', exp, 'week-table count=', t, t ? JSON.stringify((await page.locator('[data-testid="week-table"]').first().innerText()).slice(0, 200)) : '');
  }
  await ctx.close();
}
await b.close();
