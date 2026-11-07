import { createRequire } from 'module';
import fs from 'fs';
const require = createRequire('/Users/toka/code/toms_gym/frontend/package.json');
const { chromium } = require('playwright');
const D = '/Users/toka/code/toms_gym/docs/sessions/2026-11-07-100-club-week1';
const F = 'https://my-frontend-quyiiugyoq-ue.a.run.app';
const C = '32ca7bad-a970-4a09-acec-02b768793063';
const U = '7844e26d-e65c-4e9e-a4f6-9678041e61b4';
const live = JSON.parse(fs.readFileSync(`${D}/live-before.json`, 'utf8'));
const me = live.rows.find((r) => r.user_id === U);
const days = live.consistency.days_left;
const pages = {
  challenge: `${F}/challenges/${C}`,
  home: `${F}/`,
  video: `${F}/challenges/${C}/participants/${U}/video/${me.attempt_id}`,
};
const results = [];
const check = (label, ok, detail = '') => { results.push({ label, ok, detail }); console.log(ok ? 'PASS' : 'FAIL', label, detail); };
const b = await chromium.launch({ headless: true });
for (const [w, h] of [[1280, 800], [390, 844]]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h } });
  await ctx.addInitScript((uid) => { try { localStorage.setItem('userId', uid); } catch (e) {} }, U);
  const page = await ctx.newPage();
  await page.unrouteAll();
  const blocked = [];
  await page.route((url) => true, async (route) => {
    const m = route.request().method();
    if (m === 'PUT' || m === 'POST' || m === 'DELETE' || m === 'PATCH') { blocked.push(`${m} ${route.request().url()} ${(route.request().postData() || '').slice(0, 400)} @${page.url()}`); return route.fulfill({ status: 204, body: '' }); }
    return route.continue();
  });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  let first = true;
  for (const [name, url] of Object.entries(pages)) {
    await page.goto(url, { waitUntil: 'load' });
    if (first) { await page.waitForTimeout(1500); first = false; await page.goto(url, { waitUntil: 'load' }); }
    await page.waitForTimeout(3000);
    const iw = await page.evaluate(() => window.innerWidth);
    const ls = await page.evaluate(() => localStorage.getItem('userId'));
    let text = await page.evaluate(() => document.body.innerText);
    if (name === 'challenge') {
      const btn = page.locator('button', { hasText: /Toka\s*·\s*weeks/ }).first();
      const n = await btn.count();
      if (n) {
        await btn.click();
        await page.waitForTimeout(500);
        const exp = await btn.getAttribute('aria-expanded');
        const table = (await page.locator('[data-testid="week-table"]').count()) ? await page.locator('[data-testid="week-table"]').first().innerText() : '(no week-table)';
        text += `\n\n=== after clicking "Toka · weeks" (aria-expanded=${exp}) ===\n${table}`;
        check(`${w} toggle expands week table`, exp === 'true' && table !== '(no week-table)', `aria-expanded=${exp}`);
        check(`${w} week row locks Sun lead`, /Situp · locks Sun/.test(table), '');
        { const tl = (table.split('\n').find((l) => /Plank \d/.test(l)) || ''); check(`${w} per-type line`, ['Situp 40', 'Pushup 52', 'Plank 8 (82.8 s)'].every((x) => tl.split(' · ').includes(x)), tl); }
      } else check(`${w} toggle present`, false, 'no Toka weeks button');
    }
    fs.writeFileSync(`${D}/prove-viewer-${name}-${w}.txt`, `innerWidth=${iw} localStorage.userId=${ls}\n${text}`);
    check(`${w} ${name} innerWidth`, iw === w, `innerWidth=${iw}`);
    if (name === 'challenge') {
      check(`${w} ring`, text.includes(`${me.this_week.lifts}\n/ ${me.this_week.quota}`) || text.includes(`${me.this_week.lifts} / ${me.this_week.quota}`) || new RegExp(`${me.this_week.lifts}\\s*/\\s*${me.this_week.quota}`).test(text), (text.match(/\d+(\.\d+)?\s*\/\s*\d+[^\n]*/) || [''])[0]);
      check(`${w} You lead`, text.includes(`You lead ${me.this_week.leading.join(', ')} this week`), (text.match(/You lead[^\n]*/) || ['(none)'])[0]);
      check(`${w} tie line`, text.includes('caleb.li.larson and Toka are tied on points; more lifts this week puts caleb.li.larson ahead.'), (text.match(/tied[^\n]*/) || ['(none)'])[0]);
      check(`${w} bonus-lock line`, text.includes('Type bonuses (+25 each) are added when the week ends on Sunday.'));
      check(`${w} week line`, text.includes(`Week 1 of 8 · ${days} days left`), (text.match(/Week \d of 8[^\n]*/) || ['(none)'])[0]);
      check(`${w} pill`, text.includes('Ongoing · ends Sun 27 Dec'), (text.match(/Ongoing[^\n]*/) || ['(none)'])[0]);
      check(`${w} no Everyone else`, !text.includes('Everyone else'));
      check(`${w} viewer not shown as "Not logged yet"`, !text.includes('Not logged yet'));
    }
    if (name === 'home') {
      const pill = `${me.this_week.lifts} / ${me.this_week.quota} · ${days} days left`;
      const hasRow = text.includes('The 100 Club');
      check(`${w} home 100 Club row`, w < 768 ? hasRow : true, `hasRow=${hasRow} (to-do list is phone-only by design)`);
      check(`${w} home pill`, w < 768 ? text.includes(pill) : true, `expected "${pill}" present=${text.includes(pill)}`);
    }
    if (name === 'video') {
      const block = (await page.locator('[data-testid="consistency-result"]').count()) ? await page.locator('[data-testid="consistency-result"]').first().innerText() : null;
      check(`${w} video consistency block`, !!block, JSON.stringify(block));
      check(`${w} video no ladder`, !/Beat this/.test(text) && !/to pass/.test(text));
      check(`${w} video owner wording`, !!block && block.includes(`${me.this_week.lifts} / ${me.this_week.quota} this week`) && !/^Toka:/m.test(block), '');
    }
  }
  check(`${w} no page errors`, errors.length === 0, JSON.stringify(errors.slice(0, 5)));
  console.log(`${w} blocked writes:`, JSON.stringify(blocked));
  check(`${w} deployed build 1794067886 served`, blocked.some((x) => x.includes('"build":1794067886')), JSON.stringify(blocked.map((x) => (x.match(/"build":\d+/) || [''])[0])));
  await ctx.close();
}
await b.close();
fs.writeFileSync(`${D}/prove-viewer-results.json`, JSON.stringify(results, null, 1));
console.log('FAILS', results.filter((r) => !r.ok).length, 'of', results.length);
