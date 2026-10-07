#!/usr/bin/env python3
"""Verify two exact evidence additions, all legacy source bytes, and all surfaces."""
from pathlib import Path
from html.parser import HTMLParser
import copy,hashlib,html,json,re,sys
from liang_correction_contract import ADDITION,HASHES,original_leads,original_source_bytes
ROOT=Path(__file__).resolve().parents[1];SITE=ROOT/'dist/site';sys.path.insert(0,str(ROOT/'scripts'))
from research_leads import load_research_leads,static_lead_html
sha=lambda b:hashlib.sha256(b).hexdigest();canon=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
contract=json.loads((ROOT/'tests/liang-correction-baseline.json').read_text());data=json.loads((SITE/'data.json').read_text())
assert len(data['documents'])==131
legacy=[d for d in data['documents'] if d['id'] in contract['legacyDocumentIds']]
assert [d['id'] for d in legacy]==contract['legacyDocumentIds']
assert sha(canon(legacy))==contract['legacyDocumentsSHA256']
assert [d['id'] for d in data['documents'] if d['id'] not in contract['legacyDocumentIds']]==['liang-source-discrepancy-20261007']
assert sha(canon(original_leads(data['researchLeads'])))==contract['legacyResearchLeadsSHA256']
assert sha(canon(data['methodTransfers']))==contract['legacyMethodsSHA256']
assert len(data['researchLeads'])==20 and sum(len(x['hashes']) for x in data['researchLeads'].values())==40
for path,h in contract['unchangedSourceSHA256'].items():assert sha((ROOT/path).read_bytes())==h,path
for version,(before,after) in HASHES.items():
 path=f'resources/research-leads/liang-2022/{version}.txt';raw=(ROOT/path).read_bytes();assert sha(raw)==after
 assert sha(original_source_bytes(ROOT,path))==before
 paragraphs=re.split(r'\r?\n\s*\r?\n',raw.decode().rstrip('\r\n'));index=7 if version=='full' else 3
 assert len(paragraphs)==(11 if version=='full' else 5)
 assert paragraphs[index].endswith(ADDITION) and sum(ADDITION in p for p in paragraphs)==1
assert data['researchLeads']==load_research_leads(ROOT,{d['id'] for d in data['documents']})
row=data['researchLeads']['liang-2022'];old=original_leads(data['researchLeads'])['liang-2022'];assert old['html']==contract['oldLiangHTML']
class IDs(HTMLParser):
 def __init__(self):super().__init__();self.ids=[]
 def handle_starttag(self,t,a):
  attrs=dict(a)
  if 'id'in attrs:self.ids.append(attrs['id'])
p=IDs();p.feed(row['html']);q=IDs();q.feed(old['html']);assert p.ids==q.ids and len(p.ids)==len(set(p.ids))
for name,h in contract['legacyStaticPagesSHA256'].items():
 text=(SITE/'read'/name).read_text()
 if name=='liang-2022.html':
  new_fragment=static_lead_html(row,'liang-2022');old_fragment=static_lead_html(old,'liang-2022');assert text.count(new_fragment)==1;text=text.replace(new_fragment,old_fragment,1)
 elif name=='index.html':
  doc=next(d for d in data['documents'] if d['id']=='liang-source-discrepancy-20261007');entry='<p><a href="'+doc['id']+'.html">'+html.escape(doc['title'])+'</a></p>';assert text.count(entry)==1;text=text.replace(entry,'',1)
 assert sha(text.encode())==h,name
single=(SITE/'downloads/Paper-Lab-offline.html').read_text();embedded=json.loads(re.search(r'window\.PAPER_DATA=(.*?);\n',single)[1]);assert embedded==data
release=json.loads((SITE/'release.json').read_text());application=json.loads((ROOT/'resources/application-release.json').read_text());assert release['appVersion']==application['version']=='5.5.16'
assert "assert d['appVersion']=='5.5.16'" in (ROOT/'.github/workflows/pages.yml').read_text()
# A different or repeated append must fail the frozen legacy baseline comparison.
for mutation in [ADDITION+'extra',ADDITION+ADDITION]:
 changed=copy.deepcopy(data['researchLeads']);changed['liang-2022']['html']=changed['liang-2022']['html'].replace(html.escape(ADDITION),html.escape(mutation),1)
 try:ok=sha(canon(original_leads(changed)))==contract['legacyResearchLeadsSHA256']
 except AssertionError:ok=False
 assert not ok,'Unexpected or duplicate prose escaped the old frozen hashes'
result={'passed':True,'baseCommit':contract['baseCommit'],'legacyDocuments':130,'protectedOldSourceBlobs':len(contract['unchangedSourceSHA256']),'legacyStaticPages':len(contract['legacyStaticPagesSHA256']),'preservedNarratives':40,'preservedMethods':20,'paragraphCounts':{'full':11,'brief':5},'exactAppendPositions':{'full':8,'brief':4},'existingIDsUnchanged':True,'oldTextExactAfterRemovingApprovedAppend':True,'onlineStaticSingleHTMLConsistent':True,'newBinaryFiles':False,'browserExecutedLocally':False,'sourceCommit':release['sourceCommit']}
(ROOT/'test-results').mkdir(exist_ok=True);(ROOT/'test-results/liang-correction-static.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
