// Public production smoke check; never submits cart, checkout or admin actions.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const path = require('path');
const fs = require('fs');
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] });
  const base = process.env.STOREFRONT_URL || 'https://www.fabrything.com';
  const artifacts = path.resolve(__dirname, '../../docs/screenshots');
  fs.mkdirSync(artifacts, { recursive: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    const response = await page.request.get(`${base}/api/store/homepage/`);
    assert.equal(response.status(), 200);
    const { data } = await response.json();
    assert.equal(data.new_arrivals.length, 12);
    assert.equal(data.discover_products.length, 16);
    await page.goto(base, { waitUntil: 'domcontentloaded', timeout: 60000 });
    const heading = page.getByRole('heading', { name: 'Discover More', exact: true });
    await heading.waitFor({ timeout: 60000 });
    await heading.scrollIntoViewIfNeeded();
    await page.getByRole('button', { name: 'Next Discover More products' }).click();
    await heading.evaluate(el => window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - 140));
    await page.waitForTimeout(700);
    await page.screenshot({ path: path.join(artifacts, 'production-discovery-desktop.png') });
    const product = data.discover_products[0];
    await page.goto(`${base}/product/${product.slug}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.getByRole('heading', { name: product.name, exact: true }).waitFor({ timeout: 60000 });
    const relatedHeading = page.getByRole('heading', { name: 'You May Also Like', exact: true });
    await relatedHeading.evaluate(el => window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - 180));
    assert.equal(await relatedHeading.locator('..').locator('.MuiCard-root').count(), 8);
    await page.setViewportSize({ width: 390, height: 844 });
    await relatedHeading.evaluate(el => window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - 140));
    await page.waitForTimeout(700);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'mobile overflow');
    await page.screenshot({ path: path.join(artifacts, 'production-suggestions-mobile.png') });
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ result: 'PASS', base, arrivals: 12, discover: 16, related: 8, product: product.slug, pageErrors: errors, artifacts }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
