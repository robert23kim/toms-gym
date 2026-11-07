import { createRequire } from 'module';
const require = createRequire('/Users/toka/code/toms_gym/frontend/package.json');
const { chromium } = require('playwright');
const b = await chromium.launch();
const p = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
await p.goto('https://my-frontend-quyiiugyoq-ue.a.run.app/challenges/32ca7bad-a970-4a09-acec-02b768793063');
await p.waitForTimeout(1500);
console.log(await p.title(), await p.evaluate(() => window.innerWidth));
await b.close();
