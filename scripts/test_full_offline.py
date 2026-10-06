"""Chromium acceptance of the exact final deploy tree, with actual offline restart.
Run AFTER CI reports are copied and seal_site.py finalizes the deployment. No
files in dist/site are written by this test. All personal records are synthetic.
"""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from tempfile import TemporaryDirectory
from threading import Thread
import hashlib, json, socket, sys, zipfile
from playwright.sync_api import sync_playwright
from seal_site import check
ROOT=Path(__file__).resolve().parents[1];SITE=ROOT/'dist/site';OUT=ROOT/'test-results';OUT.mkdir(exist_ok=True)
AUDIT=check(SITE);MANIFEST=json.loads((SITE/'offline-manifest.json').read_text());checks=[];errors=[];success=False
class Handler(SimpleHTTPRequestHandler):
 interrupted='';corrupt='';portable=None
 def log_message(self,*a):pass
 def translate_path(self,path):
  from urllib.parse import unquote, urlsplit
  name=unquote(urlsplit(path).path)
  if name.startswith('/Paper/'):return str(SITE/name[len('/Paper/'):])
  if name.startswith('/Portable/') and self.portable:return str(self.portable/name[len('/Portable/'):])
  return str(SITE/'__not_found__')
 def do_GET(self):
  name=self.path.split('?')[0]
  if name==self.interrupted:
   data=Path(self.translate_path(name)).read_bytes();self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers()
   try:self.wfile.write(data[:min(100000,len(data)//2)]);self.wfile.flush();self.connection.shutdown(socket.SHUT_RDWR)
   except OSError:pass
   self.connection.close();return
  if name==self.corrupt:
   data=Path(self.translate_path(name)).read_bytes();self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(b'X'*len(data));return
  try:super().do_GET()
  except (BrokenPipeError,ConnectionResetError):pass
 def end_headers(self):self.send_header('Cache-Control','no-store');super().end_headers()
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);Thread(target=server.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{server.server_port}';base=origin+'/Paper/'
def passed(name):checks.append(name);print('PASS',name,flush=True)
def message(page,kind):
 return page.evaluate('''kind=>new Promise((resolve,reject)=>{const ch=new MessageChannel();const timer=setTimeout(()=>{ch.port1.close();reject(Error('worker operation timed out'));},600000);ch.port1.onmessage=e=>{if(e.data.type==='DONE'){clearTimeout(timer);ch.port1.close();resolve(e.data);}};navigator.serviceWorker.ready.then(r=>r.active.postMessage({type:kind},[ch.port2])).catch(e=>{clearTimeout(timer);reject(e);});})''',kind)
def wait_done(page):page.wait_for_function("!PaperOffline.isBusy() && !document.querySelector('#cache-site').disabled && !document.querySelector('#cache-status').textContent.startsWith('正在准备')",timeout=600000)
SENTINELS=[['paper-lab-reader-v2','annotations',{'id':'offline-qa-note','comment':'SYNTHETIC private annotation','bookId':'liang-2022'}],['paper-lab-reader-v2','files',{'id':'offline-qa-import','label':'SYNTHETIC imported file'}],['paper-translations-v3','translations',{'id':'offline-qa-translation','text':'SYNTHETIC reviewed translation'}],['paper-personal-device-v1','entry',{'id':'offline-qa-capability','testOnly':'SYNTHETIC noncredential sentinel'}]]
PUT='''async rows=>{for(const [name,store,value] of rows){const db=await new Promise((ok,no)=>{const r=indexedDB.open(name);r.onupgradeneeded=()=>r.result.createObjectStore(store,{keyPath:'id'});r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error);});await new Promise((ok,no)=>{const tx=db.transaction(store,'readwrite');tx.objectStore(store).put(value);tx.oncomplete=ok;tx.onerror=()=>no(tx.error);});db.close();}}'''
GET='''async rows=>{const values=[];for(const [name,store,value] of rows){const db=await new Promise((ok,no)=>{const r=indexedDB.open(name);r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error);});values.push(await new Promise((ok,no)=>{const r=db.transaction(store).objectStore(store).get(value.id);r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error);}));db.close();}return values;}'''
try:
 with TemporaryDirectory() as profile, sync_playwright() as pw:
  ctx=pw.chromium.launch_persistent_context(profile,accept_downloads=True,viewport={'width':1280,'height':900});page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base+'#/liang-2022');page.wait_for_selector('#note');page.locator('#note').fill('SYNTHETIC offline restart note');page.locator('h1').first.click();page.evaluate("Promise.race([navigator.serviceWorker.ready.then(()=>true),new Promise((_,reject)=>setTimeout(()=>reject(Error('SW install timeout')),90000))])");page.wait_for_function('!!navigator.serviceWorker.controller')
  page.evaluate(PUT,SENTINELS);page.evaluate("async()=>{const c=await caches.open('paper-lab:/Farm/:offline-sentinel');await c.put('/Farm/sentinel',new Response('SYNTHETIC Farm cache'));const d=await caches.open('mydotwork-sentinel');await d.put('/MyDotWork/sentinel',new Response('SYNTHETIC MyDotWork cache'));}")
  page.goto(base+'#/offline');page.wait_for_selector('#cache-site')
  # Actual browser CacheStorage quota failure, then recovery. No mocked Cache.put.
  cdp=ctx.new_cdp_session(page);cdp.send('Storage.overrideQuotaForOrigin',{'origin':origin,'quotaSize':1})
  page.locator('#cache-site').click();wait_done(page);assert '已完整缓存' not in page.locator('#cache-status').inner_text();assert page.locator('#cache-failures').is_visible();assert not page.locator('#cache-site').is_disabled()
  assert page.evaluate(GET,SENTINELS)==[r[2] for r in SENTINELS];passed('real browser quota failure is recoverable and preserves synthetic private stores')
  cdp.send('Storage.overrideQuotaForOrigin',{'origin':origin,'quotaSize':4*1024**3})
  zipped=next(r for r in MANIFEST['resources'] if r['url'].endswith('.zip'));Handler.interrupted='/Paper/'+zipped['url'][2:]
  page.locator('#cache-site').click();wait_done(page);assert '已完整缓存' not in page.locator('#cache-status').inner_text();assert zipped['url'] in page.locator('#cache-failures').inner_text();partial=message(page,'STATUS_FAST');assert partial['count']>20 and not partial['complete'];passed('truncated network response never counts complete; verified resources retained')
  Handler.interrupted='';page.locator('#cache-site').click();wait_done(page);assert '已完整缓存' in page.locator('#cache-status').inner_text();assert float(page.locator('#cache-progress').get_attribute('value'))>0;assert message(page,'STATUS')['complete'];passed('retry completes the exact final tree including every ZIP and CI report')
  # Same-size cache replacement is detected, cannot be served offline, and repaired.
  target=next(r for r in MANIFEST['resources'] if r['url'].endswith('.csv'))
  page.evaluate('''async r=>{const c=await caches.open('paper-lab:/Paper/:sha256-v3');await c.put(new URL('.paper-offline/sha256/'+r.sha256,location.href),new Response(new Uint8Array(r.bytes)));}''',target)
  assert not message(page,'STATUS')['complete'];assert not message(page,'STATUS_FAST')['previouslyVerified'];ctx.set_offline(True);assert page.evaluate('async p=>(await fetch(new URL(p,location.href))).status',target['url'])==503;ctx.set_offline(False);assert message(page,'CACHE_ALL')['complete'];passed('same-size cached corruption invalidates checkpoint and exact retry repairs it')
  page.screenshot(path=str(OUT/'full-offline-desktop.png'),full_page=True)
  ctx.close()
  # A new Chromium process uses the persisted profile with network disabled before navigation.
  ctx=pw.chromium.launch_persistent_context(profile,accept_downloads=True,viewport={'width':1280,'height':900});ctx.set_offline(True);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(base+'#/offline');page.wait_for_selector('#cache-site');assert message(page,'STATUS')['complete'];passed('fresh browser process reopens the complete site with network disabled')
  assert page.evaluate(GET,SENTINELS)==[r[2] for r in SENTINELS]
  assert page.evaluate("JSON.parse(localStorage.getItem('paper-lab-learning-v1')).notes['liang-2022']")=='SYNTHETIC offline restart note'
  assert page.evaluate("async()=>await(await(await caches.open('paper-lab:/Farm/:offline-sentinel')).match('/Farm/sentinel')).text()")=='SYNTHETIC Farm cache'
  assert page.evaluate("async()=>await(await(await caches.open('mydotwork-sentinel')).match('/MyDotWork/sentinel')).text()")=='SYNTHETIC MyDotWork cache';passed('notes, annotations, imported records, translations, capability sentinels and other site scopes survive')
  # All files, including normalized-control files, are compared against actual final-tree bytes.
  for r in AUDIT['files']:
   got=page.evaluate('''async name=>{const r=await fetch(new URL(name,location.href)),b=await r.arrayBuffer();return {status:r.status,bytes:b.byteLength,sha256:Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b)),x=>x.toString(16).padStart(2,'0')).join('')};}''',r['path'])
   assert got=={'status':200,'bytes':r['bytes'],'sha256':r['sha256']},(r['path'],got)
  passed(f"offline byte comparison matches every final deployed file ({len(AUDIT['files'])})")
  data=json.loads((SITE/'data.json').read_text())
  for d in data['documents']:
   page.goto(base+'#/'+d['id']);page.wait_for_function('(title)=>document.querySelector("#view h1")?.textContent===title',arg=d['title']);assert '没有找到这篇内容' not in page.locator('#view').inner_text()
  for route in ['home','library','methods','coverage','my-work','notes','search','lab','resources','annotations','discover','my-library','workbook','glossary','sync','offline']:
   page.goto(base+'#/'+route);page.wait_for_function('(route)=>location.hash==="#/"+route && !!document.querySelector("#view h1")',arg=route);page.wait_for_timeout(50);assert '没有找到这篇内容' not in page.locator('#view').inner_text()
  passed(f"all {len(data['documents'])} document routes and core navigation open offline, including never-visited pages")
  # Open never-visited full source, actual original figure, and exercise existing interactive model.
  page.goto(base+'#/original/liang-2023');page.wait_for_selector('#original-text');page.locator('.source-figure img').first.scroll_into_view_if_needed();page.wait_for_function("document.querySelector('.source-figure img').naturalWidth>0")
  page.goto(base+'#/farmdesign-2012-balance-walkthrough');page.wait_for_selector('[data-annual-field="lossFraction"]');page.locator('[data-annual-field="lossFraction"]').fill('0.1');assert page.locator('[data-annual-value="chainLoss"]').inner_text()=='84.00';passed('original figures and interactive farm calculation work offline')
  pdf=next(r for r in MANIFEST['resources'] if r['url'].endswith('.pdf'))
  got=page.evaluate("async p=>{const r=await fetch(new URL(p,location.href),{headers:{Range:'bytes=2-17'}});return {status:r.status,bytes:Array.from(new Uint8Array(await r.arrayBuffer())),range:r.headers.get('Content-Range')};}",pdf['url'])
  assert got['status']==206 and bytes(got['bytes'])==(SITE/pdf['url'][2:]).read_bytes()[2:18];passed('offline PDF byte-range response matches original bytes')
  page.goto(base+'downloads/index.html')
  for r in [r for r in MANIFEST['resources'] if r['url'].endswith('.zip')]:
   name=Path(r['url']).name
   with page.expect_download(timeout=60000) as info:page.locator('a[href="'+name+'"]').click()
   item=info.value;assert item.failure() is None;actual=Path(item.path()).read_bytes();assert len(actual)==r['bytes'] and hashlib.sha256(actual).hexdigest()==r['sha256'];item.delete()
  passed('every hosted ZIP downloads through real browser UI offline with exact SHA-256')
  page.goto(base+'#/offline');page.set_viewport_size({'width':390,'height':844});page.wait_for_selector('#cache-site');page.locator('#check-cache').click();wait_done(page);assert '已完整缓存' in page.locator('#cache-status').inner_text();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(OUT/'full-offline-mobile.png'),full_page=True);passed('390px offline controls remain readable and deep verification succeeds')
  assert not errors,errors;ctx.close()
  # The actual delivered archives must extract into a working independently sealed site.
  with TemporaryDirectory() as unpacked:
   Handler.portable=Path(unpacked)
   for archive in (SITE/'downloads').glob('*.zip'):
    with zipfile.ZipFile(archive) as z:z.extractall(unpacked)
   check(Handler.portable)
   browser=pw.chromium.launch();portable=browser.new_context(accept_downloads=True);p=portable.new_page();p.goto(origin+'/Portable/#/offline');p.wait_for_selector('#cache-site');assert message(p,'CACHE_ALL')['complete'];portable.set_offline(True);p.reload();p.wait_for_selector('#cache-site');assert message(p,'STATUS')['complete'];p.goto(origin+'/Portable/#/original/liang-2022');p.wait_for_selector('#original-text');assert p.locator('.source-page').count()==15;p.screenshot(path=str(OUT/'full-offline-portable.png'));browser.close();Handler.portable=None
   passed('all real ZIP volumes extract, verify, open, cache and read originals offline')
 check(SITE,OUT/'offline-deployment-exact-tree.json');success=True
finally:
 server.shutdown();(OUT/'full-offline-report.json').write_text(json.dumps({'status':'passed' if success else 'incomplete','checks':checks,'errors':errors,'testData':'synthetic only','scope':'Chromium persistent profile and mobile viewport; not physical mobile OS eviction testing','manifestSHA256':AUDIT['manifestSHA256']},ensure_ascii=False,indent=2))
