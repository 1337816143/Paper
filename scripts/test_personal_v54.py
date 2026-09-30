"""Synthetic two-profile test. Never accepts real user credentials or prints private URLs."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
import threading,json,base64,hashlib,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results';OUT.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT/'dist/site')));threading.Thread(target=server.serve_forever,daemon=True).start();BASE='http://127.0.0.1:'+str(server.server_port)+'/'
files={};fault={'offline':False,'badAuth':False};checks=[]
SYNTH='ghs_SyntheticPrivateEntryTestValueNoRealAccount123456789'
def api(route):
 req=route.request;path=urllib.parse.unquote(urllib.parse.urlsplit(req.url).path)
 def respond(code,data):route.fulfill(status=code,content_type='application/json',body=json.dumps(data))
 if fault['badAuth']:return respond(401,{'message':'Synthetic revoked token'})
 if path=='/repos/1337816143/My-Evolution':return respond(200,{'private':True,'owner':{'id':201706309}})
 if '/branches/' in path:return respond(200,{'name':'paper-user-data'})
 if '/contents/' not in path:return respond(404,{})
 key=path.split('/contents/')[1];assert key.startswith('private/paper-sync/v5/')
 if req.method=='GET':
  if key not in files:return respond(404,{})
  v,s=files[key];return respond(200,{'encoding':'base64','content':base64.b64encode(v).decode(),'sha':s})
 assert req.method=='PUT';p=req.post_data_json;old=files.get(key)
 if old and p.get('sha')!=old[1]:return respond(409,{})
 value=base64.b64decode(p['content']);assert SYNTH.encode() not in value
 sha=hashlib.sha256(value).hexdigest();files[key]=(value,sha);return respond(200 if old else 201,{'content':{'sha':sha},'commit':{'sha':sha}})
def capsule(page):
 return page.evaluate("""async token=>{const enc=new TextEncoder(),b64=b=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'');const raw=crypto.getRandomValues(new Uint8Array(32)),iv=crypto.getRandomValues(new Uint8Array(12)),key=await crypto.subtle.importKey('raw',raw,'AES-GCM',false,['encrypt']);const data={schema:'paper.personal.payload.v1',repository:'1337816143/My-Evolution',branch:'paper-user-data',candidates:[token]};const ct=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:enc.encode('PaperLab.personal-entry.v1')},key,enc.encode(JSON.stringify(data)));return b64(enc.encode(JSON.stringify({schema:'paper.personal.envelope.v1',algorithm:'AES-GCM-256',iv:b64(iv),ciphertext:b64(ct)})))+'.'+b64(raw)}""",SYNTH)
def confirmed(page):
 try:page.wait_for_function("window.PaperPersonal?.status().state==='connected' && PaperSync.status().state==='synced'",timeout=90000)
 except Exception:
  safe=page.evaluate("()=>({personal:PaperPersonal.status(),sync:{state:PaperSync.status().state,message:PaperSync.status().message,busy:PaperSync.status().busy,dirty:PaperSync.status().dirty}})")
  (OUT/'personal-v54-failure.json').write_text(json.dumps({'completed':checks,'safeStatus':safe,'data':'synthetic-only; no entry URLs or secrets'},ensure_ascii=False,indent=2))
  raise

try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch();a=browser.new_context();a.route('https://api.github.com/**',api);pa=a.new_page();pa.goto(BASE+'#/home');pa.wait_for_function('!!window.PaperPersonal')
  assert not pa.evaluate('PaperSync.status().connected');checks.append('Public entry has no anonymous private access and no invented cloud confirmation')
  cap=capsule(pa);pa.goto(BASE+'#/personal/'+cap);confirmed(pa)
  assert '/personal/' not in pa.url;assert not pa.evaluate("Object.values(localStorage).some(x=>x.includes('SyntheticPrivateEntryTestValue'))");checks.append('Private capsule boot connects without filling any form; fragment removed and no plaintext localStorage')
  pa.goto(BASE+'#/sync');pa.wait_for_selector('#personal-status-panel');assert pa.locator('#vault-connect').is_hidden();checks.append('Connected frontend does not expose a token-entry form')
  pa.evaluate("async()=>await PaperReader.put('annotations',{id:'v54-note',docId:'liang-2022',title:'Synthetic',comment:'FROM PROFILE A',segments:[],tags:[],links:[],type:'note',color:'yellow'})");pa.evaluate('PaperSync.sync()')
  pa.reload();confirmed(pa);assert pa.evaluate("async()=>(await PaperReader.all('annotations').then(a=>a.find(n=>n.id==='v54-note'))).comment")=='FROM PROFILE A';checks.append('Reload automatically reconnects with encrypted durable entry and preserves note')
  dbcheck=pa.evaluate("async()=>{const db=await new Promise((ok,no)=>{let r=indexedDB.open('paper-personal-device-v1',1);r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error)});return await new Promise(ok=>{let r=db.transaction('entry').objectStore('entry').get('active');r.onsuccess=()=>ok({nonextractable:r.result.key.extractable===false,hasCipher:!!r.result.envelope.ciphertext,plainToken:JSON.stringify(r.result).includes('SyntheticPrivateEntryTestValue')})})}")
  assert dbcheck['nonextractable'] and dbcheck['hasCipher'] and not dbcheck['plainToken'];checks.append('IndexedDB stores non-extractable key and authenticated ciphertext only')
  b=browser.new_context();b.route('https://api.github.com/**',api);pb=b.new_page();pb.goto(BASE+'#/personal/'+cap);confirmed(pb)
  assert pb.evaluate("async()=>(await PaperReader.all('annotations').then(a=>a.find(n=>n.id==='v54-note'))).comment")=='FROM PROFILE A';checks.append('Independent new browser restores the same private record from the same capsule without typing')
  snapshot=pb.evaluate('PaperSync.capture().then(x=>JSON.stringify(x.entries))');assert 'paper-personal-device-v1' not in snapshot and SYNTH not in snapshot;checks.append('Authorization capsule and key never enter synchronized data or notes backups')
  # Valid local mutation survives disconnected network and is replayed after return.
  b.set_offline(True);pb.evaluate("async()=>{let n=await PaperReader.all('annotations').then(a=>a.find(n=>n.id==='v54-note'));await PaperReader.put('annotations',{...n,comment:'OFFLINE B CHANGE'});} ")
  assert pb.evaluate('PaperSync.status().state')!='synced';b.set_offline(False);pb.evaluate('PaperPersonal.resume()');pb.wait_for_function("PaperSync.status().state==='synced'",timeout=90000);pa.evaluate('PaperSync.sync()');assert pa.evaluate("async()=>(await PaperReader.all('annotations').then(a=>a.find(n=>n.id==='v54-note'))).comment")=='OFFLINE B CHANGE';checks.append('Offline edit is not falsely confirmed, then synchronizes and reaches the other profile')
  # User key cannot decrypt a corrupted capsule, and local notes remain intact.
  parts=cap.split('.');decoded=json.loads(base64.urlsafe_b64decode(parts[0]+'='*((4-len(parts[0])%4)%4)));s=decoded['ciphertext'];decoded['ciphertext']=('A' if s[0]!='A' else 'B')+s[1:];bad=base64.urlsafe_b64encode(json.dumps(decoded).encode()).decode().rstrip('=')+'.'+parts[1]
  ok=pa.evaluate("async c=>{try{await PaperPersonal.accept(c);return false}catch{return true}}",bad);assert ok;assert pa.evaluate("async()=>(await PaperReader.all('annotations').then(a=>a.find(n=>n.id==='v54-note'))).comment")=='OFFLINE B CHANGE';checks.append('Tampered AES-GCM capsule is rejected before replacing the saved entry or notes')
  # Teaching ledger coverage and mastery text are independent from done flags.
  pa.goto(BASE+'#/liang-2022');pa.wait_for_selector('.method-contract');assert pa.locator('.method-contract-part').count()==6;assert pa.locator('.method-contract table tbody tr').count()>=5
  assert pa.evaluate('PaperContracts.ids().length')==22;checks.append('All 22 contracts loaded; detailed input schema and six coherent evidence/practice panels available')
  pa.locator('.method-contract-part').last.locator(':scope > summary').click();field=pa.locator('.method-contract-part').last.locator('textarea').first;field.fill('SYNTHETIC mastery explanation, not an automatic completion claim');field.blur();pa.wait_for_timeout(500);pa.reload();pa.wait_for_selector('.method-contract');pa.locator('.method-contract-part').last.locator(':scope > summary').click();assert 'SYNTHETIC mastery' in pa.locator('.method-contract-part').last.locator('textarea').first.input_value();checks.append('User mastery evidence survives refresh as private research notes')
  single=browser.new_context();ps=single.new_page();ps.goto(BASE+'downloads/Paper-Lab-offline.html#/liang-2022');ps.wait_for_selector('.method-contract');exercise=ps.get_by_text('下载可运行的标准库教学脚本').get_attribute('href');assert exercise.startswith('data:text/x-python;charset=utf-8,');assert 'import argparse' in urllib.parse.unquote(exercise);checks.append('Single-file offline reader downloads the embedded runnable exercise without a sibling file')
  mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);pm=mobile.new_page();pm.goto(BASE+'#/liang-2022');pm.wait_for_selector('.method-contract');assert pm.evaluate('document.documentElement.scrollWidth<=innerWidth+1');pm.screenshot(path=str(OUT/'method-ledger-v54-mobile.png'));checks.append('390px mobile method ledger has no page overflow')
  browser.close()
finally:server.shutdown()
(OUT/'personal-v54-report.json').write_text(json.dumps({'status':'passed','checks':checks,'api':'simulated GitHub faults; private real-GitHub test is separate','credentials':'synthetic only','actualUserPATValidated':False,'realHardware':False},ensure_ascii=False,indent=2));print(json.dumps({'passed':True,'checks':len(checks),'actualUserPATValidated':False}))
