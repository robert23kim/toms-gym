import { createRequire } from 'module';
import fs from 'fs';
const require = createRequire('/Users/toka/code/toms_gym/frontend/package.json');
const { chromium } = require('playwright');
const D = '/Users/toka/code/toms_gym/docs/sessions/2026-11-07-declutter';
const F = 'https://my-frontend-quyiiugyoq-ue.a.run.app';
const OWNER = '7844e26d-e65c-4e9e-a4f6-9678041e61b4';
const live = JSON.parse(fs.readFileSync('/Users/toka/code/toms_gym/docs/sessions/2026-11-07-100-club-week1/live-before.json', 'utf8'));
const OTHER = live.rows.find((r) => r.user_id !== OWNER).user_id;
const results = [];
const check = (label, ok, detail = '') => { results.push({ label, ok, detail }); console.log(ok ? 'PASS' : 'FAIL', label, detail); };
const b = await chromium.launch({ headless: true });

async function session(name, uid, w, h, run) {
  const ctx = await b.newContext({ viewport: { width: w, height: h } });
  if (uid) await ctx.addInitScript((id) => { try { localStorage.setItem('userId', id); } catch (e) {} }, uid);
  const page = await ctx.newPage();
  await page.unrouteAll();
  const writes = [];
  const profileGets = [];
  await page.route(() => true, async (route) => {
    const m = route.request().method();
    const u = route.request().url();
    if (m !== 'GET' && m !== 'HEAD' && m !== 'OPTIONS') { writes.push(`${m} ${u}`); return route.fulfill({ status: 204, body: '' }); }
    if (/\/users\/[^/]+\/profile$/.test(u)) profileGets.push(u);
    return route.continue();
  });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  const tag = `${name}-${w}`;
  const go = async (path) => {
    await page.goto(`${F}${path}`, { waitUntil: 'load' });
    await page.waitForTimeout(1500);
    await page.goto(`${F}${path}`, { waitUntil: 'load' });
    await page.waitForTimeout(2500);
  };
  const navHrefs = async () => page.evaluate(() => [...document.querySelectorAll('header a, nav[aria-label="Primary"] a')].map((a) => a.getAttribute('href')));
  const text = async () => page.evaluate(() => document.body.innerText);
  const iw = async () => page.evaluate(() => window.innerWidth);
  await run({ page, go, navHrefs, text, iw, tag, profileGets, writes });
  fs.writeFileSync(`${D}/prove-${tag}.txt`, `profileGets=${JSON.stringify(profileGets)}\nwrites=${JSON.stringify(writes)}\nerrors=${JSON.stringify(errors)}\n`);
  check(`${tag} only boot telemetry tried to write, all answered locally`, writes.every((x) => x.endsWith('/log-error')), writes.join(' | '));
  check(`${tag} no console/page errors`, errors.length === 0, errors.slice(0, 3).join(' | '));
  await ctx.close();
}

for (const [w, h] of [[1280, 800], [390, 844]]) {
  const phone = w < 768;
  await session('anon', null, w, h, async ({ go, navHrefs, text, iw, tag, page }) => {
    await go('/');
    check(`${tag} innerWidth`, (await iw()) === w);
    const hrefs = await navHrefs();
    check(`${tag} nav has no bowl/golf`, !hrefs.includes('/bowl') && !hrefs.includes('/golf'), hrefs.join(','));
    check(`${tag} nav has lift`, hrefs.includes('/lift'), '');
    if (phone) check(`${tag} tab bar has 4 tabs`, (await page.locator('nav[aria-label="Primary"] a').count()) === 4, '');
    const t = await text();
    check(`${tag} lift-only pitch`, t.includes('AI analysis of your lift — in minutes.'), '');
    check(`${tag} no bowl/golf demo scenes`, !t.includes('ball tracking') && !t.includes('scorecard'), '');
    check(`${tag} no bowling/golf to-do rows`, !/bowling|golf/i.test(t), (t.match(/[^\n]*(bowling|golf)[^\n]*/i) || [''])[0]);
    await go('/upload');
    const up = await page.evaluate(() => [...document.querySelectorAll('main a, a')].map((a) => a.getAttribute('href')).filter((h) => h && /upload|snap/.test(h)));
    check(`${tag} upload chooser lift only`, up.includes('/lift/upload') && !up.some((h) => /bowling|golf/.test(h)), up.join(','));
    await go('/challenges');
    const c1 = await text();
    check(`${tag} challenges Open now has 100 Club`, /open now/i.test(c1) && c1.includes('The 100 Club'), '');
    const toggle = page.locator('[data-testid="past-challenges-toggle"]');
    const n = await toggle.count();
    check(`${tag} past toggle present`, n === 1, `count=${n}`);
    if (n) {
      const label = (await toggle.textContent()).trim();
      const past = parseInt((label.match(/\((\d+)\)/) || [0, '0'])[1], 10);
      check(`${tag} past challenges collapsed`, /Past challenges \(\d+\)/.test(label) && (await toggle.getAttribute('aria-expanded')) === 'false', label);
      const rowsBefore = await page.locator('a[href^="/challenges/"]').count();
      await toggle.click();
      await page.waitForTimeout(400);
      const rowsAfter = await page.locator('a[href^="/challenges/"]').count();
      check(`${tag} toggle reveals ${past} past rows`, rowsAfter - rowsBefore === past && (await toggle.textContent()).includes('Hide past challenges'), `before=${rowsBefore} after=${rowsAfter}`);
      const c2 = await text();
      check(`${tag} past rows say Results`, c2.includes('Results'), '');
      check(`${tag} no Bowling challenge in past list`, !/^Bowling$/m.test(c2), (c2.match(/^Bowling.*$/m) || [''])[0]);
    }
  });

  await session('owner', OWNER, w, h, async ({ go, navHrefs, text, tag, page, profileGets }) => {
    await go('/');
    const hrefs = await navHrefs();
    check(`${tag} nav has bowl and golf`, hrefs.includes('/bowl') && hrefs.includes('/golf'), hrefs.join(','));
    if (phone) check(`${tag} tab bar has 6 tabs`, (await page.locator('nav[aria-label="Primary"] a').count()) === 6, '');
    check(`${tag} owner resolved via profile GET`, profileGets.some((u) => u.includes(OWNER)), profileGets.join(','));
    const t = await text();
    if (phone) check(`${tag} home has bowling and golf rows`, t.includes("Snap tonight's bowling recap") && t.includes('Snap a golf scorecard'), '');
    await go(`/profile/${OWNER}`);
    const tabs = await page.evaluate(() => [...document.querySelectorAll('button')].map((b) => b.innerText.trim()).filter((x) => /^(Lift|Bowl|Golf)/.test(x)));
    check(`${tag} profile has Bowl and Golf tabs`, tabs.some((x) => x.startsWith('Bowl')) && tabs.some((x) => x.startsWith('Golf')), tabs.join(','));
    await go('/upload');
    const up = await page.evaluate(() => [...document.querySelectorAll('a')].map((a) => a.getAttribute('href')).filter((h) => h && /upload|snap/.test(h)));
    check(`${tag} upload chooser all three`, ['/lift/upload', '/bowling/upload', '/golf/snap'].every((h) => up.includes(h)), up.join(','));
    await go('/challenges');
    const ownerToggle = page.locator('[data-testid="past-challenges-toggle"]');
    const ownerLabel = (await ownerToggle.textContent()).trim();
    await ownerToggle.click();
    await page.waitForTimeout(400);
    const oc = await text();
    check(`${tag} owner sees the Bowling challenge in the past list`, /^Bowling$/m.test(oc), ownerLabel);
  });

  await session('other', OTHER, w, h, async ({ go, navHrefs, text, tag, page }) => {
    await go('/');
    const hrefs = await navHrefs();
    check(`${tag} nav has no bowl/golf`, !hrefs.includes('/bowl') && !hrefs.includes('/golf'), hrefs.join(','));
    if (phone) check(`${tag} tab bar has 4 tabs`, (await page.locator('nav[aria-label="Primary"] a').count()) === 4, '');
    const t = await text();
    check(`${tag} no bowling/golf to-do rows`, !/bowling|golf/i.test(t), '');
    await go(`/profile/${OTHER}`);
    const tabs = await page.evaluate(() => [...document.querySelectorAll('button')].map((b) => b.innerText.trim()).filter((x) => /^(Lift|Bowl|Golf)/.test(x)));
    check(`${tag} profile hides Bowl and Golf tabs`, !tabs.some((x) => /^(Bowl|Golf)/.test(x)), tabs.join(','));
  });
}
await b.close();
const failed = results.filter((r) => !r.ok);
fs.writeFileSync(`${D}/prove-results.json`, JSON.stringify(results, null, 2));
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
process.exit(failed.length ? 1 : 0);
