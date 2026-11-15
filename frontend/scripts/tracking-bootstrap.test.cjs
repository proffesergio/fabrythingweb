const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../public/index.html'), 'utf8')
  .match(/<script id="fabrything-tracking">([\s\S]*?)<\/script>/)[1];

function run({ga='', mode='', container='GTM-WX92HL7Q', hostname='www.fabrything.com', denied=false} = {}) {
  const scripts=[];
  const document={getElementById:()=>null,createElement:()=>({}),head:{appendChild:s=>scripts.push(s)}};
  const window={location:{hostname},localStorage:{getItem:()=>denied?'denied':null}};
  const code=source.replace('%REACT_APP_GA4_MEASUREMENT_ID%',ga)
    .replace('%REACT_APP_GTM_ID%',container).replace('%REACT_APP_TRACKING_MODE%',mode);
  vm.runInNewContext(code,{window,document});
  return {scripts,window};
}
test('confirmed Analytics stream loads through its published Google tag; only the store Pixel initializes', () => {
  const {scripts,window}=run();
  assert.equal(scripts.length,2);
  assert.equal(scripts[0].src,'https://www.googletagmanager.com/gtm.js?id=G-T4T8KFW86C');
  assert.equal(scripts[1].src,'https://connect.facebook.net/en_US/fbevents.js');
  assert.deepEqual(Array.from(window.fbq.queue[0]),['init','442368228898246']);
  assert.equal(window.fbq.queue.length,1); // Router owns PageView, not the bootstrap too.
});
test('a configured Google tag is loaded once with automatic pageviews disabled', () => {
  const {scripts,window}=run({ga:'G-VALID123'});
  assert.equal(scripts.filter(s=>s.src.includes('googletagmanager')).length,1);
  assert.equal(scripts[0].src,'https://www.googletagmanager.com/gtm.js?id=G-VALID123');
  assert.deepEqual(Array.from(window.dataLayer[1]),['set','send_page_view',false]);
});
test('explicit container ownership does not also load direct Google or Meta scripts', () => {
  const {scripts,window}=run({ga:'G-VALID123',mode:'gtm'});
  assert.equal(scripts.length,1);
  assert.equal(scripts[0].src,'https://www.googletagmanager.com/gtm.js?id=GTM-WX92HL7Q');
  assert.equal(window.fbq,undefined);
});
test('previews, unknown hosts and saved opt-out send no tracking requests', () => {
  for (const options of [{hostname:'localhost'},{hostname:'fabrythingweb.vercel.app'},{hostname:'example.com'},{denied:true}]) {
    assert.equal(run({...options,ga:'G-VALID123'}).scripts.length,0);
  }
});
