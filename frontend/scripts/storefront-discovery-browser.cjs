// Fixture-only discovery QA: no orders, payments, or production mutations.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');
const picture = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"><rect width="400" height="400" fill="#eef2f6"/><path d="M120 100h160v200H120z" fill="#275d60"/></svg>');
const products = Array.from({ length: 28 }, (_, i) => ({
  id: i + 1, name: `Discovery item ${i + 1}`, slug: `discovery-${i + 1}`,
  brand: 'Fabrything', image: [picture], initial_selling_price: 590 + i * 10,
  effective_shipping_fee: 60, review_count: 0, available_sizes: [],
  variants: [{ id: i + 1, size: '', effective_price: 590 + i * 10, stock_quantity: 20, in_stock: true }],
}));
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] });
  const artifacts = path.resolve(__dirname, '../../docs/screenshots');
  fs.mkdirSync(artifacts, { recursive: true });
  const results = [];
  try {
    for (const mobile of [false, true]) {
      console.log(`Checking ${mobile ? 'mobile reduced-motion' : 'desktop'} storefront`);
      const page = await browser.newPage({ viewport: mobile ? { width: 390, height: 844 } : { width: 1440, height: 1000 }, reducedMotion: mobile ? 'reduce' : 'no-preference' });
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.route('**/api/**', async route => {
        const pathname = new URL(route.request().url()).pathname;
        let data = [];
        if (pathname.includes('/store/homepage')) data = { new_arrivals: products.slice(0, 12), discover_products: products.slice(12), categories: [] };
        const match = pathname.match(/\/store\/products\/discovery-(\d+)\//);
        if (match) {
          const product = products[Number(match[1]) - 1];
          data = { ...product, related_products: products.filter(p => p.id !== product.id).slice(0, 8) };
        }
        await route.fulfill({ json: { data } });
      });
      await page.goto(process.env.STOREFRONT_URL || 'http://127.0.0.1:3191', { waitUntil: 'domcontentloaded', timeout: 120000 });
      const discover = page.getByRole('heading', { name: 'Discover More', exact: true });
      await discover.waitFor({ timeout: 120000 });
      await page.getByText('Discovery item 12', { exact: true }).waitFor();
      await discover.scrollIntoViewIfNeeded();
      const carousel = page.locator('.swiper').filter({ has: page.getByText('Discovery item 13', { exact: true }) });
      assert.equal(await carousel.locator('.swiper-slide').count(), 16);
      console.log('Homepage collection counts verified');
      assert.equal(await carousel.evaluate(el => el.swiper.params.speed), mobile ? 0 : 350);
      const before = await carousel.locator('.swiper-wrapper').evaluate(el => getComputedStyle(el).transform);
      await page.getByRole('button', { name: 'Next Discover More products' }).click();
      await page.waitForTimeout(500);
      const after = await carousel.locator('.swiper-wrapper').evaluate(el => getComputedStyle(el).transform);
      assert.notEqual(before, after, 'carousel next button must move products');
      console.log('Carousel navigation verified');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'homepage horizontal overflow');
      await page.screenshot({ path: path.join(artifacts, `storefront-discovery-${mobile ? 'mobile' : 'desktop'}.png`) });
      await page.getByText('Discovery item 15', { exact: true }).click();
      await page.getByRole('heading', { name: 'Discovery item 15', exact: true }).waitFor();
      await page.getByText('You May Also Like', { exact: true }).evaluate(el => window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - 180));
      await page.waitForTimeout(500);
      const suggestions = page.locator('.MuiGrid-container').filter({ has: page.getByText('Discovery item 1', { exact: true }) }).last();
      assert.equal(await suggestions.locator('img').count(), 8);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'detail horizontal overflow');
      await page.screenshot({ path: path.join(artifacts, `storefront-suggestions-${mobile ? 'mobile' : 'desktop'}.png`) });
      await page.getByText('Discovery item 1', { exact: true }).click();
      await page.getByRole('heading', { name: 'Discovery item 1', exact: true }).waitFor();
      assert.deepEqual(errors, []);
      results.push({ viewport: mobile ? 'mobile' : 'desktop', reducedMotion: mobile, popular: 12, discover: 16, suggestions: 8, pageErrors: errors });
      await page.close();
    }
    console.log(JSON.stringify({ result: 'PASS', results, artifacts }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
