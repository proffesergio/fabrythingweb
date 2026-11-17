// Local static preview of an isolated build with live read-only news API.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const build = path.resolve(__dirname, '../.local-validation/news-ui-build');
const types = {'.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.json': 'application/json', '.txt': 'text/plain'};

http.createServer(async (req, res) => {
  if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405); res.end(); return; }
  const url = new URL(req.url, 'http://127.0.0.1');
  if (url.pathname.startsWith('/api/')) {
    try {
      const upstream = await fetch('https://nobleseek.fabrything.com' + url.pathname + url.search, {signal: AbortSignal.timeout(30000)});
      res.writeHead(upstream.status, {'Content-Type': upstream.headers.get('Content-Type') || 'application/json'});
      res.end(Buffer.from(await upstream.arrayBuffer()));
    } catch (_) { res.writeHead(503); res.end('API unavailable'); }
    return;
  }
  let file = path.resolve(build, '.' + decodeURIComponent(url.pathname));
  if (!file.startsWith(build + path.sep)) file = path.join(build, 'index.html');
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(build, 'index.html');
  res.writeHead(200, {'Content-Type': types[path.extname(file)] || 'application/octet-stream'});
  res.end(req.method === 'HEAD' ? undefined : fs.readFileSync(file));
}).listen(5937, '127.0.0.1', () => console.log('News UI preview: http://127.0.0.1:5937/nobleseek'));
