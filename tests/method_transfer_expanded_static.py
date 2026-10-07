#!/usr/bin/env python3
"""All nineteen method pages, exact legacy overlays and annotation preservation."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,html,json,re,sys,tempfile,subprocess,copy
ROOT=Path(__file__).resolve().parents[1];SITE=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'dist/site';BASE=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None
sys.path.insert(0,str(ROOT/'scripts'))
from method_transfer import load_method_transfers,static_transfer_html,static_source_notice
canonical=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();sha=lambda b:hashlib.sha256(b).hexdigest()
contract=json.loads((ROOT/'tests/method-transfer-expanded-baseline.json').read_text());data=json.loads((SITE/'data.json').read_text());extra=json.loads((ROOT/'resources/method-transfer-expanded.json').read_text());old_raw=json.loads((ROOT/'resources/method-transfer.json').read_text());ids=set(contract['legacy_document_ids']);transfers=data['methodTransfers']
assert len(ids)==128 and len(data['documents'])==129
assert [d['id'] for d in data['documents'] if d['id'] not in ids]==['method-transfer-expanded-20261007']
assert sha(canonical([d for d in data['documents'] if d['id'] in ids]))==contract['legacy_documents_sha256']
assert sha((ROOT/'resources/method-transfer.json').read_bytes())==contract['legacy_method_source_sha256']
assert sha(canonical({pid:transfers[pid] for pid in contract['legacy_method_ids']}))==contract['legacy_method_html_sha256']
assert sha(canonical(data['researchLeads']))==contract['legacy_research_leads_sha256']
for f,h in contract['protected_source_files'].items():assert sha((ROOT/f).read_bytes())==h,f
assert set(extra['papers'])==set(contract['new_method_step_counts']) and len(extra['papers'])==15
assert set(old_raw['papers']).isdisjoint(extra['papers'])
assert set(transfers)==set(data['researchLeads']) and len(transfers)==19
assert {pid:len(row['steps']) for pid,row in extra['papers'].items()}==contract['new_method_step_counts']
assert sha(canonical(extra['papers']))==contract['reviewed_new_papers_sha256']
assert load_method_transfers(ROOT,ids)=={pid:transfers[pid] for pid in old_raw['papers']}
assert load_method_transfers(ROOT,ids,'method-transfer-expanded.json')=={pid:transfers[pid] for pid in extra['papers']}
class Fragment(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.ids=[];self.paragraphs=[];self.current=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);assert tag not in {'img','script','iframe','object','embed'};assert not any(k.lower().startswith('on') for k in a);assert 'hidden' not in a;assert 'prose' not in a.get('class','').split()
  if 'id' in a:self.ids.append(a['id'])
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
def static(pid):
 value=static_transfer_html(transfers[pid],pid)
 for record in json.loads((ROOT/'resources/catalog.json').read_text())['records']:
  for url in set(record.get('aliases',[])+[record.get('sourceURL',''),record.get('downloadURL','')]):
   if url:value=value.replace('href="'+html.escape(url,quote=True)+'"','href="../index.html#/original/'+record['id']+'"')
 return value
fields=0;paragraphs=0;anchor_count=0;anchor_proof={}
with tempfile.TemporaryDirectory() as tmp:
 rendered=Path(tmp)/'rendered.json';subprocess.run(['node',str(ROOT/'tests/method_transfer_expanded_render.cjs'),str(SITE),str(rendered)],check=True);articles=json.loads(rendered.read_text())
 for pid in ids:
  old=AnnotationBlocks();old.feed(articles['before'][pid]);new=AnnotationBlocks();new.feed(articles['after'][pid]);assert old.blocks==new.blocks,pid;anchor_count+=len(old.blocks);anchor_proof[pid]={'blocks':len(old.blocks),'id_and_text_sha256':sha(canonical(old.blocks)),'unchanged':True}
 for pid,row in extra['papers'].items():
  parsed=Fragment();parsed.feed(transfers[pid]['html']);assert len(parsed.ids)==len(set(parsed.ids))
  expected=[row['intro'],*extra['scope'],row['chain']]
  for step in row['steps']:
   assert step['fields'];expected.extend(f['label']+'：'+f['text'] for f in step['fields']);fields+=len(step['fields'])
  expected.extend(n['text'] for n in row['notes']);paragraphs+=len(expected);assert [p[1] for p in parsed.paragraphs]==expected,pid
  block=static(pid);page=(SITE/'read'/f'{pid}.html').read_text();assert page.count(block)==1;assert page.index('data-research-lead')<page.index(block)<page.index('<section class="reader" id="s0"')
  ids_on_page=re.findall(r'\bid="([^"]+)"',articles['after'][pid]);assert len(ids_on_page)==len(set(ids_on_page)),pid
  notice=static_source_notice(ROOT,pid);assert page.count(notice)==1
  if BASE:assert page.replace(block,'',1).replace(notice,'',1)==(BASE/'read'/f'{pid}.html').read_text(),pid
 if BASE:
  for p in (BASE/'read').glob('*.html'):
   if p.stem=='index':
    current=(SITE/'read/index.html').read_text();doc=next(d for d in data['documents'] if d['id']=='method-transfer-expanded-20261007');entry='<p><a href="'+doc['id']+'.html">'+html.escape(doc['title'])+'</a></p>';assert current.count(entry)==1;assert current.replace(entry,'',1)==p.read_text()
   elif p.stem not in extra['papers']:
    current=(SITE/'read'/p.name).read_text()
    if p.stem in transfers:
     notice=static_source_notice(ROOT,p.stem);assert current.count(notice)==1;current=current.replace(notice,'',1)
    assert p.read_text()==current,p.name
assert (SITE/'method-transfer-ui.js').read_bytes()==(ROOT/'src/method-transfer-ui.js').read_bytes()
single=(SITE/'downloads/Paper-Lab-offline.html').read_text();embedded=json.loads(re.search(r'window\.PAPER_DATA=(.*?);\n',single)[1]);assert embedded['methodTransfers']==transfers
assert (ROOT/'src/method-transfer-ui.js').read_text().replace('</script','<\\/script') in single
source_kinds={'public-archive':0,'source-status':0}
for pid in transfers:
 notice=static_source_notice(ROOT,pid);page=(SITE/'read'/f'{pid}.html').read_text();assert page.count(notice)==1
 kind='public-archive' if 'data-method-source-status="public-archive"' in notice else 'source-status';source_kinds[kind]+=1
assert source_kinds=={'public-archive':12,'source-status':7}
assert len(data['researchLeads'])==19 and sum(len(row['hashes']) for row in data['researchLeads'].values())==38
# Non-DOI primary sources are allowed only for that exact catalog identity.
with tempfile.TemporaryDirectory() as tmp:
 r=Path(tmp);(r/'resources').mkdir();sample=copy.deepcopy(extra);pid='cheng-landscape-evidence-2025';sample['papers']={pid:sample['papers'][pid]};f=r/'resources/method-transfer-expanded.json';f.write_text(json.dumps(sample))
 def rejected():
  try:load_method_transfers(r,ids,'method-transfer-expanded.json')
  except ValueError:return True
  return False
 assert rejected()
 (r/'resources/catalog.json').write_text(json.dumps({'records':[{'id':pid,'sourceURL':sample['papers'][pid]['url']}]}));assert pid in load_method_transfers(r,ids,'method-transfer-expanded.json')
 sample['papers'][pid]['url']='https://example.org/unapproved';f.write_text(json.dumps(sample));assert rejected()
 sample['papers'][pid]['url']='javascript:alert(1)';f.write_text(json.dumps(sample));assert rejected()
 for bad in ['../method-transfer.json','catalog.json']:
  try:load_method_transfers(r,ids,bad)
  except ValueError:pass
  else:raise AssertionError('Unknown input file accepted')
OUT=ROOT/'test-results';OUT.mkdir(exist_ok=True);(OUT/'method-transfer-expanded-anchors.json').write_text(json.dumps(anchor_proof,ensure_ascii=False,indent=2)+'\n')
result={'passed':True,'legacy_documents_unchanged':len(ids),'total_documents':len(data['documents']),'legacy_annotation_blocks_unchanged':anchor_count,'legacy_four_method_fragments_byte_identical':True,'legacy_method_steps':30,'legacy_method_fields':211,'new_method_papers':15,'total_method_papers':19,'new_method_steps':sum(contract['new_method_step_counts'].values()),'new_literal_step_fields':fields,'new_literal_paragraphs':paragraphs,'old_research_narratives':38,'static_pages_strip_to_exact_baseline':BASE is not None,'singleHTML_all19_identical':True,'sourceURLs_catalog_bound':True,'static_source_notices_additive':True,'browser_tested':False};(OUT/'method-transfer-expanded-static.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
