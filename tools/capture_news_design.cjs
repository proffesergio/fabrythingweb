const {chromium} = require('C:/Users/bhnbi/AppData/Local/12ui/versions/0.2.134/node_modules/playwright');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
    await page.goto(pathToFileURL(path.resolve(__dirname, '../.superdesign/news-modern.html')).href, {waitUntil: 'networkidle', timeout: 60000});
    await page.screenshot({path: path.resolve(__dirname, '../.local-validation/news-design-desktop.png'), fullPage: true});
    await page.setViewportSize({width: 390, height: 844});
    await page.screenshot({path: path.resolve(__dirname, '../.local-validation/news-design-mobile.png'), fullPage: true});
    console.log('Captured desktop and mobile design references.');
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode = 1;});
