#!/usr/bin/env python3
"""Actual built-page Chromium tests, synthetic records only. Run in supported CI.
No isolated fixture substitutes for the generated app, original-access page,
HTTP subdirectory, downloaded single HTML, or application history.
"""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from tempfile import TemporaryDirectory
from urllib.parse import unquote,urlsplit
import hashlib,json,re,shutil,sys
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]; SITE=ROOT/'dist/site'; OUT=ROOT/'test-results/dong'; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'scripts'))
from browser_idle import after_reading_idle,observe_activity
GUIDE='dong-si-boundary-walkthrough'; SI='https://ars.els-cdn.com/content/image/1-s2.0-S0308521X26000636-mmc1.docx'
checks=[];errors=[];downloads=[];report={};browser=page=context=None
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
 def translate_path(self,path):
  name=unquote(urlsplit(path).path)
  target=(SITE/name.removeprefix('/Paper/')).resolve() if name.startswith('/Paper/') else SITE/'__missing__'
  return str(target if target.is_relative_to(SITE.resolve()) else SITE/'__missing__')
 def end_headers(self):self.send_header('Cache-Control','no-store');super().end_headers()
server=ThreadingHTTPServer(('127.0.0.1',0),Quiet);Thread(target=server.serve_forever,daemon=True).start();BASE=f'http://127.0.0.1:{server.server_port}/Paper/'
def check(label,condition):
 assert condition,label
 checks.append(label);print('PASS',label,flush=True)
def go(id):
 page.goto(BASE+'#/'+id);page.wait_for_selector('#note');page.clock.run_for(250)
def state(p=None):return (p or page).evaluate('PaperDong.mount(document.getElementById("dong-boundary")).getState()')
def field(key,value,p=None): (p or page).locator(f'[data-dong-field="{key}"]').fill(str(value))
def action(name,p=None): (p or page).locator(f'[data-dong-action="{name}"]').click()
def expected_blocks(id):
 n={'dong-2026':9,'dong-2026-ledger':6}[id]
 d=next(d for d in json.loads((ROOT/'content'/f'{id}.json').read_text()) if d['id']==id)
 rules=json.loads((ROOT/'resources/research-presentation.json').read_text());parts=[]
 for section in d['sections'][:n]:
  text=section[2]
  if section[1]=='教学代码':parts.append(text);continue
  for before,after in sorted(rules.items(),key=lambda x:-len(x[0])):text=text.replace(before,after)
  parts.extend(re.sub(r'\[\[[a-z0-9-]+\|([^\]]+)\]\]',r'\1',text).split('\n\n'))
 return {'lesson-block-'+str(i):text for i,text in enumerate(parts)}
def download(p,selector,label,expected=None):
 with p.expect_download() as event:p.locator(selector).click()
 item=event.value;failure=item.failure();check(label+' completed in Chromium',failure is None)
 data=Path(item.path()).read_bytes()
 if expected is not None:check(label+' exact source bytes',data==expected)
 downloads.append({'label':label,'name':item.suggested_filename,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'scheme':urlsplit(item.url).scheme})
 return data
def check_result_download(p,label):
 result=json.loads(download(p,'[data-dong-download="result"]',label))
 current=state(p)['result'];check(label+' contains current parameters and all exact computed values',all(result[k]==v for k,v in current.items()) and 'synthetic' in result['label'])
def popup(id):
 trigger=page.locator(f'[data-context-note="{id}"]').first;trigger.focus();trigger.press('Enter');page.wait_for_selector('#paper-context-note[open]')
 box=page.locator('#paper-context-note');check(id+' opens source and complete derivation',box.locator(f'a[href="{SI}"]').count()==1 and box.locator(f'a[href^="#/{GUIDE}/s"]').count()==1)
 page.keyboard.press('Escape');check(id+' closes and returns keyboard focus',box.count()==0 and trigger.evaluate('(e)=>e===document.activeElement'))
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch();context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True,reduced_motion='reduce')
  page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.clock.install();observe_activity(page)
  notes={};oldblocks={}
  for id,indices in [('dong-2026',[4,5,6,8]),('dong-2026-ledger',[3,5])]:
   go(id);oldblocks[id]=expected_blocks(id)
   actual=page.locator('.prose [data-block]').evaluate_all('(xs)=>Object.fromEntries(xs.map(x=>[x.id,x.textContent]))')
   check(id+' original paragraph text and stable IDs preserved',all(actual[k]==v for k,v in oldblocks[id].items()))
   check(id+' appended correction adds no old-prose markup',page.locator('.prose .dong-source-update').count()==0)
   for i in indices:
    go(f'{id}/s{i}');check(f'{id}/s{i} deep anchor exposes historical source notice','不再表示当前' in page.locator(f'#s{i} .dong-source-update').inner_text())
   n=4 if id=='dong-2026' else 3;notice=page.locator(f'#s{n} .dong-source-update').inner_text();check(id+' old268 paragraph is explicitly corrected at its own anchor',all(t in notice for t in ['268配262','314分别配218、187、174','不能据此把268逐项相除']))
   note='SYNTHETIC preserved old note for '+id;notes[id]=note;page.locator('#note').fill(note);page.locator('#note').evaluate('(e)=>e.blur()');page.clock.run_for(300)
  go('dong-2026');first=next(iter(oldblocks['dong-2026']));quote=oldblocks['dong-2026'][first][:24]
  legacy={'id':'synthetic-pre5511-dong','docId':'lesson:dong-2026','type':'highlight','title':'SYNTHETIC pre-5.5.11 annotation','comment':'Synthetic only','tags':[],'links':[],'color':'yellow','quote':quote,'segments':[{'block':first,'start':0,'end':len(quote),'quote':quote,'prefix':'','suffix':oldblocks['dong-2026'][first][len(quote):len(quote)+40]}]}
  page.evaluate('(x)=>PaperReader.put("annotations",x)',legacy);page.reload();page.wait_for_selector('mark[data-annotation="synthetic-pre5511-dong"]')
  check('Old synthetic highlight remains anchored before new workflow',''.join(page.locator('mark[data-annotation="synthetic-pre5511-dong"]').all_text_contents())==quote)
  go(GUIDE+'/dong-boundary');panel=page.locator('.dong-boundary');check('Actual app mounts one live Dong panel with no annotation blocks',panel.count()==1 and panel.locator('.prose,[data-block],.term-word').count()==0)
  s=state();check('Default chain starts M100, total110, harvest52.5 with closure0',s['result']['upper']['managed_input']==100 and s['result']['upper']['total_input']==110 and s['result']['upper']['harvest']==52.5 and abs(s['result']['upper']['mass_balance_residual'])<1e-10)
  check('Default combined ledger counts3010−550=2460 and no residual',s['result']['ledger']['gross_receipts']==3010 and s['result']['ledger']['internal_receipts']==550 and s['result']['ledger']['external_receipts']==2460 and s['result']['ledger']['residual']==0)
  check('Default reset configuration has no Dong busy guard',not page.evaluate('PaperDong.isBusy()'))
  for boundary,gross,inside in [('crop',1960,100),('livestock',1050,0),('combined',3010,550)]:
   page.locator('[data-dong-field="boundary"]').select_option(boundary);r=state()['result']['ledger']
   check(boundary+' boundary recalculates receipt and internal cancellation',r['gross_receipts']==gross and r['internal_receipts']==inside and r['residual']==0 and f'{gross:.3f}' in panel.locator('.dong-ledger').inner_text())
  field('extra',123);check('Unassigned outside input is exposed as123 residual',state()['result']['ledger']['residual']==123 and '123.000' in panel.locator('.dong-ledger').inner_text())
  action('reset');action('target55');check('Target55 produces explicitly empty conditional interval',not state()['result']['interval']['nonempty'] and '交集为空' in panel.locator('.dong-status').inner_text())
  action('target50');check('Target50 produces nonempty conditional interval',state()['result']['interval']['nonempty'] and abs(state()['result']['interval']['managed_input_lower']-95.23809523809524)<1e-9)
  page.evaluate('window.__dongTargetNode=document.querySelector("[data-dong-field=target]")');field('target',55)
  check('Recalculation preserves real input node and focus',page.evaluate('window.__dongTargetNode===document.querySelector("[data-dong-field=target]") && document.activeElement===window.__dongTargetNode'))
  for key,value in [('limit',20),('share_fe_fix',.4),('agricultural_land_fraction',.8),('nh3_fraction_of_deposition',.4),('harvest_fraction',.8)]:
   before=state()['result'];field(key,value);after=state()['result'];check(key+' alters current numeric output',after!=before and not state()['invalid'])
  check('Current upper limit20 returns deposition20 under stated assumption',abs(state()['result']['upper']['deposition']-20)<1e-9)
  last=state()['result']
  for key,value in [('target',''),('agricultural_land_fraction',0),('limit',60)]:
   field(key,value);check(key+' invalid draft preserves last-valid result and blocks export',bool(state()['invalid']) and state()['result']==last and page.locator('[data-dong-download="result"]').is_disabled() and panel.locator('.dong-error').is_visible())
   field(key,last['target'] if key=='target' else last['parameters'][key] if key in last['parameters'] else last['limit'])
  action('reset');field('target',55);page.locator('.dong-full summary').click();field('target','')
  page.locator('.dong-boundary a[href="#/original/dong-2026"]').click();page.wait_for_selector('#source-access-v4');page.clock.run_for(300)
  check('Source access stays rights-aware without public Dong PDF',page.locator('#original-text').count()==0 and page.locator('#source-access-v4').is_visible())
  check('Leaving lesson removes panel and its update guard',page.locator('.dong-boundary').count()==0 and not page.evaluate('PaperDong.isBusy()'))
  page.go_back();page.wait_for_selector('.dong-boundary');page.clock.run_for(300)
  check('Back restores invalid draft, last valid55 and expanded derivation',page.locator('[data-dong-field="target"]').input_value()=='' and bool(state()['invalid']) and state()['result']['target']==55 and page.locator('.dong-full').evaluate('(e)=>e.open'))
  page.go_forward();page.wait_for_selector('#source-access-v4');page.go_back();page.wait_for_selector('.dong-boundary');page.clock.run_for(300)
  field('target',50);check('Repeated history and correction resume actual recomputation',state()['result']['interval']['nonempty'] and not state()['invalid'])
  safe=after_reading_idle(page);check('Expanded Dong derivation protects automatic update',not safe['ready'] and '董' in safe['reason'])
  check('Official SI link is publisher DOCX, not publicly copied source',panel.locator(f'a[href="{SI}"]').count()==1 and panel.locator(f'a[href="{SI}"]').get_attribute('rel')=='noopener noreferrer')
  check('Panel states unresolved0.7,398/436 and single-constraint limits',all(x in panel.inner_text() for x in ['0.7','398','436','未证明','NH3','NOx','固定私有渲染']))
  check_result_download(page,'HTTP current calculation');download(page,'[data-dong-download="code"]','HTTP Python',(ROOT/'examples/dong_boundary_lab.py').read_bytes())
  check('Active download object URLs hold update guard',page.evaluate('PaperDong.isBusy()'));page.clock.fast_forward(61000);action('reset');check('Reset and completed URLs release the guard',not page.evaluate('PaperDong.isBusy()'))
  for section,id in [('s1','dong-si-input-boundary'),('s2','dong-si-internal-flow'),('s3','dong-si-nh3-inverse')]:
   go(GUIDE+'/'+section);popup(id)
  for width in [390,320]:
   page.set_viewport_size({'width':width,'height':844});go(GUIDE+'/dong-boundary');page.locator('.dong-full summary').click()
   check(str(width)+'px whole page stays inside viewport',page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
   check(str(width)+'px tables and chart have real internal scroll',panel.locator('.dong-svg').evaluate('(e)=>e.scrollWidth>e.clientWidth') and panel.locator('.dong-table').first.evaluate('(e)=>e.scrollWidth>e.clientWidth'))
   check(str(width)+'px SVG has accessible title and full data alternative',panel.locator('svg title').count()==1 and panel.locator('svg desc').count()==1 and panel.locator('.dong-all tbody tr').count()==14)
   panel.screenshot(path=str(OUT/f'dong-{width}-light.png'));page.locator('#theme').click();panel.screenshot(path=str(OUT/f'dong-{width}-dark.png'))
   check(str(width)+'px dark mode applies to panel',panel.evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(21, 41, 54)');page.locator('#theme').click()
  page.set_viewport_size({'width':1440,'height':1000});go(GUIDE+'/dong-boundary');panel.screenshot(path=str(OUT/'dong-desktop.png'))
  for id in notes:
   go(id);check(id+' old note preserved after interactions and history',page.locator('#note').input_value()==notes[id])
  go('dong-2026');page.wait_for_selector('mark[data-annotation="synthetic-pre5511-dong"]');check('Legacy highlight survives the complete new workflow',''.join(page.locator('mark[data-annotation="synthetic-pre5511-dong"]').all_text_contents())==quote)
  backup=json.loads(download(page,'[data-action="export"]','Synthetic legacy notes export'));check('Actual notes export retains both old Dong notes',all(backup['data']['notes'][id]==value for id,value in notes.items()))
  go(GUIDE+'/dong-boundary');page.evaluate('navigator.serviceWorker.ready.then(()=>true)');page.wait_for_function('!!navigator.serviceWorker.controller',timeout=60000)
  context.set_offline(True);page.reload();page.wait_for_selector('.dong-boundary');action('target55');check('Installed offline core recalculates target55 and keeps source limits',not state()['result']['interval']['nonempty'] and panel.locator(f'a[href="{SI}"]').count()==1);context.set_offline(False)
  with TemporaryDirectory(prefix='paper-dong-single-') as directory:
   single=Path(directory)/'Paper-Lab-offline.html';shutil.copyfile(SITE/'downloads/Paper-Lab-offline.html',single)
   fc=browser.new_context(accept_downloads=True,viewport={'width':390,'height':844});fp=fc.new_page();net=[];fp.on('request',lambda r:net.append(r.url) if r.url.startswith(('http:','https:')) else None);fp.on('pageerror',lambda e:errors.append(str(e)))
   fp.goto(single.as_uri()+'#/'+GUIDE+'/dong-boundary');fp.wait_for_selector('.dong-boundary');action('target55',fp);check('Isolated downloaded file computes target55 with no adjacent assets',not state(fp)['result']['interval']['nonempty'] and list(Path(directory).iterdir())==[single])
   check_result_download(fp,'file current calculation');download(fp,'[data-dong-download="code"]','file Python',(ROOT/'examples/dong_boundary_lab.py').read_bytes())
   check('Isolated file sends zero HTTP requests',not net);check('Isolated file has no page overflow',fp.evaluate('document.documentElement.scrollWidth<=innerWidth+2'));fp.screenshot(path=str(OUT/'dong-file-mobile.png'));fc.close()
  check('No uncaught application errors in complete integration',not errors);report={'passed':True,'checks':checks,'downloads':downloads,'errors':errors,'scope':'Actual built HTTP subdirectory, original access, live math, legacy synthetic notes/highlight, native history, narrow/dark layout, installed core offline and isolated file. Existing full-site cache suite remains separate.'}
except Exception as e:
 report={'passed':False,'checks':checks,'downloads':downloads,'errors':errors,'error':str(e)}
 try:
  page.screenshot(path=str(OUT/'failure-last-state.png'));report['url']=page.url;report['activeElement']=page.evaluate('({tag:document.activeElement?.tagName,id:document.activeElement?.id})')
 except Exception:pass
 raise
finally:
 (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 if browser and browser.is_connected():browser.close()
 server.shutdown()
print(json.dumps({'passed':True,'checks':len(checks),'downloads':len(downloads)}))
