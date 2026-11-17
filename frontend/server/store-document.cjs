// Runs in the head, before the catalog body can paint or external assets wait.
// Every visitor receives the same document; no-JS browsers use the catalog.
function startStoreDocument() {
  var element = document.documentElement;
  var boot = window.__fabStoreBoot = {phase: 'loading'};
  element.setAttribute('data-store-boot', 'loading');
  try {
    if (window.localStorage.getItem('sf_dark') === 'true') element.setAttribute('data-store-boot-theme', 'dark');
  } catch (_) { /* The default theme works without browser storage. */ }
  function clean() {
    window.clearTimeout(timer);
    window.removeEventListener('error', onError, true);
  }
  boot.fail = function () {
    if (boot.phase !== 'loading') return;
    boot.phase = 'fallback';
    element.setAttribute('data-store-boot', 'fallback');
    clean();
  };
  boot.finish = function () {
    // Once visitors are using the fallback, do not replace it unexpectedly
    // when a slow script finally arrives. The reload link starts a new attempt.
    if (boot.phase === 'fallback') return false;
    boot.phase = 'ready';
    element.removeAttribute('data-store-boot');
    element.removeAttribute('data-store-boot-theme');
    clean();
    return true;
  };
  function onError(event) {
    var url = event.target && (event.target.src || event.target.href) || event.filename;
    if (!url) return;
    try {
      var asset = new URL(url, window.location.href);
      if (asset.origin === window.location.origin && /^\/static\/(js|css)\//.test(asset.pathname)) boot.fail();
    } catch (_) { /* An unrelated provider/image failure cannot hold the shop. */ }
  }
  window.addEventListener('error', onError, true);
  var timer = window.setTimeout(boot.fail, 15000);
}

const startupStyle = '<style id="store-document-startup-style">' +
  '#store-document-loader,#store-document-fallback-note{display:none}' +
  'html[data-store-boot=loading]{background:#f8fafc}' +
  'html[data-store-boot=loading] .store-document{display:none}' +
  'html[data-store-boot=loading] #store-document-loader{display:flex;min-height:100vh;min-height:100svh;align-items:center;justify-content:center;flex-direction:column;gap:24px;background:#f8fafc;color:#4f46e5;font:14px/1.5 system-ui,sans-serif}' +
  'html[data-store-boot-theme=dark][data-store-boot=loading],html[data-store-boot-theme=dark] #store-document-loader{background:#0f172a;color:#818cf8}' +
  '#store-document-loader .brand{width:170px;height:34px;object-fit:contain}' +
  '#store-document-loader .dark-brand{display:none}' +
  'html[data-store-boot-theme=dark] #store-document-loader .light-brand{display:none}' +
  'html[data-store-boot-theme=dark] #store-document-loader .dark-brand{display:block}' +
  '#store-document-loader svg{animation:store-document-spin 1s linear infinite}' +
  '@keyframes store-document-spin{to{transform:rotate(360deg)}}' +
  '@media(prefers-reduced-motion:reduce){#store-document-loader svg{animation:none}}' +
  'html[data-store-boot=fallback] #store-document-fallback-note{display:block;margin:0;padding:12px 24px;background:#eef2ff;color:#17182f;font:14px/1.5 system-ui,sans-serif}' +
  'html[data-store-boot=fallback] #store-app-status{display:none}' +
  '</style>';
const startupBody = '<div id="store-document-loader" role="status" aria-label="Loading Fabrything">' +
  '<img class="brand light-brand" src="/fabrything-horizontal-light.png" alt="Fabrything" width="170" height="34">' +
  '<img class="brand dark-brand" src="/fabrything-horizontal-dark.png" alt="" width="170" height="34">' +
  '<svg width="36" height="36" viewBox="0 0 36 36" aria-hidden="true"><circle cx="18" cy="18" r="15" fill="none" stroke="currentColor" stroke-width="3" stroke-dasharray="65 30"/></svg></div>' +
  '<p id="store-document-fallback-note" role="status">The interactive shop is taking longer to open. You can browse the catalog below or <a href="">reload the full shop</a>.</p>';

function composeDocument(shell, document) {
  const shellHead = shell.match(/<head[^>]*>([\s\S]*?)<\/head>/i)?.[1];
  const head = document.match(/<head[^>]*>([\s\S]*?)<\/head>/i)?.[1];
  const body = document.match(/<body[^>]*>([\s\S]*?)<\/body>/i)?.[1];
  if (!shellHead || !head || !body || !shell.includes('/static/js/')) throw new Error('Document shell unavailable');
  // Preserve this deployment's analytics, verification, fonts and hashed assets.
  // The public document owns title/description/canonical and initial schema.
  const extras = shellHead.replace(/<title[^>]*>[\s\S]*?<\/title>/gi, '')
    .replace(/<meta\b[^>]*(?:name=["'](?:description|robots|twitter:[^"']+)["']|property=["']og:[^"']+["'])[^>]*>/gi, '')
    .replace(/<link\b[^>]*rel=["']canonical["'][^>]*>/gi, '')
    .replace(/<script\b[^>]*type=["']application\/ld\+json["'][^>]*>[\s\S]*?<\/script>/gi, '');
  // News stays readable while its data-dependent React route loads. Both
  // readers and crawlers receive the article, never a bot-specific document.
  if (document.includes('data-news-document')) {
    return '<!doctype html><html lang="bn"><head>' + head + extras
      .replace(/<meta\b[^>]*name=["']google-adsense-account["'][^>]*>/gi, '') +
      '</head><body style="margin:0">' + body + '</body></html>';
  }
  return '<!doctype html><html lang="en"><head>' + head + startupStyle +
    '<script id="store-document-startup">(' + startStoreDocument.toString() + ')();</script>' +
    extras + '</head><body style="margin:0">' + startupBody + body + '</body></html>';
}

function createHandler({loadShell, fetchDocument}) {
  return async function handler(req, res) {
    if (!['GET', 'HEAD'].includes(req.method)) { res.statusCode = 405; res.end(); return; }
    const kind = String(req.query?.kind || 'home');
    const slug = String(req.query?.slug || '');
    const safeSlug = /^[\p{L}\p{M}\p{N}_-]{1,255}$/u.test(slug);
    if (!['home', 'shop', 'deals', 'product', 'news'].includes(kind) ||
        (kind === 'product' && !safeSlug) || (kind === 'news' && slug && !safeSlug)) {
      res.statusCode = 404; res.setHeader('X-Robots-Tag', 'noindex'); res.end('Not found'); return;
    }
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(req.query || {})) {
      if (!['kind', 'slug'].includes(key) && typeof value === 'string') params.set(key, value);
    }
    const target = (kind === 'news' ? '/api/store/nobleseek/document/' : '/api/store/documents/' + kind + '/') +
      ((kind === 'product' || kind === 'news') && slug ? encodeURIComponent(slug) + '/' : '') + (params.size ? '?' + params : '');
    try {
      const upstream = await fetchDocument(target);
      if (upstream.status === 404) { res.statusCode = 404; res.setHeader('X-Robots-Tag', 'noindex'); res.end('Product or page not found'); return; }
      if (!upstream.ok) throw new Error('Upstream unavailable');
      const html = composeDocument(loadShell(), await upstream.text());
      res.statusCode = 200;
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.setHeader('Cache-Control', kind === 'news'
        ? 'public, max-age=0, s-maxage=300, stale-while-revalidate=60'
        : 'public, max-age=0, s-maxage=60, stale-while-revalidate=30');
      res.setHeader('X-Content-Type-Options', 'nosniff');
      res.end(req.method === 'HEAD' ? undefined : html);
    } catch (_) {
      // A temporary API outage must not become an indexable empty soft-404.
      res.statusCode = 503; res.setHeader('Retry-After', '60'); res.setHeader('Cache-Control', 'no-store');
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      let fallback = 'Store temporarily unavailable. Please retry shortly.';
      try { fallback = loadShell(); } catch (_) { /* Keep a usable error if the build is absent. */ }
      res.end(req.method === 'HEAD' ? undefined : fallback);
    }
  };
}

const handler = createHandler({
  loadShell: () => require('./build-shell.cjs'),
  fetchDocument: (target) => fetch('https://fabrythingapi.vercel.app' + target, {signal: AbortSignal.timeout(15000), redirect: 'error'}),
});
module.exports = {composeDocument, createHandler, handler, startStoreDocument};
