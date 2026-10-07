#!/usr/bin/env python3
"""Literal method fields, old content/anchors and all three reading surfaces."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,html,json,re,sys,tempfile,copy,subprocess
ROOT=Path(__file__).resolve().parents[1]; SITE=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'dist/site'; BASE=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None
sys.path.insert(0,str(ROOT/'scripts'))
from method_transfer import load_method_transfers,static_transfer_html,static_source_notice
sha=lambda b:hashlib.sha256(b).hexdigest()
canonical=lambda obj:json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
contract=json.loads((ROOT/'tests/method-transfer-baseline.json').read_text());data=json.loads((SITE/'data.json').read_text());raw=json.loads((ROOT/'resources/method-transfer.json').read_text());all_transfers=data['methodTransfers'];transfers={pid:all_transfers[pid] for pid in raw['papers']};ids=set(contract['legacy_document_ids'])
assert len(ids)==127 and len(data['documents'])==130
assert [d['id'] for d in data['documents'] if d['id'] not in ids]==['method-transfer-20261007','method-transfer-expanded-20261007','ditzler-reading-20261007']
legacy=[d for d in data['documents'] if d['id'] in ids]
assert sha(canonical(legacy))==contract['legacy_documents_sha256'],'An old document changed'
assert sha(canonical({k:v for k,v in data['researchLeads'].items() if k!='ditzler-2019'}))==contract['legacy_research_leads_sha256'],'An accepted research introduction changed'
# Only these independently reviewed stale-navigation guards may differ from
# the pinned reader. Remove them exactly, then verify every original byte.
reader=(ROOT/'src/reader.js').read_bytes().decode('utf-8')
reader_guards=[("async function notes(target){const ns=await all('annotations');", "async function notes(target){const ticket=epoch,ns=await all('annotations');if(ticket!==epoch)return;"), ("async function paint(){const root=docid?$('#original-text'):$('#view .reader');", "async function paint(){const ticket=epoch,root=docid?$('#original-text'):$('#view .reader');"), ("const ns=(await all('annotations')).filter(n=>n.docId===id);", "const ns=(await all('annotations')).filter(n=>n.docId===id);if(ticket!==epoch||!root.isConnected||root!==(docid?$('#original-text'):$('#view .reader')))return;"), ('let b=document.getElementById(s.block),a=b?resolve(s,b):null;', 'let b=document.getElementById(s.block);if(b&&!root.contains(b))b=null;let a=b?resolve(s,b):null;')]
reader_guards.append(("async function shelf(){const locals=await all('books');","async function shelf(){const ticket=epoch,locals=await all('books');if(ticket!==epoch)return;"))
for before,after in reader_guards:
 assert reader.count(after)==1,'Expected exact reader navigation guard'
 reader=reader.replace(after,before,1)
assert sha(reader.encode())==contract['reader_sha256'],'Reader changed outside reviewed navigation guards'
assert sha((ROOT/'resources/catalog.json').read_bytes())==contract['catalog_sha256']
assert {pid:len(row['steps']) for pid,row in raw['papers'].items()}==contract['paper_step_counts']
assert transfers==load_method_transfers(ROOT,{d['id'] for d in data['documents']})
class Fragment(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.ids=[];self.paragraphs=[];self.current=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);assert tag not in {'img','script','iframe','object','embed'};assert not any(k.lower().startswith('on') for k in a);assert 'hidden' not in a;assert 'prose' not in a.get('class','').split()
  if 'id'in a:self.ids.append(a['id'])
  if tag=='p' and 'data-block' in a:self.current=[a['id'],''];self.paragraphs.append(self.current)
 def handle_data(self,text):
  if self.current is not None:self.current[1]+=text
 def handle_endtag(self,tag):
  if tag=='p':self.current=None
class AnnotationBlocks(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.stack=[];self.blocks=[];self.active=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);in_prose=any('prose' in x[1].get('class','').split() for x in self.stack)
  if tag in {'p','pre'} and in_prose:
   block=[a.get('id') or 'lesson-block-'+str(len(self.blocks)),''];self.blocks.append(block);self.active.append((len(self.stack),block))
  if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append((tag,a))
 def handle_data(self,text):
  for _,block in self.active:block[1]+=text
 def handle_endtag(self,tag):
  if tag in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:return
  if self.stack:self.stack.pop()
  self.active=[(depth,block) for depth,block in self.active if depth<len(self.stack)]
counts=0;anchor_count=0;anchor_proof={}
with tempfile.TemporaryDirectory() as tmp:
 rendered=Path(tmp)/'rendered.json';subprocess.run(['node',str(ROOT/'tests/method_transfer_render.cjs'),str(SITE),str(rendered)],check=True)
 articles=json.loads(rendered.read_text())
 for pid in ids:
  old=AnnotationBlocks();old.feed(articles['before'][pid]);new=AnnotationBlocks();new.feed(articles['after'][pid]);assert old.blocks==new.blocks,pid
  anchor_count+=len(old.blocks);anchor_proof[pid]={'blocks':len(old.blocks),'id_and_text_sha256':sha(canonical(old.blocks)),'unchanged':True}
 for pid,row in raw['papers'].items():
  fragment=Fragment();fragment.feed(transfers[pid]['html']);assert len(fragment.ids)==len(set(fragment.ids))
  expected=[row['intro'],*raw['scope'],row['chain']]
  for step in row['steps']:
   assert [f['label'] for f in step['fields']]==contract['reviewed_step_labels'][pid][step['id']]
   expected.extend(f['label']+'：'+f['text'] for f in step['fields']);counts+=len(step['fields'])
  expected.extend(n['text'] for n in row['notes'])
  assert [p[1] for p in fragment.paragraphs]==expected,pid
  static=static_transfer_html(transfers[pid],pid)
  for record in json.loads((ROOT/'resources/catalog.json').read_text())['records']:
   for url in set(record.get('aliases',[])+[record.get('sourceURL',''),record.get('downloadURL','')]):
    if url:static=static.replace('href="'+html.escape(url,quote=True)+'"','href="../index.html#/original/'+record['id']+'"')
  page=(SITE/'read'/f'{pid}.html').read_text();assert page.count(static)==1;assert page.index('data-research-lead')<page.index(static)<page.index('<section class="reader" id="s0"')
  if BASE:assert page.replace(static,'',1).replace(static_source_notice(ROOT,pid),'',1)==(BASE/'read'/f'{pid}.html').read_text(),pid
  ids_on_page=re.findall(r'\bid="([^"]+)"',articles['after'][pid]);assert len(ids_on_page)==len(set(ids_on_page)),pid
 if BASE:
  for p in (BASE/'read').glob('*.html'):
   if p.stem=='index':
    current=(SITE/'read/index.html').read_text()
    for doc in data['documents']:
     if doc['id'] not in ids:
      entry='<p><a href="'+doc['id']+'.html">'+html.escape(doc['title'])+'</a></p>';assert current.count(entry)==1;current=current.replace(entry,'',1)
    assert current==p.read_text()
   elif p.stem not in transfers:
    current=(SITE/'read'/p.name).read_text()
    if p.stem in all_transfers:
     later=static_transfer_html(all_transfers[p.stem],p.stem)
     for record in json.loads((ROOT/'resources/catalog.json').read_text())['records']:
      for url in set(record.get('aliases',[])+[record.get('sourceURL',''),record.get('downloadURL','')]):
       if url:later=later.replace('href="'+html.escape(url,quote=True)+'"','href="../index.html#/original/'+record['id']+'"')
     assert current.count(later)==1;current=current.replace(later,'',1).replace(static_source_notice(ROOT,p.stem),'',1)
    assert p.read_text()==current,p.name
assert counts==211
single=(SITE/'downloads/Paper-Lab-offline.html').read_text();single_data=re.search(r'window\.PAPER_DATA=(.*?);\n',single)[1];assert {pid:json.loads(single_data)['methodTransfers'][pid] for pid in raw['papers']}==transfers
assert len(data['researchLeads'])==20 and sum(len(x['hashes']) for x in data['researchLeads'].values())==40
# New content is escaped and unknown documents, duplicate identities and missing text fail closed.
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);assert load_method_transfers(root,ids)=={};(root/'resources').mkdir();f=root/'resources/method-transfer.json'
 unsafe=copy.deepcopy(raw);pid='farmdesign-2012';unsafe['papers'][pid]['intro']='<img src=x onerror=alert(1)> < 0';f.write_text(json.dumps(unsafe));fragment=load_method_transfers(root,ids)[pid]['html'];assert '&lt;img 'in fragment and '<img 'not in fragment;Fragment().feed(fragment)
 cases=[]
 v=copy.deepcopy(raw);v['schema']='other';cases.append(v)
 v=copy.deepcopy(raw);v['papers']['unknown']=v['papers'].pop(pid);cases.append(v)
 v=copy.deepcopy(raw);v['papers'][pid]['url']='javascript:alert(1)';cases.append(v)
 v=copy.deepcopy(raw);v['papers'][pid]['steps'][1]['id']=v['papers'][pid]['steps'][0]['id'];cases.append(v)
 v=copy.deepcopy(raw);v['papers'][pid]['steps'][0]['id']='bad"id';cases.append(v)
 v=copy.deepcopy(raw);v['papers'][pid]['intro']='';cases.append(v)
 for v in cases:
  f.write_text(json.dumps(v))
  try:load_method_transfers(root,ids)
  except ValueError:pass
  else:raise AssertionError('Malformed method-transfer data accepted')
OUT=ROOT/'test-results';OUT.mkdir(exist_ok=True)
(OUT/'method-transfer-anchors.json').write_text(json.dumps(anchor_proof,ensure_ascii=False,indent=2))
report={'passed':True,'legacy_documents_unchanged':len(legacy),'total_documents':len(data['documents']),'legacy_annotation_blocks_individually_unchanged':anchor_count,'existing_research_leads':38,'papers':len(transfers),'steps':sum(contract['paper_step_counts'].values()),'literal_step_fields':counts,'static_pages_strip_to_exact_baseline':BASE is not None,'single_file_data_identical':True,'all_additions_escaped':True,'malformed_cases_rejected':len(cases),'browser_tested':False}
(OUT/'method-transfer-static.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
