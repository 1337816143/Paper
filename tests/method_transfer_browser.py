#!/usr/bin/env python3
"""Real-browser acceptance for the additive method notes. Synthetic user data only."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from urllib.parse import unquote,urlsplit
import hashlib,json,re,time
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];SITE=ROOT/'dist/site';OUT=ROOT/'test-results/method-transfer';OUT.mkdir(parents=True,exist_ok=True)
new_note_results=[]
RAW=json.loads((ROOT/'resources/method-transfer.json').read_text());PAPERS=dict(RAW['papers']);PAPERS.update(json.loads((ROOT/'resources/method-transfer-expanded.json').read_text())['papers']);assert len(PAPERS)==19;checks=[];errors=[];passed=False
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

def legacy_blocks(page):
 return page.locator('#view .reader .prose p, #view .reader .prose pre').evaluate_all('(nodes)=>nodes.map(p=>[p.id,p.textContent])')

def assert_method_annotation(page,pid,record,original):
 identity=record['id'];block_id=record['segments'][0]['block'];quote=record['quote']
 page.wait_for_function("""({identity,blockId,quote,original})=>{
   const block=document.getElementById(blockId);
   const marks=[...document.querySelectorAll('mark[data-annotation]')].filter(e=>e.dataset.annotation===identity);
   return block&&marks.length>0&&marks.every(e=>block.contains(e))&&marks.map(e=>e.textContent).join('')===quote&&block.textContent===original;
 }""",arg={'identity':identity,'blockId':block_id,'quote':quote,'original':original})
 stored=page.evaluate('async(id)=>(await PaperReader.all("annotations")).filter(r=>r.id===id)',identity)
 check(pid+' new method annotation and selection unchanged',stored==[record])
 return page.locator('#'+block_id+' mark[data-annotation="'+identity+'"]')

def exercise_new_method_notes(browser,base,label,offline=False):
 started=time.monotonic();paper_times={}
 context=browser.new_context(offline=offline,viewport={'width':390,'height':844},reduced_motion='reduce')
 page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));network=[]
 if offline:page.on('request',lambda req:network.append(req.url) if urlsplit(req.url).scheme in {'http','https'} else None)
 saved={};multi_mark=0;catalog={r['id']:r for r in json.loads((ROOT/'resources/catalog.json').read_text())['records']}
 for pid in PAPERS:
  paper_started=time.monotonic()
  page.goto(base+'#/'+pid);page.wait_for_selector('#method-transfer-'+pid+'[data-method-transfer-ready="v1"]');root=page.locator('[data-method-transfer="'+pid+'"]')
  check(label+'/'+pid+' new paragraphs stay outside old prose numbering',root.locator('.prose').count()==0)
  access='public-archive' if catalog[pid].get('bookPath') else 'source-status'
  check(label+'/'+pid+' exact source availability shown',root.locator('[data-method-source-status="'+access+'"]').count()==1)
  if offline:check(label+'/'+pid+' single HTML original-resource boundary is visible','单HTML不包含原件' in root.locator('.method-transfer-access').inner_text())
  if access=='source-status':check(label+'/'+pid+' does not claim public full text','未公开托管' in root.locator('.method-transfer-access').inner_text())
  previous=legacy_blocks(page)
  selected=page.evaluate("""(pid)=>{
    const root=document.querySelector('[data-method-transfer="'+pid+'"]');
    const nodes=[...root.querySelectorAll('details[id] p[data-block]')];
    const block=nodes.find(p=>p.querySelector('[data-study-term]'));
    if(!block)return null;
    for(let p=block.parentElement;p&&p!==root;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;
    return {id:block.id,text:block.textContent,utf16Length:block.textContent.length,hasTerm:!!block.querySelector('[data-study-term]')};
  }""",pid)
  check(label+'/'+pid+' own method paragraph has an existing glossary term',bool(selected) and selected['hasTerm'])
  paragraph=page.locator('#'+selected['id']);paragraph.scroll_into_view_if_needed()
  if selected['hasTerm']:
   term=paragraph.locator('[data-study-term]').first;term.click();page.locator('#study-term-popover').wait_for(state='visible')
   check(label+'/'+pid+' existing glossary explanation opens',bool(page.locator('#study-term-popover h3').inner_text()))
   page.locator('#study-term-popover .term-close').click();page.locator('#study-term-popover').wait_for(state='detached')
   term.focus();term.press('Enter');page.locator('#study-term-popover').wait_for(state='visible');term.press('Escape');page.locator('#study-term-popover').wait_for(state='detached')
   check(label+'/'+pid+' glossary close leaves exact paragraph and route',paragraph.text_content()==selected['text'] and page.url.endswith('#/'+pid))
  page.evaluate("""(id)=>{const block=document.getElementById(id);const range=document.createRange();range.selectNodeContents(block);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);document.dispatchEvent(new Event('selectionchange'));}""",selected['id'])
  page.locator('#selection-tools').wait_for(state='visible');page.locator('#selection-tools [data-quick="highlight"]').click()
  page.wait_for_function('async({pid,id,quote})=>(await PaperReader.all("annotations")).filter(r=>r.docId==="lesson:"+pid&&r.quote===quote&&r.segments?.[0]?.block===id).length===1',arg={'pid':pid,'id':selected['id'],'quote':selected['text']})
  record=page.evaluate('async({pid,id})=>(await PaperReader.all("annotations")).find(r=>r.docId==="lesson:"+pid&&r.segments?.[0]?.block===id)',{'pid':pid,'id':selected['id']})
  check(label+'/'+pid+' actual selection toolbar saves one stable method block',len(record['segments'])==1 and record['quote']==selected['text'] and record['segments'][0]['start']==0 and record['segments'][0]['end']==selected['utf16Length'])
  marks=assert_method_annotation(page,pid,record,selected['text'])
  if selected['hasTerm']:
   check(label+'/'+pid+' cross-term quote survives multiple marks',marks.count()>1);multi_mark+=1
  page.reload();page.wait_for_selector('#method-transfer-'+pid+'[data-method-transfer-ready="v1"]');assert_method_annotation(page,pid,record,selected['text'])
  check(label+'/'+pid+' note target is initially folded',page.locator('#'+selected['id']).evaluate('(e)=>!!e.closest("details:not([open])")'))
  page.goto(base+'#/annotations');page.locator('#note-'+record['id']).wait_for(state='visible');page.locator('#note-'+record['id']+' a[href="#/'+pid+'/'+selected['id']+'"]').click();page.wait_for_url(base+'#/'+pid+'/'+selected['id'])
  page.wait_for_function('(id)=>{const e=document.getElementById(id);return e&&!e.closest("details:not([open])")&&document.activeElement===e;}',arg=selected['id'])
  check(label+'/'+pid+' annotation deep link opens folded parents and focuses exact block',page.locator('#'+selected['id']).is_visible())
  assert_method_annotation(page,pid,record,selected['text']);check(label+'/'+pid+' runtime tools preserve old prose IDs and text',legacy_blocks(page)==previous)
  page.go_back();page.wait_for_url(base+'#/annotations');page.go_forward();page.wait_for_url(base+'#/'+pid+'/'+selected['id']);page.wait_for_function('(id)=>{const e=document.getElementById(id);return e&&!e.closest("details:not([open])");}',arg=selected['id']);assert_method_annotation(page,pid,record,selected['text'])
  saved[pid]={'record':record,'text':selected['text'],'legacy':previous};paper_times[pid]=round(time.monotonic()-paper_started,3)
 check(label+' every paper exercises cross-term selection',multi_mark==len(PAPERS))
 if not offline:
  page.goto(base+'#/liang-2022');page.wait_for_selector('#method-transfer-liang-2022[data-method-transfer-ready="v1"]');page.locator('#method-transfer-liang-2022 a[href="#/original/liang-2022"]').click();page.wait_for_selector('#original-text')
  check('public-archive method source link opens existing archived original',page.url.endswith('#/original/liang-2022'))
  page.goto(base+'#/farmdesign-2012');page.wait_for_selector('#method-transfer-farmdesign-2012[data-method-transfer-ready="v1"]');page.locator('#method-transfer-farmdesign-2012 a[href="#/original/farmdesign-2012"]').click();page.wait_for_selector('#source-access-v4')
  check('unhosted method source link opens status and legal-import panel',page.url.endswith('#/original/farmdesign-2012') and page.locator('#original-text').count()==0)
 page.goto(base+'#/annotations');page.locator('#export-annotations').wait_for(state='visible')
 with page.expect_download() as download:page.locator('#export-annotations').click()
 export=OUT/('synthetic-method-annotations-'+label+'.json');download.value.save_as(export);backup=json.loads(export.read_text());expected={v['record']['id']:v['record'] for v in saved.values()}
 check(label+' all nineteen method annotations exported exactly',backup['schema']=='paper.annotations.v2' and {r['id']:r for r in backup['annotations']}==expected)
 if offline:check(label+' new method tools require no network',not network)
 context.close()
 restored=browser.new_context(offline=offline,viewport={'width':390,'height':844},reduced_motion='reduce');page=restored.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(base+'#/annotations');page.locator('#import-annotations').wait_for(state='visible')
 with page.expect_file_chooser() as chooser:page.locator('#import-annotations').click()
 chooser.value.set_files(export);page.wait_for_function('async()=> (await PaperReader.all("annotations")).length===19')
 check(label+' imported annotations retain exact original records',{r['id']:r for r in page.evaluate('()=>PaperReader.all("annotations")')}==expected)
 for pid,snapshot in saved.items():
  record=snapshot['record'];block_id=record['segments'][0]['block'];page.goto(base+'#/'+pid+'/'+block_id);page.wait_for_function('(id)=>{const e=document.getElementById(id);return e&&!e.closest("details:not([open])");}',arg=block_id);assert_method_annotation(page,pid,record,snapshot['text'])
  check(label+'/'+pid+' imported note returns to unchanged legacy context',legacy_blocks(page)==snapshot['legacy'])
 restored.close();return {'papers':len(saved),'multiMarkCases':multi_mark,'nativeSelectionToolbarUsed':True,'exportImportExact':True,'offline':offline,'durationSeconds':round(time.monotonic()-started,3),'perPaperSeconds':paper_times}

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
  downloaded=OUT/'synthetic-notes.json';download.value.save_as(downloaded);backup=json.loads(downloaded.read_text());check('export retains all nineteen original notes',all(backup['data']['notes'][pid]==v[0] for pid,v in records.items()))
  old.close()
  new_note_results.append(exercise_new_method_notes(browser,BASE,'http'))
  nojs=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844});p=nojs.new_page()
  for pid in PAPERS:
   p.goto(BASE+'read/'+pid+'.html');block=assert_transfer(p,pid,True);check(pid+' static page has no mobile overflow',p.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
  nojs.close()
  offline=browser.new_context(offline=True,viewport={'width':390,'height':844});p=offline.new_page();external=[];p.on('request',lambda r:external.append(r.url) if urlsplit(r.url).scheme in {'http','https'} else None);p.on('pageerror',lambda e:errors.append(str(e)))
  single=(SITE/'downloads/Paper-Lab-offline.html').resolve().as_uri()
  for pid in PAPERS:
   p.goto(single+'#/'+pid);assert_transfer(p,pid,True)
  check('offline single HTML embeds all nineteen method additions',p.evaluate('Object.keys(PAPER_DATA.methodTransfers).length')==19);check('file-protocol text has no network dependency',not external);check('no browser script errors',not errors);offline.close();new_note_results.append(exercise_new_method_notes(browser,single,'file',offline=True));check('no errors after new method interaction tests',not errors);browser.close();passed=True
finally:
 server.shutdown();report={'passed':passed,'browser':'Chromium via Playwright','papers':len(PAPERS),'steps':sum(len(row['steps']) for row in PAPERS.values()),'checks':checks,'errors':errors,'sourceCommit':json.loads((SITE/'release.json').read_text())['sourceCommit'],'dataSHA256':hashlib.sha256((SITE/'data.json').read_bytes()).hexdigest(),'syntheticRecordsOnly':True,'newMethodInteractionResults':new_note_results};(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
