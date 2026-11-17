// Read-only checks of public editorial pages and their React enhancement.
const {chromium} = require('C:/Users/bhnbi/AppData/Local/12ui/versions/0.2.134/node_modules/playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({headless: true, ...(process.env.NEWS_CHROME_PATH ? {executablePath: process.env.NEWS_CHROME_PATH} : {})});
  const origin = process.env.NEWS_URL || 'https://nobleseek.fabrything.com';
  const output = path.resolve(__dirname, '../.local-validation');
  const prefix = process.env.NEWS_FILE_PREFIX || 'news-live';
  const content = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../.superdesign/news-content.json'), 'utf8'));
  const findings = [];
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({width, height: 1000});
      await page.goto(origin + '/nobleseek', {waitUntil: 'domcontentloaded', timeout: 60000});
      await page.locator('#root h1').first().waitFor({timeout: 60000});
      await page.waitForFunction(() => !document.getElementById('store-document-fallback'), undefined, {timeout: 60000});
      if (process.env.NEWS_EXPECT_DENSE) {
        await page.waitForFunction(() => document.querySelectorAll('[data-news-topics] section').length >= 4, undefined, {timeout: 60000});
        assert.ok(await page.locator('[data-news-latest] h3').count() >= 6, 'six-column latest stories');
      }
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'horizontal overflow at ' + width);
      assert.equal(await page.locator('head script[src*="adsbygoogle.js?client="]').count(), 1);
      const headlineCount = await page.locator('#root h1, #root h2, #root h3').count();
      await page.screenshot({path: path.join(output, `${prefix}-${width}.png`), fullPage: width === 1440});
      findings.push({page: 'home', width, headlineCount, overflow: false});
    }
    const articleUrl = origin + '/nobleseek/' + encodeURIComponent(content[0].slug);
    await page.goto(articleUrl, {waitUntil: 'domcontentloaded', timeout: 60000});
    await page.locator('#root h1').waitFor({timeout: 60000});
    await page.waitForFunction(() => !document.getElementById('store-document-fallback'), undefined, {timeout: 60000});
    assert.equal(await page.locator('head link[rel="canonical"]').count(), 1);
    assert.equal(await page.locator('#root h1').count(), 1);
    assert.equal(await page.locator('head script[src*="adsbygoogle.js?client="]').count(), 1);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'article horizontal overflow');
    findings.push({page: 'article', width: 320, canonical: await page.locator('head link[rel="canonical"]').getAttribute('href')});
    if (!process.env.NEWS_SKIP_NO_JS) {
      const noJs = await browser.newContext({javaScriptEnabled: false});
      const plain = await noJs.newPage();
      await plain.goto(articleUrl, {waitUntil: 'domcontentloaded'});
      assert.equal(await plain.locator('h1').count(), 1);
      assert.ok((await plain.locator('article').innerText()).length > 200);
      findings.push({page: 'article', javaScript: false, readable: true});
      await noJs.close();
    }
    assert.deepEqual(errors, [], 'browser page exceptions');
    fs.writeFileSync(path.join(output, prefix + '-browser-check.json'), JSON.stringify(findings, null, 2));
    console.log(JSON.stringify(findings));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
