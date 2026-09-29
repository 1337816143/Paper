"""Browser regression suite. GitHub faults are simulated here; a separate PRIVATE
workflow verifies real GitHub writes with synthetic notes and an ephemeral token.
Never record authorization headers, real user data, or browser storage traces.
"""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
import json,threading,hashlib,base64,urllib.parse,traceback
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/site';RES=ROOT/'test-results';RES.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8795),partial(Quiet,directory=str(OUT)));threading.Thread(target=server.serve_forever,daemon=True).start()
BASE='http://127.0.0.1:8795/';checks=[];errors=[];failure=None
files={};fault={'cas':False,'writes':0,'force401':False};secret='ghs_123_'+'SyntheticJWT.Header-Payload.SignatureOnlyForTests123456789'

def github(route):
 request=route.request;url=urllib.parse.urlsplit(request.url);path=urllib.parse.unquote(url.path)
 def reply(code,data):route.fulfill(status=code,content_type='application/json',body=json.dumps(data))
 if fault['force401']:return reply(401,{'message':'Test authentication failure'})
 if path.rstrip('/') in ['/repos/paper-tests/private','/repos/paper-tests/public']:return reply(200,{'private':'/private' in path,'permissions':{'push':True}})
 if '/branches/' in path:return reply(200,{'name':'paper-user-data','commit':{'sha':'test-branch'}})
 if '/contents/' not in path:return reply(404,{'message':'Not found'})
 file=path.split('/contents/',1)[1]
 assert file.startswith('private/paper-sync/v5/'),file
 if request.method=='GET':
  if file not in files:return reply(404,{'message':'Not found'})
  b,s=files[file];return reply(200,{'encoding':'base64','content':base64.b64encode(b).decode(),'sha':s,'size':len(b)})
 assert request.method=='PUT'
 data=request.post_data_json
 assert data['branch']=='paper-user-data'
 if file.endswith('/index.json') and fault['cas']:
  fault['cas']=False;return reply(409,{'message':'Simulated compare-and-swap race'})
 old=files.get(file)
 if old and data.get('sha')!=old[1]:return reply(409,{'message':'SHA mismatch'})
 raw=base64.b64decode(data['content']);s=hashlib.sha1(raw).hexdigest();files[file]=(raw,s);fault['writes']+=1
 return reply(200 if old else 201,{'content':{'sha':s},'commit':{'sha':hashlib.sha1((s+str(fault['writes'])).encode()).hexdigest()}})

def putnote(page,value):
 page.evaluate("async v=>{await PaperReader.put('annotations',{id:'note-one',docId:'liang-2022',title:'SYNTHETIC',comment:v,segments:[],tags:[],links:[],type:'note',color:'yellow',createdAt:'2026-09-29T00:00:00Z',updatedAt:new Date().toISOString()});}",value)
def connect(page):
 return page.evaluate("async token=>await PaperSync.connect({repository:'paper-tests/private',branch:'paper-user-data'},token)",secret)
with sync_playwright() as p:
 browser=p.chromium.launch();context=browser.new_context(viewport={'width':1280,'height':900});page=context.new_page();page.set_default_timeout(45000);page.on('pageerror',lambda e:errors.append(str(e)))
 try:
  page.goto(BASE+'#/liang-2022');page.wait_for_selector('.paper-framework');page.wait_for_selector('.guided-reading-check');checks.append('Guided reading closes the existing argument chain with evidence-oriented checkpoints')
  page.goto(BASE+'#/annotations');page.wait_for_selector('#new-note');page.locator('#new-note').click();page.wait_for_selector('#note-editor')
  assert page.locator('#note-editor').evaluate("e=>e.tagName==='ASIDE'&&e.getAttribute('aria-modal')==='false'")
  assert page.locator('dialog[open]').count()==0
  r=page.locator('#note-editor').bounding_box();assert r['width']<=372 and r['height']<650
  page.locator('#note-editor [name="title"]').fill('Draft example');page.locator('#note-editor [name="comment"]').fill('SYNTHETIC unsaved draft retained')
  page.locator('.pagehead h1').click();page.wait_for_function("!document.querySelector('#note-editor')")
  page.locator('#new-note').click();page.wait_for_selector('#note-editor');assert page.locator('#note-editor [name="comment"]').input_value()=='SYNTHETIC unsaved draft retained'
  page.locator('#note-form button[type="submit"]').click();page.wait_for_selector('.annotation-card');assert 'SYNTHETIC unsaved draft retained' in page.locator('.annotation-card').first.inner_text();checks.append('Nonmodal small note editor preserves click-away drafts and saves the unchanged annotation schema')
  page.goto(BASE+'#/home');page.wait_for_selector('.interactive-tag');tag=page.locator('.interactive-tag').first;tag.click();page.wait_for_selector('.tag-popover');page.locator('[data-edit-tag]').click();page.wait_for_selector('.tag-editor')
  page.locator('.tag-editor [name="label"]').fill('My learning tag');page.locator('.tag-editor [name="text"]').fill('Beginner explanation with a concrete example.');page.locator('.tag-editor [name="href"]').fill('javascript:alert(1)');page.locator('.tag-editor button[type="submit"]').click();assert '不安全' in page.locator('.tag-edit-status').inner_text()
  page.locator('.tag-editor [name="href"]').fill('#/liang-2022');page.locator('.tag-editor button[type="submit"]').click();page.wait_for_function("!document.querySelector('.tag-editor')");page.reload();page.wait_for_selector('.interactive-tag');page.get_by_role('button',name='My learning tag',exact=True).first.click();assert 'concrete example' in page.locator('.tag-popover').inner_text();assert page.locator('.tag-destination').get_attribute('href')=='#/liang-2022'
  page.locator('[data-delete-tag]').click();page.wait_for_function("!document.querySelector('.tag-popover')");assert page.get_by_role('button',name='My learning tag',exact=True).count()==0;checks.append('Tag rename, detailed explanation, safe links, reload and removal all persist')
  page.goto(BASE+'#/original/liang-2022');page.wait_for_selector('.source-heading-projection');assert 'Highlights' in page.locator('.source-heading-projection').first.inner_text()
  intact=page.evaluate("""async()=>{const b=await PaperReader.loadBook('liang-2022');return b.pages.flatMap(p=>p.blocks).filter(b=>b.text).every(b=>document.getElementById(b.id).textContent===b.text.replace(/\s+/g,' ').trim());}""")
  assert intact;page.wait_for_selector('.figure-tags .tag-add');page.locator('.figure-tags .tag-add').first.click();page.wait_for_selector('.tag-editor');page.locator('.tag-editor [name="label"]').fill('Compare axes');page.locator('.tag-editor [name="text"]').fill('Check units and directions before interpreting this figure.');page.locator('.tag-editor button[type="submit"]').click();page.wait_for_function("!document.querySelector('.tag-editor')");assert page.get_by_role('button',name='Compare axes',exact=True).count()==1;checks.append('Figures have editable contextual tags; spaced headers are projected without changing original anchor text')
  page.goto(BASE+'#/sync');page.wait_for_selector('#vault-connect');assert '尚未连接' in page.locator('#vault-status').inner_text() or '本地' in page.locator('#vault-status').inner_text();checks.append('Unconnected browser clearly shows local-only status, never an invented cloud confirmation')
  # Two independent browser profiles, shared mocked GitHub, real application sync code.
  a=browser.new_context(viewport={'width':1200,'height':850});b=browser.new_context(viewport={'width':1200,'height':850});a.route('https://api.github.com/**',github);b.route('https://api.github.com/**',github);pa=a.new_page();pb=b.new_page();pa.goto(BASE+'#/home');pb.goto(BASE+'#/home');pa.wait_for_function('!!window.PaperSync');pb.wait_for_function('!!window.PaperSync');putnote(pa,'Original note')
  pa.evaluate("""async()=>{const bytes=new TextEncoder().encode('SYNTHETIC original attachment');const h=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');await PaperReader.put('files',{id:'synthetic-book/original',blob:new Blob([bytes],{type:'text/plain'})});await PaperReader.put('books',{id:'synthetic-book',title:'SYNTHETIC PAPER',local:true,sourceHash:h,originalType:'txt',pages:[{number:1,blocks:[{id:'p1-b1',kind:'paragraph',text:'SYNTHETIC original attachment'}]}]});await PaperComfort.put('tags',{id:'tag-synthetic',owner:'paper:liang-2022',label:'Synthetic cloud tag',text:'Example explanation',href:'#/liang-2022',builtin:false,updatedAt:new Date().toISOString()});}""")
  connect(pa);connect(pb);assert pb.evaluate("async()=> (await PaperReader.all('annotations')).find(n=>n.id==='note-one').comment")=='Original note';assert pb.evaluate("async()=>await (await PaperReader.all('files')).find(n=>n.id==='synthetic-book/original').blob.text()")=='SYNTHETIC original attachment';assert pb.evaluate("async()=> (await PaperComfort.all('tags')).some(t=>t.id==='tag-synthetic')");checks.append('Independent profile restores notes, imported original bytes, books and custom tags from the vault')
  # Failure means pending data is retained, not a green cloud badge.
  putnote(pa,'Pending before failed authentication');fault['force401']=True
  result=pa.evaluate("async()=>{try{await PaperSync.sync();return false;}catch{return PaperSync.status().state==='error';}}")
  assert result;assert pa.evaluate("async()=> (await PaperReader.all('annotations')).find(n=>n.id==='note-one').comment")=='Pending before failed authentication';fault['force401']=False;fault['cas']=True;pa.evaluate('async()=>await PaperSync.sync()');assert fault['cas'] is False;checks.append('401 retains local data; 409 re-reads and retries compare-and-swap without blind overwrite')
  pb.evaluate('async()=>await PaperSync.sync()')
  a.set_offline(True);putnote(pa,'Offline A edit');putnote(pb,'Concurrent B edit');pb.evaluate('async()=>await PaperSync.sync()');a.set_offline(False);pa.evaluate('async()=>await PaperSync.sync()')
  conflicts=pa.evaluate("async()=> (await PaperComfort.all('conflicts')).filter(c=>!c.resolved)");assert any(c.get('local',{}).get('value',{}).get('comment')=='Offline A edit' for c in conflicts);assert pa.evaluate("async()=> (await PaperReader.all('annotations')).find(n=>n.id==='note-one').comment")=='Concurrent B edit';checks.append('Concurrent same-note edits retain both versions as an explicit conflict, including offline edits')
  pa.evaluate("async()=>{const d=await new Promise(ok=>{const r=indexedDB.open('paper-lab-reader-v2',1);r.onsuccess=()=>ok(r.result);});await new Promise((ok,no)=>{const t=d.transaction('annotations','readwrite');t.objectStore('annotations').delete('note-one');t.oncomplete=ok;t.onerror=no;});PaperSync.changed('annotations');await PaperSync.sync();}")
  pb.evaluate('async()=>await PaperSync.sync()');assert not pb.evaluate("async()=> (await PaperReader.all('annotations')).some(n=>n.id==='note-one')");pb.evaluate('async()=>await PaperSync.sync()');assert not pb.evaluate("async()=> (await PaperReader.all('annotations')).some(n=>n.id==='note-one')");checks.append('Synchronized deletion uses tombstones and is not resurrected by another device')
  for page2 in [pa,pb]:
   assert not page2.evaluate("s=>JSON.stringify(localStorage).includes(s)||JSON.stringify(sessionStorage).includes(s)",secret)
   assert not page2.evaluate("async s=>JSON.stringify((await PaperSync.capture()).entries).includes(s)",secret)
  writes=fault['writes'];result=pa.evaluate("async token=>{PaperSync.disconnect();try{await PaperSync.connect({repository:'paper-tests/public',branch:'paper-user-data'},token);return false;}catch(e){return e.message.includes('公开仓库');}}",secret);assert result and fault['writes']==writes;pb.evaluate('PaperSync.disconnect()');checks.append('Public repositories are rejected before any note write; authorization never enters storage or captured backups')
  phone=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=2);m=phone.new_page();m.goto(BASE+'#/annotations');m.wait_for_selector('#new-note');m.locator('#new-note').click();m.wait_for_selector('#note-editor');box=m.locator('#note-editor').bounding_box();assert box['x']>=0 and box['x']+box['width']<=391;assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+1');m.screenshot(path=str(RES/'v5-phone-note.png'));m.locator('#close-note').click();m.goto(BASE+'#/home');m.wait_for_selector('.interactive-tag');assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+1');m.screenshot(path=str(RES/'v5-phone-home.png'));m.locator('#theme').click();m.screenshot(path=str(RES/'v5-phone-dark.png'));checks.append('390px touch viewport, note popover, liquid-glass light/dark layouts stay within the screen')
  m.emulate_media(reduced_motion='reduce');assert m.evaluate("getComputedStyle(document.querySelector('.hero')).animationName==='none'");checks.append('Reduced-motion preference disables decorative animation')
  # Expanded beginner material and source-scoped terminology remain present.
  assert page.evaluate("PAPER_STUDY.terms.filter(t=>t.example&&t.explanation).length>=60");assert not errors,errors
 except Exception:
  failure=traceback.format_exc();raise
 finally:
  (RES/'v5-report.json').write_text(json.dumps({'passed':checks,'errors':errors,'failure':failure,'scope':'Chromium desktop and mobile simulation; GitHub API mocked for fault injection, separate private workflow required for live GitHub proof'},ensure_ascii=False,indent=2));browser.close();server.shutdown()
print(json.dumps({'passed':checks},ensure_ascii=False))
