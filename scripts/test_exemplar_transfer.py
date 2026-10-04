#!/usr/bin/env python3
"""Evidence, preservation, and failed-refresh regression checks (stdlib only)."""
import copy, hashlib, importlib.util, json, runpy, sys, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
GUIDE=read('content/exemplar-transfer-v553.json')[0]
LEGACY={'liang-2022': {'file': 'content/papers.json', 'sections': 8, 'digest': 'c8f732d83a00c8568e62474f35a284eacc5552fe1b0b89e536dcc9890df87f14'}, 'positive-deviance': {'file': 'content/methods.json', 'sections': 4, 'digest': '7a654bf307d4fe160fb93e436e644003c7db4712416b5e11a81ffd02b4b551e6'}, 'research-synthesis': {'file': 'content/research-library-v55.json', 'sections': 5, 'digest': 'a59bf59e8b0bc8696159d42b78f50d0e49a9a71af0536131d7f218b1ab0376a3'}}
class ExemplarTransfer(unittest.TestCase):
 def test_legacy_sections_quizzes_and_source_ids_are_unchanged(self):
  for id,e in LEGACY.items():
   d=next(x for x in read(e['file']) if x['id']==id)
   old={'sections':d['sections'][:e['sections']],'quiz':d.get('quiz',[])}
   self.assertEqual(hashlib.sha256(json.dumps(old,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),e['digest'])
  self.assertEqual(len(read('resources/research-coverage-v55.json')['papers']),22)
  self.assertEqual(GUIDE['type'],'guide');self.assertEqual(GUIDE['quiz'],[])
 def test_exact_evidence_blocks_and_hash(self):
  ledger=GUIDE['sourceLedger'];r=next(x for x in read('resources/catalog.json')['records'] if x['id']=='liang-2022')
  self.assertEqual(hashlib.sha256((ROOT/'resources'/r['originalPath']).read_bytes()).hexdigest(),ledger['sourceHash'])
  book=read('resources/'+r['bookPath']);blocks={b['id']:p['number'] for p in book['pages'] for b in p['blocks']}
  for e in ledger['evidence']:
   self.assertEqual(e['kind'],'article-evidence')
   for id in e['blocks']:self.assertIn(blocks[id],e['pages'])
  for field in ['fullThesisAcquired','authorDataAcquired','authorCodeRun']:self.assertFalse(ledger[field])
 def test_guide_exposes_inference_limits_and_complete_results(self):
  text=json.dumps(GUIDE,ensure_ascii=False)
  for s in ['0.2','0.02','九例中的一例','共同输入','+1100','−350','30 h','反证','相同候选活动','尚未证明原创','未取得','没有运行','原始数据']:
   self.assertIn(s,text)
  for s in ['github_pat_','ghp_','assistant-review.json','private/paper-sync']:
   self.assertNotIn(s,text)
 def test_live_provenance_points_to_same_version_as_catalog(self):
  r=next(x for x in read('resources/catalog.json')['records'] if x['id']=='toorop-2023')
  p=read('resources/'+str(Path(r['bookPath']).parent/'provenance.json'))
  self.assertEqual(p['sha256'],r['sha256'])
  for key in ['bookPath','originalPath','epubPath']:
   self.assertEqual(p[key],r[key]);self.assertTrue((ROOT/'resources'/p[key]).is_file())
  self.assertEqual(hashlib.sha256((ROOT/'resources'/p['originalPath']).read_bytes()).hexdigest(),p['sha256'])
  self.assertTrue((ROOT/'resources/library/toorop-2023/e4c7cc912b38/source.pdf').is_file())
 def test_refresh_candidate_paths_and_failure_preserve_active_record(self):
  raw=b'%PDF-synthetic-refresh';sha=hashlib.sha256(raw).hexdigest()
  record={'id':'test-paper','title':'Synthetic fixture','sourceURL':'https://doi.org/10.1000/test','downloadURL':'https://example.test/source.pdf','sha256':'old','bookPath':'library/test-paper/old/book.json','originalPath':'library/test-paper/old/source.pdf','epubPath':'library/test-paper/old/article.epub'}
  class Doc:
   def __len__(self):return 1
   def __getitem__(self,i):return types.SimpleNamespace(get_text=lambda:'DOI 10.1000/test')
  response=types.SimpleNamespace(content=raw,raise_for_status=lambda:None)
  requests=types.SimpleNamespace(get=lambda *a,**k:response)
  fitz=types.SimpleNamespace(open=lambda **k:Doc())
  refine=types.SimpleNamespace(article_license=lambda d:({'name':'CC BY 4.0'},'synthetic'))
  for fail in [False,True]:
   with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);(root/'resources').mkdir();p=root/'resources/catalog.json';p.write_text(json.dumps({'records':[copy.deepcopy(record)]}))
    seen=[]
    def convert(pdf,candidate,dest,prefix):
     seen.append(copy.deepcopy(candidate))
     for key,file in [('bookPath','book.json'),('originalPath','source.pdf'),('epubPath','article.epub')]:self.assertEqual(candidate[key],prefix+'/'+file)
     if fail:raise RuntimeError('Synthetic conversion interruption')
     (dest/'provenance.json').write_text(json.dumps(candidate))
    with patch.dict(sys.modules,{'requests':requests,'fitz':fitz,'refine_sources':refine,'compile_sources':types.SimpleNamespace(convert=convert)}):
     env=runpy.run_path(str(ROOT/'scripts/refresh_sources.py'));env['run'].__globals__['ROOT']=root;env['run']()
    active=json.loads(p.read_text())['records'][0]
    self.assertEqual(len(seen),1)
    if fail:self.assertEqual(active,record)
    else:
     self.assertEqual(active['sha256'],sha)
     self.assertEqual(json.loads((root/'resources'/Path(active['bookPath']).parent/'provenance.json').read_text()),active)
 def test_built_guide_and_download_preserve_full_artifact(self):
  out=ROOT/'dist/site';docs={d['id']:d for d in json.loads((out/'data.json').read_text())['documents']}
  self.assertEqual(docs[GUIDE['id']],GUIDE)
  self.assertIn('liang-exemplar-transfer',(out/'read/liang-2022.html').read_text())
  self.assertEqual((out/'examples/exemplar_transfer.py').read_bytes(),(ROOT/'examples/exemplar_transfer.py').read_bytes())
  self.assertIn('exemplar_transfer.py',(out/'downloads/Paper-Lab-offline.html').read_text())
if __name__=='__main__':unittest.main(verbosity=2)
