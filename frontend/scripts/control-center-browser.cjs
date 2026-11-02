// Local browser smoke check. Every API response is a fixture; no provider is contacted.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('fs');
const path = require('path');
(async () => {
 const browser = await chromium.launch({ executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome', headless:true, args:['--no-sandbox'] });
 try {
 const page = await browser.newPage({viewport:{width:1440,height:1100}});
 const errors=[], mutations=[]; let offline=false;
 page.on('pageerror',e=>errors.push(e.message));
 const job={id:1,mode:'ANALYTICS',interval_minutes:1440,batch_limit:12,is_paused:true,next_run_at:null};
 const insights={kpis:{total_orders:528,total_units:1378,total_revenue:362400},inventory_state:'available',
 sales_heatmap:Array.from({length:30},(_,i)=>({day:`2026-10-${String(i+1).padStart(2,'0')}`,orders:4+i,units:8+i,revenue:4000+i*200})),
 inventory_velocity:[{product_name:'Field Jacket',units:148,revenue:118400}],
 conversion_funnel:[{stage:'view_item',count:8420},{stage:'add_to_cart',count:1624},{stage:'begin_checkout',count:814},{stage:'purchase',count:528}],
 product_funnels:[{item_id:'p1',item_name:'Field Jacket',views:1290,adds_to_cart:236,checkouts:121,purchases:86}],
 search_gaps:[{query:'linen co-ord set',impressions:1860,clicks:42,ctr:0.0226}],
 providers:{merchant:{state:'unconfigured'},analytics:{state:'completed',last_run_at:new Date().toISOString(),result:{funnel:[]}},search_console:{state:'unconfigured'}}};
 await page.route('**/api/**', async route=>{
  const req=route.request(), url=new URL(req.url()); let data=[];
  if(offline && url.pathname.includes('admin/insights')) return route.fulfill({status:503,json:{message:'Temporarily unavailable'}});
  if(req.method()!=='GET') {
   mutations.push({path:url.pathname,body:req.postDataJSON()});
   if(url.pathname.endsWith('/resume/'))job.is_paused=false;
   if(url.pathname.endsWith('/pause/'))job.is_paused=true;
   if(req.method()==='PATCH')Object.assign(job,req.postDataJSON());
   data=job;
  } else if(url.pathname.includes('admin/insights'))data=insights;
  else if(url.pathname.includes('sync-jobs'))data=[job];
  await route.fulfill({json:{data,message:'OK'}});
 });
 await page.addInitScript(()=>{localStorage.setItem('token',`e30.${btoa(JSON.stringify({exp:4102444800,user_id:1,role:'Super Admin',name:'QA Admin'}))}.qa`);localStorage.setItem('sf_dark','true');});
 await page.goto(`${process.env.CONTROL_CENTER_URL || 'http://127.0.0.1:3191'}/admin/shop/control-center`, {waitUntil:'domcontentloaded',timeout:60000});
 await page.getByRole('heading',{name:'Shop Control Center'}).waitFor();
 await page.getByRole('button',{name:'Resume Analytics',exact:true}).click();
 await page.getByRole('button',{name:'Pause Analytics',exact:true}).waitFor();
 await page.getByRole('button',{name:'Run now',exact:true}).click();
 await page.waitForTimeout(800);
 await page.getByRole('combobox',{name:'Schedule Analytics'}).click();
 await page.getByRole('option',{name:'Hourly',exact:true}).click();
 await page.waitForTimeout(700);
 if(job.interval_minutes!==60)throw Error('Schedule not persisted');
 await page.getByRole('switch',{name:'Show demo data'}).check();
 await page.locator('.cc-demo-banner').waitFor();
 if(await page.getByRole('button',{name:'Run now',exact:true}).first().isEnabled())throw Error('Demo mutation enabled');
 const artifacts=path.resolve(__dirname,'../../docs/screenshots');
 fs.mkdirSync(artifacts,{recursive:true});
 await page.screenshot({path:path.join(artifacts,'control-center-desktop.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.waitForTimeout(500);
 const overflow=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
 if(overflow.scroll>overflow.width) {
  await page.screenshot({path:path.join(artifacts,'control-center-mobile-overflow.png'),fullPage:true});
  const offenders=await page.evaluate(()=>[...document.querySelectorAll('body *')].map(el=>({tag:el.tagName,cls:el.className,left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right})).filter(x=>x.right>innerWidth+1).slice(0,30));
  throw Error('Mobile document overflow '+JSON.stringify({overflow,offenders}));
 }
 await page.screenshot({path:path.join(artifacts,'control-center-mobile.png'),fullPage:true});
 await page.getByRole('switch',{name:'Show demo data'}).uncheck();
 await page.waitForTimeout(500); offline=true;
 await page.getByRole('button',{name:'Refresh',exact:true}).click();
 await page.getByText('The latest live snapshot could not be refreshed.',{exact:false}).waitFor();
 if(errors.length)throw Error(errors.join('\n'));
 console.log(JSON.stringify({result:'PASS',mutations,overflow,pageErrors:errors,artifacts}));
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1)});
