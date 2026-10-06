"""Real browser upgrade across two versioned service workers, using synthetic notes only."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
import json,shutil,tempfile,re,time
from playwright.sync_api import sync_playwright
from seal_site import seal
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results';OUT.mkdir(exist_ok=True)
checks=[]
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def end_headers(self):
  self.send_header('Cache-Control','no-store');super().end_headers()
def check(name,condition):
 if not condition:
  (OUT/'release51-failure.json').write_text(json.dumps({'failed':name,'completed':checks,'testData':'synthetic-only'},indent=2))
 assert condition,name
 checks.append(name)
with tempfile.TemporaryDirectory() as temp:
 target=Path(temp)/'Paper'
 def ignore(path,names):
  return [n for n in names if n=='library' or n=='translation' and Path(path).name=='vendor' or n.endswith('.zip')]
 shutil.copytree(ROOT/'dist/site',target,ignore=ignore)
 # Derive the exact release from the build, not a stale literal from version 5.1.
 declared=json.loads((target/'release.json').read_text())
 expected=declared['appVersion'];match=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)',expected)
 assert match, 'Release must declare a semantic application version'
 assert declared['application']['version']==expected, 'Release fields disagree'
 major,minor,patch=map(int,match.groups());next_version=f'{major}.{minor}.{patch+1}'
 # Seal the sparse fixture itself. Integrity is never disabled for an upgrade test.
 seal(target)
 sw=target/'sw.js';source=sw.read_text()
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=temp));Thread(target=server.serve_forever,daemon=True).start()
 base=f'http://127.0.0.1:{server.server_port}/Paper/'
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch();ctx=browser.new_context();a=ctx.new_page();errors=[];a.on('pageerror',lambda e:errors.append(str(e)))
   a.goto(base+'#/liang-2022');a.wait_for_selector('#release-badge');a.evaluate("Promise.race([navigator.serviceWorker.ready.then(()=>true),new Promise((_,reject)=>setTimeout(()=>reject(Error('SW installation timeout')),45000))])");a.wait_for_timeout(1200)
   check('visible semantic version matches built release',a.locator('#release-badge').inner_text().split()[0]=='v'+expected)
   a.locator('#note').fill('Synthetic device A note retained across upgrade.');a.locator('h1').first.click();a.evaluate('getSelection().removeAllRanges()')
   b=ctx.new_page();b.on('pageerror',lambda e:errors.append(str(e)));b.goto(base+'#/cheng-2025');b.wait_for_selector('#note');b.locator('#note').fill('Synthetic device B draft must never disappear.')
   old=json.loads((target/'release.json').read_text());before=old['version'];new='auto51testrelease'
   data=json.loads((target/'data.json').read_text());data['version']=new;data['application']['version']=next_version
   (target/'data.json').write_text(json.dumps(data,ensure_ascii=False));(target/'data.js').write_text('window.PAPER_DATA='+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+';')
   old['version']=new;old['appVersion']=next_version;old['application']['version']=next_version;(target/'release.json').write_text(json.dumps(old,ensure_ascii=False));seal(target)
   time.sleep(1.2);a.evaluate('PaperRelease.check(true)');a.wait_for_function('navigator.serviceWorker.getRegistration().then(r=>!!r.waiting)',timeout=30000)
   a.wait_for_timeout(13500);a.evaluate('PaperRelease.maybeApply()');a.wait_for_timeout(1500)
   check('other tab input blocks activation',a.evaluate('PAPER_DATA.version')==before and b.evaluate('PAPER_DATA.version')==before)
   check('other tab unsaved text unchanged',b.locator('#note').input_value()=='Synthetic device B draft must never disappear.')
   b.locator('h1').first.click();b.evaluate('getSelection().removeAllRanges()');a.wait_for_timeout(13500)
   a.evaluate('PaperRelease.maybeApply()');a.wait_for_function('(v)=>PAPER_DATA.version===v',arg=new,timeout=45000);b.wait_for_function('(v)=>PAPER_DATA.version===v',arg=new,timeout=45000)
   check('both pages update without manual activation',a.locator('#release-badge').inner_text().split()[0]=='v'+next_version and b.locator('#release-badge').inner_text().split()[0]=='v'+next_version)
   notes=a.evaluate("JSON.parse(localStorage.getItem('paper-lab-learning-v1')).notes")
   check('both notes survive automatic reload',notes.get('liang-2022')=='Synthetic device A note retained across upgrade.' and notes.get('cheng-2025')=='Synthetic device B draft must never disappear.')
   a.wait_for_timeout(13000)
   a.evaluate("window.__realSync=PaperSync.status;PaperSync.status=()=>({connected:true,busy:false})")
   check('live page-memory authorization defers reload',a.evaluate('PaperRelease.safeToReload().ready') is False)
   a.evaluate('PaperSync.status=window.__realSync')
   check('idle unlocked page is eligible',a.evaluate('PaperRelease.safeToReload().ready') is True)
   a.evaluate("(()=>{let r=document.createRange();r.selectNodeContents(document.querySelector('.articlehead h1'));getSelection().addRange(r)})()")
   check('selection prevents reload',a.evaluate('PaperRelease.safeToReload().ready') is False);a.evaluate('getSelection().removeAllRanges()')
   a.evaluate("Promise.race([navigator.serviceWorker.ready.then(()=>true),new Promise((_,reject)=>setTimeout(()=>reject(Error('SW installation timeout')),45000))])")
   ctx.set_offline(True);a.goto(base+'#/cheng-2025');a.wait_for_selector('#release-badge');check('new version refresh works offline',a.evaluate('PAPER_DATA.version')==new)
   check('offline note remains available','Synthetic device B' in a.locator('#note').input_value())
   ctx.set_offline(False)
   # A broken subsequent worker install must leave the installed release running.
   broken=sw.read_text()+'\nself.addEventListener(\'install\',e=>e.waitUntil(Promise.reject(Error(\'synthetic installation failure\'))));\n'
   sw.write_text(broken)
   a.evaluate("async()=>{window.__failedWorkerState='waiting';const r=await navigator.serviceWorker.getRegistration();r.addEventListener('updatefound',()=>{const w=r.installing;w.addEventListener('statechange',()=>{window.__failedWorkerState=w.state;});});}")
   a.evaluate('PaperRelease.check(true)');a.wait_for_function("window.__failedWorkerState==='redundant'",timeout=45000)
   ctx.set_offline(True);a.goto(base+'#/liang-2022');a.wait_for_selector('#note')
   check('failed new installation preserves working release',a.evaluate('PAPER_DATA.version')==new)
   check('failed installation leaves real offline reload and both saved notes intact',a.locator('#note').input_value()=='Synthetic device A note retained across upgrade.' and a.evaluate("JSON.parse(localStorage.getItem('paper-lab-learning-v1')).notes['cheng-2025']")=='Synthetic device B draft must never disappear.')
   ctx.set_offline(False)
   mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);m=mobile.new_page();m.goto(base);m.wait_for_selector('#release-badge');check('mobile version visible without overflow',m.locator('#release-badge').is_visible() and m.evaluate('document.documentElement.scrollWidth<=innerWidth+1'));m.screenshot(path=str(OUT/'release51-mobile.png'));mobile.close()
   check('no application JavaScript errors',not errors)
   browser.close()
 finally:server.shutdown()
report={'status':'passed','checks':checks,'testedVersion':expected,'syntheticNextVersion':next_version,'data':'synthetic-only','realServiceWorkerUpgrade':True,'externalInferenceAndOriginals':'covered by unchanged existing study/reader suites','realHardware':False,'newHostedAuthorization':'not deployed by this test'}
(OUT/'release51-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
