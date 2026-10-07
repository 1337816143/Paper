#!/usr/bin/env python3
"""Additive Ditzler closure; real browser execution is a separate CI gate."""
from pathlib import Path
from liang_correction_contract import original_leads, original_source_bytes
from html.parser import HTMLParser
import hashlib,html,json,re,sys,tempfile,copy,zipfile
ROOT=Path(__file__).resolve().parents[1]; SITE=ROOT/'dist/site';sys.path.insert(0,str(ROOT/'scripts'))
from research_leads import load_research_leads,static_lead_html
from method_transfer import load_method_transfers,static_transfer_html,static_source_notice
sha=lambda b:hashlib.sha256(b).hexdigest();canon=lambda d:json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
contract=json.loads((ROOT/'tests/ditzler-baseline.json').read_text());data=json.loads((SITE/'data.json').read_text());pid='ditzler-2019'
application=json.loads((ROOT/'resources/application-release.json').read_text())
assert "assert d['appVersion']=='"+application['version']+"'" in (ROOT/'.github/workflows/pages.yml').read_text(), 'Live deploy guard must require the current exact release'
legacy=[d for d in data['documents'] if d['id'] in contract['documentIds']]
assert len(legacy)==129 and sha(canon(legacy))==contract['documentsSHA256']
assert [d['id'] for d in data['documents'] if d['id'] not in contract['documentIds']]==['ditzler-reading-20261007','liang-source-discrepancy-20261007']
assert set(data['researchLeads'])==set(contract['legacyLeadIds'])|{pid}
assert set(data['methodTransfers'])==set(contract['legacyMethodIds'])|{pid}
assert sha(canon({k:original_leads(data['researchLeads'])[k] for k in contract['legacyLeadIds']}))==contract['researchLeadsSHA256']
assert sha(canon({k:data['methodTransfers'][k] for k in contract['legacyMethodIds']}))==contract['methodTransfersSHA256']
for path,h in contract['unchangedSourceSHA256'].items():assert sha(original_source_bytes(ROOT,path))==h,path
ids={d['id'] for d in data['documents']}; lead=data['researchLeads'][pid]; method=data['methodTransfers'][pid]
assert load_research_leads(ROOT,ids)[pid]==lead
assert load_method_transfers(ROOT,ids,'method-transfer-ditzler.json')=={pid:method}
class Fragment(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.links=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);assert tag not in {'img','script','iframe','object','embed'}
  assert not any(k.lower().startswith('on') for k in a);assert 'prose' not in a.get('class','').split()
  if 'id'in a:self.ids.append(a['id'])
  if tag=='a':self.links.append(a['href'])
f=Fragment();f.feed(lead['html']+method['html']);assert len(f.ids)==len(set(f.ids));assert all('ditzler-2019' in identity for identity in f.ids)
links=json.loads((ROOT/'resources/research-leads/accepted-ditzler.json').read_text())['papers'][pid]['sourceLinks']
assert all(x['url'] in f.links for x in links)
page=(SITE/'read'/f'{pid}.html').read_text();l=static_lead_html(lead,pid);m=static_transfer_html(method,pid)
for record in json.loads((ROOT/'resources/catalog.json').read_text())['records']:
 for url in set(record.get('aliases',[])+[record.get('sourceURL',''),record.get('downloadURL','')]):
  if url:m=m.replace('href="'+html.escape(url,quote=True)+'"','href="../index.html#/original/'+record['id']+'"')
notice=static_source_notice(ROOT,pid)
assert all(page.count(x)==1 for x in [l,m,notice]);assert sha(page.replace(l,'',1).replace(m,'',1).replace(notice,'',1).encode())==contract['legacyDitzlerStaticSHA256']
assert page.index(l)<page.index(m)<page.index('<section class="reader" id="s0"')
single=(SITE/'downloads/Paper-Lab-offline.html').read_text();embedded=json.loads(re.search(r'window\.PAPER_DATA=(.*?);\n',single)[1]);assert embedded==data
library=json.loads((SITE/'research-library-data.js').read_text().removeprefix('window.PAPER_LIBRARY=').strip().removesuffix(';'))
update=json.loads((ROOT/'resources/ditzler-reading-update.json').read_text());original=json.loads((ROOT/'resources/research-coverage-v55.json').read_text());original['papers'][pid].update(update['coverage']);assert library['coverage']==original
assert (SITE/'research-library-data.js').read_text().replace('</script','<\\/script') in single
full=(ROOT/'resources/research-leads/ditzler-2019/full.txt').read_text();brief=(ROOT/'resources/research-leads/ditzler-2019/brief.txt').read_text();raw=json.loads((ROOT/'resources/method-transfer-ditzler.json').read_text());row=raw['papers'][pid]
assert len(row['steps'])==8 and len(row['notes'])==128
for token in ['−439','1750','336.86','333','1.165','1.07','面积抵消','下界20','403','作者程序']:
 assert token in full,token
for token in ['ED=0','两倍','下界','面积抵消','−439','403']:
 assert token in brief,token
assert '所有项非负' not in full and 'NP旱地种稻' not in full
all_text=json.dumps(raw,ensure_ascii=False);assert 'Σw_i A_i q_i' in all_text and '共同候选集' in all_text
for title,count in [('Table1',16),('Table2',11),('A1',15),('A2 DK',21),('A3 NP',24),('A4',25)]:assert sum(n['title'].startswith(title) for n in row['notes'])==count
# No binary or source copies were added; the publication source stays external.
assert not any(p.suffix.lower() in {'.pdf','.png','.jpg','.jpeg','.webp'} for p in (ROOT/'resources/research-leads/ditzler-2019').rglob('*'))
assert 3023+332-3356-438==-439 and 5302+242-1988-831==2725
# The allowlist fails closed for altered URLs and duplicate old lead identities.
with tempfile.TemporaryDirectory() as temp:
 r=Path(temp);folder=r/'resources/research-leads';folder.mkdir(parents=True)
 (folder/'accepted.json').write_text(json.dumps({'schema':'paper.research-leads.v1','papers':{}}))
 import shutil;shutil.copytree(ROOT/'resources/research-leads/ditzler-2019',folder/pid)
 supplement=json.loads((ROOT/'resources/research-leads/accepted-ditzler.json').read_text());supplement['papers'][pid]['sourceLinks'][0]['url']='javascript:alert(1)';(folder/'accepted-ditzler.json').write_text(json.dumps(supplement))
 try:load_research_leads(r,{pid});raise AssertionError('unsafe source link accepted')
 except ValueError:pass
result={'passed':True,'baseCommit':contract['baseCommit'],'protectedOldSourceBlobs':len(contract['unchangedSourceSHA256']),'legacyDocuments':129,'legacyNarratives':38,'legacyMethods':19,'newNarratives':2,'newMethodSteps':8,'publishedTableRows':112,'literalBlocks':len(f.ids),'oldStaticPageExactAfterStrippingAddition':True,'onlineStaticSingleHTMLConsistent':True,'freshBrowserRun':False,'authorSoftwareExecuted':False}
(ROOT/'test-results').mkdir(exist_ok=True);(ROOT/'test-results/ditzler-static.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
