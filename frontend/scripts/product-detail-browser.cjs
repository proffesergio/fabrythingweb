// Fixture-only QA: no external supplier or production mutations.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const image = color => 'data:image/svg+xml,' + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600"><rect width="600" height="600" fill="#f4f5f6"/><path d="M180 140l70-40h100l70 40 65 100-75 40-20-40v260H210V240l-20 40-75-40z" fill="${color}"/></svg>`);
const product = {
  id: 1, slug: 'sports-titanium', name: 'Mens Sports Edition T-Shirt - Titanium', brand: 'Fabrilife',
  image: [image('#17433e'), image('#243c39')], initial_selling_price: 899, discount_price: 699, discount_percentage: 22,
  description: 'A lightweight sports T-shirt with a regular fit and comfortable crew neck.', highlights: ['Polyester fabric', 'Regular fit', 'Sublimation print'],
  specifications: { Material: 'Polyester', Fit: 'Regular fit' }, review_count: 0, available_sizes: ['M', 'L'],
  size_chart: { M: { chest: 39, length: 27.5 }, L: { chest: 40.5, length: 28 } },
  variants: [{ id: 1, size: 'M', effective_price: 699, stock_quantity: 2, in_stock: true }, { id: 2, size: 'L', effective_price: 699, stock_quantity: 5, in_stock: true }],
};
(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] });
  const artifacts = path.resolve(__dirname, '../../docs/screenshots');
  fs.mkdirSync(artifacts, { recursive: true });
  try {
    for (const width of [1440, 390]) {
      const page = await browser.newPage({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' });
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.route('**/api/**', route => {
        const url = new URL(route.request().url()).pathname;
        const data = url.includes('/store/products/sports-titanium/') ? product : url.includes('/store/config/') ? { fixed_shipping_rate: 70, outside_dhaka_shipping_rate: 120, currency: 'BDT' } : [];
        return route.fulfill({ json: { data } });
      });
      await page.goto('http://127.0.0.1:3191/product/sports-titanium', { waitUntil: 'domcontentloaded', timeout: 120000 });
      await page.getByRole('heading', { name: product.name, exact: true }).waitFor();
      await page.getByText('BDT 70', { exact: true }).waitFor();
      await page.getByText('BDT 120', { exact: true }).waitFor();
      const thumb = page.getByRole('button', { name: 'View product image 2' });
      await thumb.click();
      assert.equal(await thumb.getAttribute('aria-pressed'), 'true');
      await page.getByRole('button', { name: 'Increase quantity' }).click();
      assert.ok(await page.getByRole('button', { name: 'Increase quantity' }).isDisabled());
      await page.getByRole('button', { name: 'Size Chart', exact: true }).click();
      await page.getByRole('tab', { name: 'CM', exact: true }).click();
      await page.getByText('99.1 cm', { exact: true }).waitFor();
      await page.keyboard.press('Escape');
      await page.getByRole('button', { name: 'Add to Cart - ৳1,398', exact: true }).click();
      await page.getByText('Added to your cart.', { exact: false }).waitFor();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `horizontal overflow at ${width}`);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(200);
      await page.screenshot({ path: path.join(artifacts, `product-detail-${width}.png`), fullPage: true });
      await page.getByRole('link', { name: 'View cart', exact: true }).click();
      await page.getByRole('button', { name: /checkout/i }).first().waitFor();
      assert.ok(await page.getByText('৳70–৳120', { exact: true }).count());
      assert.deepEqual(errors, []);
      console.log(`PASS product gallery, size chart, stock limit, add to cart, regional cart rates, no overflow: ${width}px`);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
