"""Check literal additions and stable legacy annotation indices without a browser."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,html,json,re,sys,tempfile,copy,subprocess
ROOT=Path(__file__).resolve().parents[1];SITE=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'dist/site';BASE=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None
sys.path.insert(0,str(ROOT/'scripts'));from research_leads import load_research_leads,static_lead_html
sha=lambda b:hashlib.sha256(b).hexdigest()
contract=json.loads((ROOT/'tests/research-leads-baseline.json').read_text());data=json.loads((SITE/'data.json').read_text());leads=data.get('researchLeads',{});ids=set(contract['legacy_document_ids'])
legacy=[d for d in data['documents'] if d['id'] in ids]
assert sha(json.dumps(legacy,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==contract['legacy_documents_sha256']
# Only these independently reviewed stale-navigation guards may differ from
# the pinned reader. Remove them exactly, then verify every original byte.
reader=(ROOT/'src/reader.js').read_bytes().decode('utf-8')
reader_guards=[("async function notes(target){const ns=await all('annotations');", "async function notes(target){const ticket=epoch,ns=await all('annotations');if(ticket!==epoch)return;"), ("async function paint(){const root=docid?$('#original-text'):$('#view .reader');", "async function paint(){const ticket=epoch,root=docid?$('#original-text'):$('#view .reader');"), ("const ns=(await all('annotations')).filter(n=>n.docId===id);", "const ns=(await all('annotations')).filter(n=>n.docId===id);if(ticket!==epoch||!root.isConnected||root!==(docid?$('#original-text'):$('#view .reader')))return;"), ('let b=document.getElementById(s.block),a=b?resolve(s,b):null;', 'let b=document.getElementById(s.block);if(b&&!root.contains(b))b=null;let a=b?resolve(s,b):null;')]
reader_guards.append(("async function shelf(){const locals=await all('books');","async function shelf(){const ticket=epoch,locals=await all('books');if(ticket!==epoch)return;"))
for before,after in reader_guards:
 assert reader.count(after)==1,'Expected exact reader navigation guard'
 reader=reader.replace(after,before,1)
assert sha(reader.encode())==contract['reader_sha256'],'Reader changed outside reviewed navigation guards'
assert sha((ROOT/'resources/catalog.json').read_bytes())==contract['legacy_catalog_sha256']
assert leads==load_research_leads(ROOT,{d['id'] for d in data['documents']})
class Fragment(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.paragraphs=[];self.current=None;self.ids=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);assert 'hidden' not in a;assert not any(k.lower().startswith('on') for k in a);assert tag not in {'img','script','iframe','object','embed'}
  assert 'prose' not in a.get('class','').split()
  if 'id'in a:self.ids.append(a['id'])
  if tag=='p':self.current=[a,''];self.paragraphs.append(self.current)
 def handle_data(self,text):
  if self.current:self.current[1]+=text
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
with tempfile.TemporaryDirectory() as tmp:
 rendered=Path(tmp)/'articles.json'
 subprocess.run(['node',str(ROOT/'tests/research_leads_render.cjs'),str(SITE),str(rendered)],check=True,capture_output=True,text=True)
 articles=json.loads(rendered.read_text());anchor_proof={};anchor_count=0
 for pid,old_html in articles['before'].items():
  if pid not in ids:continue
  before=AnnotationBlocks();before.feed(old_html);after=AnnotationBlocks();after.feed(articles['after'][pid]);assert before.blocks==after.blocks,(pid,'legacy annotation block changed')
  anchor_count+=len(before.blocks);anchor_proof[pid]={'legacy_blocks':len(before.blocks),'id_and_text_sha256':sha(json.dumps(before.blocks,ensure_ascii=False,separators=(',',':')).encode()),'unchanged':True}
 (ROOT/'test-results').mkdir(exist_ok=True);(ROOT/'test-results/research-leads-anchors.json').write_text(json.dumps(anchor_proof,ensure_ascii=False,indent=2))
counts=0
for pid,lead in leads.items():
 parser=Fragment();parser.feed(lead['html']);assert len(parser.ids)==len(set(parser.ids));expected=[]
 for version in ['full','brief']:
  raw=(ROOT/'resources/research-leads'/pid/(version+'.txt')).read_bytes();assert sha(raw)==lead['hashes'][version]
  paragraphs=re.split(r'\r?\n\s*\r?\n',raw.decode().rstrip('\r\n'));expected.extend(paragraphs)
 assert [p[1] for p in parser.paragraphs]==expected;counts+=len(expected)
 block=static_lead_html(lead,pid);text=(SITE/'read'/(pid+'.html')).read_text();assert text.count(block)==1
 for version in ['full','brief']:assert 'href="#research-lead-'+pid+'-'+version+'"' in block
 if BASE:
  previous=text.replace(block,'',1)
  if pid in data.get('methodTransfers',{}):
   from method_transfer import static_transfer_html,static_source_notice
   later=static_transfer_html(data['methodTransfers'][pid],pid)
   for record in json.loads((ROOT/'resources/catalog.json').read_text())['records']:
    for url in set(record.get('aliases',[])+[record.get('sourceURL',''),record.get('downloadURL','')]):
     if url:later=later.replace('href="'+html.escape(url,quote=True)+'"','href="../index.html#/original/'+record['id']+'"')
   assert previous.count(later)==1
   previous=previous.replace(later,'',1).replace(static_source_notice(ROOT,pid),'',1)
  assert previous==(BASE/'read'/(pid+'.html')).read_text(),pid
 assert text.index(block)<text.index('<section class="reader" id="s0"')
if BASE:
 for p in (BASE/'read').glob('*.html'):
  if p.stem=='index':
   current=(SITE/'read'/p.name).read_text()
   for d in data['documents']:
    if d['id'] not in ids:
     entry='<p><a href="'+d['id']+'.html">'+html.escape(d['title'])+'</a></p>'
     assert current.count(entry)==1;current=current.replace(entry,'',1)
   assert current==p.read_text(),'static index changed beyond appended release entry'
  elif p.stem not in leads:assert p.read_bytes()==(SITE/'read'/p.name).read_bytes(),p.name
# Optional mode and malformed/stale content fail closed; plain markup is escaped as text.
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);assert load_research_leads(root,{'example'})=={}
 folder=root/'resources/research-leads/example';folder.mkdir(parents=True)
 text='p<0.001；<img src=x onerror=alert(1)>\n\n第二段';raw=(text+'\n').encode()
 for version in ['full','brief']:(folder/(version+'.txt')).write_bytes(raw)
 m={'schema':'paper.research-leads.v1','papers':{'example':{v:{'sha256':sha(raw),'accepted':True} for v in ['full','brief']}}};manifest=folder.parent/'accepted.json';manifest.write_text(json.dumps(m))
 lead=load_research_leads(root,{'example'})['example']['html'];assert 'p&lt;0.001' in lead and '<img ' not in lead;Fragment().feed(lead)
 try:load_research_leads(root,{'other'});raise AssertionError('Unknown ID accepted')
 except ValueError:pass
 (folder/'brief.txt').write_text('changed')
 try:load_research_leads(root,{'example'});raise AssertionError('Changed accepted prose accepted')
 except ValueError:pass
print(json.dumps({'passed':True,'source_documents_unchanged':len(legacy),'legacy_annotation_blocks_individually_unchanged':anchor_count,'appended_papers':len(leads),'literal_paragraphs_checked':counts,'static_pages_strip_to_exact_baseline':BASE is not None,'legacy_annotation_selector_excludes_new_prose':True,'no_script_content_visible':True,'browser_tested':False}))
