const fs = require('node:fs');
const path = require('node:path');

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
  return '<!doctype html><html lang="en"><head>' + head + extras + '</head><body style="margin:0">' + body + '</body></html>';
}

function createHandler({loadShell, fetchDocument}) {
  return async function handler(req, res) {
    if (!['GET', 'HEAD'].includes(req.method)) { res.statusCode = 405; res.end(); return; }
    const kind = String(req.query?.kind || 'home');
    const slug = String(req.query?.slug || '');
    if (!['home', 'shop', 'deals', 'product'].includes(kind) || (kind === 'product' && !/^[a-zA-Z0-9_-]{1,255}$/.test(slug))) {
      res.statusCode = 404; res.setHeader('X-Robots-Tag', 'noindex'); res.end('Not found'); return;
    }
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(req.query || {})) {
      if (!['kind', 'slug'].includes(key) && typeof value === 'string') params.set(key, value);
    }
    const target = '/api/store/documents/' + kind + '/' + (kind === 'product' ? encodeURIComponent(slug) + '/' : '') + (params.size ? '?' + params : '');
    try {
      const upstream = await fetchDocument(target);
      if (upstream.status === 404) { res.statusCode = 404; res.setHeader('X-Robots-Tag', 'noindex'); res.end('Product or page not found'); return; }
      if (!upstream.ok) throw new Error('Upstream unavailable');
      const html = composeDocument(loadShell(), await upstream.text());
      res.statusCode = 200;
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.setHeader('Cache-Control', 'public, max-age=0, s-maxage=60, stale-while-revalidate=30');
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
  loadShell: () => fs.readFileSync(path.join(process.cwd(), 'build', 'index.html'), 'utf8'),
  fetchDocument: (target) => fetch('https://fabrythingapi.vercel.app' + target, {signal: AbortSignal.timeout(15000), redirect: 'error'}),
});
module.exports = {composeDocument, createHandler, handler};
