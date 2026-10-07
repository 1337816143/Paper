#!/usr/bin/env python3
"""Real-browser acceptance for the additive method notes. Synthetic user data only."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from urllib.parse import unquote,urlsplit
import hashlib,json,re
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];SITE=ROOT/'dist/site';OUT=ROOT/'test-results/method-transfer';OUT.mkdir(parents=True,exist_ok=True)
RAW=json.loads((ROOT/'resources/method-transfer.json').read_text());PAPERS=RAW['papers'];checks=[];errors=[];passed=False
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def translate_path(self,path):
  name=unquote(urlsplit(path).path);target=(SITE/name.removeprefix('/Paper/')).resolve()
  return str(target if name.startswith('/Paper/') and target.is_relative_to(SITE.resolve()) else SITE/'__missing__')
 def end_headers(self):self.send_header('Cache-Control','no-store');super().end_headers()
def check(label,value):
 assert value,label
 checks.append(label);print('PASS',label,flush=True)
def assert_transfer(page,pid,toggle=False):
 block=page.locator('[data-method-transfer="'+pid+'"]');block.wait_for(state='attached');check(pid+' has one addition',block.count()==1)
 check(pid+' retains both original introductions',page.locator('[data-research-lead="'+pid+'"] [data-lead-version]').count()==2)
 check(pid+' addition is between introductions and old section zero',page.evaluate('(pid)=>{const a=document.querySelector(`[data-research-lead="${pid}"]`),b=document.querySelector(`[data-method-transfer="${pid}"]`),c=document.getElementById("s0");return !!(a.compareDocumentPosition(b)&Node.DOCUMENT_POSITION_FOLLOWING)&&!!(b.compareDocumentPosition(c)&Node.DOCUMENT_POSITION_FOLLOWING)}',pid))
 for n,step in enumerate(PAPERS[pid]['steps'],1):
  detail=block.locator('#method-transfer-'+pid+'-'+step['id']);summary=detail.locator('summary')
  check(pid+'/'+step['id']+' retains every literal field',detail.locator('p').all_text_contents()==[f['label']+'：'+f['text'] for f in step['fields']])
  check(pid+'/'+step['id']+' title',summary.text_content()==str(n)+'. '+step['title'])
  if toggle:
   summary.click();check(pid+'/'+step['id']+' opens on click',detail.evaluate('(e)=>e.open'))
   summary.click();check(pid+'/'+step['id']+' closes on repeated click',not detail.evaluate('(e)=>e.open'))
   summary.focus();summary.press('Enter');check(pid+'/'+step['id']+' opens by keyboard',detail.evaluate('(e)=>e.open'))
   summary.press('Enter');check(pid+'/'+step['id']+' closes by keyboard',not detail.evaluate('(e)=>e.open'))
 return block
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);Thread(target=server.serve_forever,daemon=True).start();BASE=f'http://127.0.0.1:{server.server_port}/Paper/'
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch();context=browser.new_context(viewport={'width':1280,'height':900},reduced_motion='reduce');page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  for pid in PAPERS:
   page.goto(BASE+'#/'+pid);block=assert_transfer(page,pid,True)
   block.locator('details').evaluate_all('(xs)=>xs.forEach(e=>e.open=true)');page.set_viewport_size({'width':390,'height':844})
   check(pid+' mobile expanded fields do not overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
   if pid=='farmsteps-2026':block.screenshot(path=str(OUT/'farmsteps-mobile-expanded.png'))
   page.set_viewport_size({'width':1280,'height':900});page.evaluate('location.hash="#/'+pid+'/s0"');page.wait_for_url(BASE+'#/'+pid+'/s0')
   check(pid+' old s0 anchor exists',page.locator('#s0').count()==1)
  page.goto(BASE+'#/farmdesign-2012/s0');page.goto(BASE+'#/landscape-2018/s0');page.go_back();page.wait_for_url(BASE+'#/farmdesign-2012/s0');assert_transfer(page,'farmdesign-2012');page.go_forward();page.wait_for_url(BASE+'#/landscape-2018/s0');assert_transfer(page,'landscape-2018');check('Back and Forward retain old routes and additions',True)
  context.close()
  # Disable only the new overlay, create synthetic old notes/highlights, then
  # reload the same browser storage with the overlay restored.
  old=browser.new_context(viewport={'width':1280,'height':900});old.add_init_script('''let paperData;Object.defineProperty(window,'PAPER_DATA',{configurable:true,get(){return paperData;},set(v){if(sessionStorage.getItem('synthetic-transfer-phase')!=='new')delete v.methodTransfers;paperData=v;}});''');p=old.new_page();p.on('pageerror',lambda e:errors.append(str(e)));records={}
  for pid in PAPERS:
   p.goto(BASE+'#/'+pid);p.wait_for_selector('#lesson-block-0');check(pid+' pre-addition overlay is absent',p.locator('[data-method-transfer]').count()==0)
   note='SYNTHETIC old note for '+pid;p.locator('#note').fill(note);original=p.locator('#lesson-block-0').text_content();quote=original[:20];identity='synthetic-transfer-'+pid
   record={'id':identity,'docId':'lesson:'+pid,'type':'highlight','title':'SYNTHETIC legacy anchor','comment':'Synthetic only','tags':[],'links':[],'color':'yellow','quote':quote,'segments':[{'block':'lesson-block-0','start':0,'end':len(quote),'quote':quote,'prefix':'','suffix':original[len(quote):len(quote)+40]}]}
   p.evaluate('(record)=>PaperReader.put("annotations",record)',record);records[pid]=(note,original,quote,identity,record)
  p.evaluate('sessionStorage.setItem("synthetic-transfer-phase","new")');p.reload()
  for visit in ['after addition','after route re-entry']:
   p.goto(BASE+'#/home')
   for pid,(note,original,quote,identity,record) in records.items():
    p.goto(BASE+'#/'+pid);assert_transfer(p,pid)
    # Glossary spans can divide one selection into several DOM marks. Wait
    # for the complete ordered quote, never just its first fragment.
    p.wait_for_function("""({identity,quote,original})=>{
      const block=document.getElementById('lesson-block-0');
      const marks=[...document.querySelectorAll('mark[data-annotation]')].filter(e=>e.dataset.annotation===identity);
      return block&&marks.length>0&&marks.every(e=>block.contains(e))&&
        marks.map(e=>e.textContent).join('')===quote&&block.textContent===original;
    }""",arg={'identity':identity,'quote':quote,'original':original})
    mark=p.locator('#lesson-block-0 mark[data-annotation="'+identity+'"]')
    stored=p.evaluate('async(identity)=>(await PaperReader.all("annotations")).filter(r=>r.id===identity)',identity)
    check(pid+' '+visit+' retains the original annotation and selection',stored==[record])
    check(pid+' '+visit+' original note survives',p.locator('#note').input_value()==note)
    check(pid+' '+visit+' original highlight uses unchanged ordered quote and block', ''.join(mark.all_text_contents())==quote and p.locator('#lesson-block-0').text_content()==original)
  with p.expect_download() as download:p.locator('article button[data-action="export"]').click()
  downloaded=OUT/'synthetic-notes.json';download.value.save_as(downloaded);backup=json.loads(downloaded.read_text());check('export retains all four original notes',all(backup['data']['notes'][pid]==v[0] for pid,v in records.items()))
  old.close()
  nojs=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844});p=nojs.new_page()
  for pid in PAPERS:
   p.goto(BASE+'read/'+pid+'.html');block=assert_transfer(p,pid,True);check(pid+' static page has no mobile overflow',p.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
  nojs.close()
  offline=browser.new_context(offline=True,viewport={'width':390,'height':844});p=offline.new_page();external=[];p.on('request',lambda r:external.append(r.url) if urlsplit(r.url).scheme in {'http','https'} else None);p.on('pageerror',lambda e:errors.append(str(e)))
  single=(SITE/'downloads/Paper-Lab-offline.html').resolve().as_uri()
  for pid in PAPERS:
   p.goto(single+'#/'+pid);assert_transfer(p,pid,True)
  check('offline single HTML embeds all four method additions',p.evaluate('Object.keys(PAPER_DATA.methodTransfers).length')==4);check('file-protocol text has no network dependency',not external);check('no browser script errors',not errors);offline.close();browser.close();passed=True
finally:
 server.shutdown();report={'passed':passed,'browser':'Chromium via Playwright','papers':4,'steps':30,'checks':checks,'errors':errors,'sourceCommit':json.loads((SITE/'release.json').read_text())['sourceCommit'],'dataSHA256':hashlib.sha256((SITE/'data.json').read_bytes()).hexdigest(),'syntheticRecordsOnly':True};(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
