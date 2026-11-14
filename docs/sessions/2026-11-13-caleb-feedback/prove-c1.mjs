// Read-only production proof for C1/C2. Every non-GET is fulfilled with a stub; identity GETs
// (by-email, the fake attempt's result) are stubbed so no typed address reaches prod.
import { createRequire } from 'module';
import fs from 'fs';
import crypto from 'crypto';
const require = createRequire('/Users/toka/code/toms_gym/frontend/package.json');
const { chromium } = require('playwright');

const DIR = '/Users/toka/code/toms_gym/docs/sessions/2026-11-13-caleb-feedback';
const FE = process.env.FE || 'https://my-frontend-quyiiugyoq-ue.a.run.app';
const CLUB = '32ca7bad-a970-4a09-acec-02b768793063';
const REPORTER = 'b7bb417c-9407-42c5-9cee-be7816d03f13';
const FAKE_EMAIL = 'prover@example.invalid';
const FAKE_ATTEMPT = '00000000-0000-4000-8000-00000000fa7e';
const BOARD = `${FE}/challenges/${CLUB}`;
const OLD = 'Most of a lift type in a week';
const NEW = process.env.NEW || 'nobody logs more than you';
const OLD1 = 'nobody logs more than you';
const OUTDIR = process.env.OUTDIR || `${DIR}/prove`;
const live = JSON.parse(fs.readFileSync(process.env.LIVE || `${DIR}/prove/lb-prove.json`, 'utf8'));
const liveMe = live.rows.find((r) => r.user_id === REPORTER);

const only = (process.env.CASES || '').split(',').filter(Boolean);
const widths = (process.env.WIDTHS || '390x844,1280x800').split(',').map((s) => s.split('x').map(Number));
const tag = process.env.TAG || '';

function cors(req) {
  const h = req.headers();
  return {
    'content-type': 'application/json',
    'access-control-allow-origin': h.origin || FE,
    'access-control-allow-credentials': 'true',
    'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
    'access-control-allow-headers': h['access-control-request-headers'] || 'content-type,authorization',
  };
}

async function run(caseName, w, h) {
  const holder = {};
  try { return await runInner(caseName, w, h, holder); } catch (e) { e.partialOut = holder.out; try { await holder.browser?.close(); } catch {} throw e; }
}
async function runInner(caseName, w, h, holder) {
  const out = { case: caseName + tag, width: w, checks: {}, stubbed: [], stubbedGets: [], console: [], pageerrors: [] };
  holder.out = out;
  const b = await chromium.launch();
  holder.browser = b;
  const ctx = await b.newContext({ viewport: { width: w, height: h } });
  await ctx.unrouteAll();
  if (caseName === 'reporter' || caseName === 'synthetic-table') {
    await ctx.addInitScript((id) => { try { localStorage.setItem('userId', id); } catch {} }, REPORTER);
  }
  if (caseName === 'random') {
    const rnd = crypto.randomUUID();
    out.randomId = rnd;
    await ctx.addInitScript((id) => { try { localStorage.setItem('userId', id); } catch {} }, rnd);
  }
  await ctx.route((u) => true, async (route) => {
    const req = route.request();
    const m = req.method();
    const url = req.url();
    if (m !== 'GET') {
      out.stubbed.push(`${m} ${url.split('?')[0]}`);
      if (url.includes('/log-error')) out.logErrorBodies = [...(out.logErrorBodies || []), (req.postData() || '').slice(0, 400)];
      let body = {};
      if (m === 'OPTIONS') return route.fulfill({ status: 204, headers: cors(req), body: '' });
      if (url.includes('/upload/signed-url')) body = {
        upload_url: 'https://fake-gcs.invalid/put', object_name: 'videos/prove_clip.mp4',
        public_url: 'https://fake-gcs.invalid/videos/prove_clip.mp4', content_type: 'video/mp4' };
      else if (url.includes('/upload/finalize')) body = {
        message: 'Upload finalized and attempt created', url: 'https://fake-gcs.invalid/videos/prove_clip.mp4',
        attempt_id: FAKE_ATTEMPT, user_competition_id: '00000000-0000-4000-8000-0000000000c1', user_id: REPORTER };
      else if (url.includes('/lifting/analyze/')) body = { message: 'queued', attempt_id: FAKE_ATTEMPT };
      return route.fulfill({ status: 200, headers: cors(req), body: JSON.stringify(body) });
    }
    if (url.includes('/users/by-email/')) {
      out.stubbedGets.push(url);
      if (caseName === 'flow-findprofile')
        return route.fulfill({ status: 200, headers: cors(req), body: JSON.stringify({ id: REPORTER, name: liveMe.name, email: FAKE_EMAIL }) });
      return route.fulfill({ status: 404, headers: cors(req), body: JSON.stringify({ error: 'No user found with that email' }) });
    }
    if (url.includes(FAKE_ATTEMPT)) {
      out.stubbedGets.push(url);
      return route.fulfill({ status: 200, headers: cors(req), body: JSON.stringify({ attempt_id: FAKE_ATTEMPT, processing_status: 'processing' }) });
    }
    if (caseName === 'synthetic-table' && url.includes(`/competitions/${CLUB}/leaderboard`)) {
      out.stubbedGets.push(url);
      const lb = JSON.parse(JSON.stringify(live));
      const fakes = [1, 2, 3].map((i) => ({ ...JSON.parse(JSON.stringify(liveMe)),
        user_id: `00000000-0000-4000-8000-00000000000${i}`, name: `synthetic.${i}`, score: 1000 - i * 100, rank: i, attempt_id: `00000000-0000-4000-8000-0000000001${i}0` }));
      lb.rows = [...fakes, ...live.rows.map((r) => ({ ...r, rank: r.rank + 3 }))];
      return route.fulfill({ status: 200, headers: cors(req), body: JSON.stringify(lb) });
    }
    return route.continue();
  });
  const page = await ctx.newPage();
  await page.unrouteAll();
  page.on('console', (msg) => { if (msg.type() === 'error') out.console.push(`${msg.text()} @ ${msg.location()?.url || ''}`); });
  page.on('pageerror', (e) => out.pageerrors.push(String(e)));
  const has = async (sel) => page.locator(sel).count();
  const txt = async () => page.evaluate(() => document.body.innerText);
  const uid = async () => page.evaluate(() => { try { return localStorage.getItem('userId'); } catch { return 'THROW'; } });

  await page.goto(BOARD);
  await page.waitForTimeout(1500);
  await page.waitForSelector('[data-testid="consistency-hero"]', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(500);
  out.checks.innerWidth = await page.evaluate(() => window.innerWidth);
  out.checks.url = page.url();
  let t = await txt();
  out.checks.notLoggedYet = t.split('Not logged yet').length - 1;
  out.checks.youRow = await has('[data-testid="you-row"]');
  out.checks.youRowUnknown = await has('[data-testid="you-row-unknown"]');
  out.checks.enteredTrue = await has('[data-testid="you-row"][data-entered="true"]');
  out.checks.enteredFalse = await has('[data-testid="you-row"][data-entered="false"]');
  out.checks.oldBonus = t.split(OLD).length - 1;
  out.checks.newBonus = t.split(NEW).length - 1;
  out.checks.round1Bonus = t.split(OLD1).length - 1;
  out.checks.viewerBlock = await has('[data-testid="consistency-viewer"]');
  out.checks.ring = (await has('[data-testid="consistency-ring-count"]')) ? await page.locator('[data-testid="consistency-ring-count"]').first().innerText() : null;
  out.checks.receiptTotal = (await has('[data-testid="receipt-total"]')) ? await page.locator('[data-testid="receipt-total"]').first().innerText() : null;
  out.checks.storedUserId = await uid();
  if (out.checks.youRowUnknown) {
    out.checks.youRowUnknownText = await page.locator('[data-testid="you-row-unknown"]').first().innerText();
    out.checks.youRowUnknownHref = await page.locator('[data-testid="you-row-unknown"]').first().evaluate((el) => (el.closest('a') || el.querySelector('a') || el).getAttribute('href'));
  }
  if (out.checks.youRow) out.checks.youRowText = await page.locator('[data-testid="you-row"]').first().innerText();
  const bonusLines = t.split('\n').filter((l) => l.includes(NEW));
  out.checks.bonusLines = bonusLines;
  fs.writeFileSync(`${DIR}/prove-c1-${caseName}${tag}-${w}.txt`, t);
  await page.screenshot({ path: `${OUTDIR}/prove-c1-${caseName}${tag}-${w}.png`, fullPage: false });

  if (caseName === 'anon' || caseName === 'flow-findprofile' || caseName === 'flow-inline') {
    await page.locator('[data-testid="you-row-unknown"]').first().click();
    await page.waitForURL(/find-profile/, { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(800);
    out.checks.findProfileUrl = page.url();
    const ft = await txt();
    out.checks.findProfileLoaded = ft.includes('Who am I?');
    fs.writeFileSync(`${DIR}/prove-c1-${caseName}${tag}-${w}-findprofile.txt`, ft);
  }
  if (caseName === 'flow-findprofile' || caseName === 'flow-inline') {
    await page.locator('input[type="email"]').first().fill(FAKE_EMAIL);
    await page.locator('form button[type="submit"]').first().click();
    if (caseName === 'flow-findprofile') {
      await page.getByText('Back to the challenge').first().waitFor({ timeout: 10000 });
      out.checks.uidAfterLookup = await uid();
      await page.getByText('Back to the challenge').first().click();
    } else {
      await page.getByRole('link', { name: 'Upload something', exact: true }).waitFor({ timeout: 10000 });
      out.checks.uploadSomethingHref = await page.getByRole('link', { name: 'Upload something', exact: true }).getAttribute('href');
      await page.getByRole('link', { name: 'Upload something', exact: true }).click();
      await page.waitForURL(/upload=1/, { timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(1500);
      out.checks.formEmailInputs = await has('form input[type="email"]');
      await page.locator('form input[type="email"]').first().fill(FAKE_EMAIL);
      out.checks.boardUrlBeforeFill = page.url();
      out.checks.fileInputs = await has('#challenge-video-upload');
      await page.locator('#challenge-video-upload').setInputFiles({ name: 'prove_clip.mp4', mimeType: 'video/mp4', buffer: Buffer.alloc(4096, 1) });
      await page.waitForTimeout(300);
      await page.locator('form button[type="submit"]').first().click();
      await page.getByText('Upload Successful!').first().waitFor({ timeout: 15000 }).catch(() => {});
      out.checks.toast = await page.locator('li[role="status"], [data-state="open"][data-swipe-direction]').allInnerTexts().catch(() => []);
    }
    await page.waitForURL(new RegExp(`/challenges/${CLUB}`), { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(2000);
    t = await txt();
    out.after = {
      url: page.url(),
      storedUserId: await uid(),
      youRow: await has('[data-testid="you-row"]'),
      youRowUnknown: await has('[data-testid="you-row-unknown"]'),
      enteredTrue: await has('[data-testid="you-row"][data-entered="true"]'),
      notLoggedYet: t.split('Not logged yet').length - 1,
      viewerBlock: await has('[data-testid="consistency-viewer"]'),
      ring: (await has('[data-testid="consistency-ring-count"]')) ? await page.locator('[data-testid="consistency-ring-count"]').first().innerText() : null,
      receiptTotal: (await has('[data-testid="receipt-total"]')) ? await page.locator('[data-testid="receipt-total"]').first().innerText() : null,
      deviceLogsAs: t.includes('This device now logs as'),
    };
    fs.writeFileSync(`${DIR}/prove-c1-${caseName}${tag}-${w}-after.txt`, t);
    await page.screenshot({ path: `${OUTDIR}/prove-c1-${caseName}${tag}-${w}-after.png`, fullPage: false });
  }
  await b.close();
  return out;
}

const cases = only.length ? only : ['anon', 'reporter', 'random', 'flow-findprofile', 'flow-inline', 'synthetic-table'];
const results = [];
for (const c of cases) for (const [w, h] of widths) {
  try { results.push(await run(c, w, h)); } catch (e) { results.push({ case: c + tag, width: w, crashed: String(e), partial: e.partialOut }); }
}
fs.writeFileSync(`${OUTDIR}/prove-c1-results${tag}.json`, JSON.stringify(results, null, 2));
console.log(JSON.stringify(results.map((r) => ({ case: r.case, w: r.width, crashed: r.crashed, checks: r.checks, after: r.after, stubbed: r.stubbed?.length, stubbedGets: r.stubbedGets?.length, console: r.console?.length, pageerrors: r.pageerrors?.length })), null, 1));
