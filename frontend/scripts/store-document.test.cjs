const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const vm = require('node:vm');
const {packageStoreShell} = require('./package-store-shell.cjs');
const {composeDocument, createHandler, startStoreDocument} = require('../server/store-document.cjs');
const shell = '<html><head><title>Fabrything</title><meta name="description" content="old"><meta name="google-site-verification" content="public-verification"><script>window.existingAnalytics=true;</script><script defer src="/static/js/main.abc.js"></script></head><body><div id="root"></div></body></html>';
const document = '<html><head><title>Cotton shirt</title><meta name="description" content="Cotton"><link rel="canonical" href="https://www.fabrything.com/product/shirt"></head><body><div id="root"><h1>Cotton shirt</h1></div></body></html>';
function response() { return {statusCode:0, headers:{},setHeader(k,v){this.headers[k]=v;},end(body){this.body=body;}}; }
test('crawlable HTML preserves deployed assets, analytics and verification without duplicate canonical/title', () => {
 const html=composeDocument(shell,document);
 assert.match(html, /<h1>Cotton shirt<\/h1>/);
 assert.match(html,/public-verification/);
 assert.match(html,/existingAnalytics/);
 assert.match(html,/main.abc.js/);
 assert.equal((html.match(/<title>/g)||[]).length,1);
 assert.equal((html.match(/rel="canonical"/g)||[]).length,1);
 assert.doesNotMatch(html,/content="old"/);
 assert.ok(html.indexOf('id="store-document-startup"') < html.indexOf('src="/static/js/'));
 assert.match(html,/role="status" aria-label="Loading Fabrything"/);
 assert.match(html,/html\[data-store-boot=loading\] \.store-document\{display:none\}/);
});

function bootPage({dark=false,storageBlocked=false}={}) {
 const attributes=new Map(),listeners=new Map();let timeout,cleared=false;
 const element={setAttribute:(k,v)=>attributes.set(k,v),removeAttribute:k=>attributes.delete(k)};
 const window={location:{origin:'https://www.fabrything.com',href:'https://www.fabrything.com/'},
  localStorage:{getItem(){if(storageBlocked)throw new Error('private mode');return dark?'true':null;}},
  addEventListener:(k,f)=>listeners.set(k,f),removeEventListener:k=>listeners.delete(k),
  setTimeout:f=>{timeout=f;return 1;},clearTimeout:()=>{cleared=true;}};
 vm.runInNewContext('('+startStoreDocument.toString()+')();',{window,document:{documentElement:element},URL});
 return {boot:window.__fabStoreBoot,attributes,listeners,timeout:()=>timeout(),isCleared:()=>cleared};
}
test('the pre-paint gate matches the saved theme and ends immediately when the route is ready', () => {
 const page=bootPage({dark:true});
 assert.equal(page.attributes.get('data-store-boot'),'loading');
 assert.equal(page.attributes.get('data-store-boot-theme'),'dark');
 assert.equal(page.boot.finish(),true);
 assert.equal(page.attributes.has('data-store-boot'),false);
 assert.equal(page.attributes.has('data-store-boot-theme'),false);
 assert.equal(page.isCleared(),true);
 assert.equal(page.listeners.size,0);
 page.timeout();assert.equal(page.boot.phase,'ready');
});
test('an asset failure restores the catalog; unrelated third-party and image failures do not', () => {
 const page=bootPage();const error=page.listeners.get('error');
 error({target:{src:'https://connect.facebook.net/en_US/fbevents.js'}});
 error({target:{src:'https://www.fabrything.com/product.jpg'}});
 assert.equal(page.boot.phase,'loading');
 error({target:{src:'https://www.fabrything.com/static/js/123.chunk.js'}});
 assert.equal(page.attributes.get('data-store-boot'),'fallback');
 assert.equal(page.boot.finish(),false);
 assert.equal(page.isCleared(),true);
});
test('a stalled bootstrap reveals a stable fallback even when browser storage is unavailable', () => {
 const page=bootPage({storageBlocked:true});
 page.timeout();
 assert.equal(page.boot.phase,'fallback');
 assert.equal(page.boot.finish(),false);
 assert.equal(page.attributes.get('data-store-boot'),'fallback');
});
test('upstream outage returns retryable 503 instead of indexable empty success', async () => {
 const handler=createHandler({loadShell:()=>shell,fetchDocument:async()=>{throw new Error('offline');}});
 const res=response();await handler({method:'GET',query:{kind:'product',slug:'shirt'}},res);
 assert.equal(res.statusCode,503);assert.equal(res.headers['Retry-After'],'60');assert.match(res.body,/main.abc.js/);
});
test('missing product remains HTTP404', async () => {
 const handler=createHandler({loadShell:()=>shell,fetchDocument:async()=>({status:404})});
 const res=response();await handler({method:'GET',query:{kind:'product',slug:'missing'}},res);
 assert.equal(res.statusCode,404);assert.equal(res.headers['X-Robots-Tag'],'noindex');
});

test('news preserves readable Bengali HTML and validates Unicode slugs and real 404s', async () => {
 const news = document.replace('<html>', '<html lang="bn">').replace('<h1>', '<h1 data-news-document>');
 const html = composeDocument(shell, news);
 assert.match(html, /<html lang="bn">/);
 assert.match(html, /data-news-document/);
 assert.match(html, /main.abc.js/);
 assert.doesNotMatch(html, /id="store-document-startup"/);
 let target;
 const handler = createHandler({loadShell:()=>shell,fetchDocument:async(p)=>{target=p;return {ok:true,text:async()=>news};}});
 const res = response();
 await handler({method:'GET',query:{kind:'news',slug:'বাংলা-সংবাদ'}},res);
 assert.equal(res.statusCode,200);
 assert.equal(target,'/api/store/nobleseek/document/' + encodeURIComponent('বাংলা-সংবাদ') + '/');
 const missing = createHandler({loadShell:()=>shell,fetchDocument:async()=>({status:404})});
 const missingRes=response();await missing({method:'GET',query:{kind:'news',slug:'missing'}},missingRes);
 assert.equal(missingRes.statusCode,404);
 assert.equal(missingRes.headers['X-Robots-Tag'],'noindex');
 const invalid=response();target=undefined;
 await handler({method:'GET',query:{kind:'news',slug:'../private'}},invalid);
 assert.equal(invalid.statusCode,404);assert.equal(target,undefined);
});

test('publisher verification is present on public documents and ads.txt is plain authorized inventory', () => {
 const publicShell=fs.readFileSync(path.join(__dirname,'../public/index.html'),'utf8');
 assert.match(publicShell, /<head>[\s\S]*<script async data-ns-adsense="1" src="https:\/\/pagead2.googlesyndication.com\/pagead\/js\/adsbygoogle.js\?client=ca-pub-1712742966437949" crossorigin="anonymous"><\/script>[\s\S]*<\/head>/);
 const html=composeDocument(publicShell.replace('%PUBLIC_URL%', '') + '<!-- /static/js/ -->',document);
 assert.equal((html.match(/pagead2\.googlesyndication\.com\/pagead\/js\/adsbygoogle\.js/g)||[]).length,1);
 assert.equal(fs.readFileSync(path.join(__dirname,'../public/ads.txt'),'utf8').trim(),'google.com, pub-1712742966437949, DIRECT, f08c47fec0942fa0');
 const config=require('../vercel.json');
 assert.equal(config.rewrites.find(rule=>rule.source==='/nobleseek/:slug').destination,'/api/store-document?kind=news&slug=:slug');
});
test('only fixed document types and safe slugs can be requested; queries retained', async () => {
 let target;const handler=createHandler({loadShell:()=>shell,fetchDocument:async(p)=>{target=p;return{ok:true,text:async()=>document};}});
 let res=response();await handler({method:'GET',query:{kind:'product',slug:'../../private'}},res);assert.equal(res.statusCode,404);assert.equal(target,undefined);
 res=response();await handler({method:'GET',query:{kind:'shop',page:'2',category:'fashion'}},res);assert.equal(res.statusCode,200);assert.match(target,/page=2/);assert.match(target,/category=fashion/);
});

test('deployment package has no root index shadow and shell loads from an unrelated runtime cwd', (t) => {
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'fab-shell-'));
 t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
 const build=path.join(directory,'build'),server=path.join(directory,'server');
 fs.mkdirSync(build);fs.writeFileSync(path.join(build,'index.html'),shell);
 packageStoreShell(build,server);
 assert.equal(fs.existsSync(path.join(build,'index.html')),false);
 assert.equal(fs.readFileSync(path.join(build,'app-shell.html'),'utf8'),shell);
 fs.copyFileSync(path.join(__dirname,'../server/store-document.cjs'),path.join(server,'store-document.cjs'));
 const script=`global.fetch=async()=>({ok:true,status:200,text:async()=>${JSON.stringify(document)}});const {handler}=require(${JSON.stringify(path.join(server,'store-document.cjs'))});const res={setHeader(){},end(body){if(this.statusCode!==200||!body.includes('main.abc.js')||!body.includes('<h1>Cotton shirt</h1>'))process.exitCode=1;}};handler({method:'GET',query:{kind:'home'}},res);`;
 execFileSync(process.execPath,['-e',script],{cwd:os.tmpdir(),windowsHide:true});
 const config=require('../vercel.json');
 assert.equal(config.rewrites.find(rule=>rule.source==='/').destination,'/api/store-document?kind=home');
 assert.equal(config.rewrites.at(-1).destination,'/app-shell.html');
});
