from pathlib import Path
import copy, hashlib, json, shutil, sys, tempfile, unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from source_refresh_contract import validate_refresh, read, check_unchanged_sources, canonical_layout, digest
LIVE_REPORT=read(ROOT/'resources/refresh-report.json');LIVE_CATALOG=read(ROOT/'resources/catalog.json')
# Mutation tests use deterministic synthetic states, not live ordering/status.
CATALOG={'records':[{'id':'archived','bookPath':'library/archived/book.json','sha256':'a'*64},{'id':'pending'}]}
REPORT={'schema':'paper.source.refresh.v2','checkedAt':'2026-01-01T00:00:00Z','policy':'Only already approved identities automatically update; missing rights require review. Old complete copies are never deleted.','records':[{'id':'archived','status':'unchanged','checkedAt':'2026-01-01T00:00:00Z','sha256':'a'*64},{'id':'pending','status':'requires-acquisition-or-rights-review','checkedAt':'2026-01-01T00:00:00Z'}]}

class Regression(unittest.TestCase):
 def test_current_report_and_future_timestamp(self):
  validate_refresh(LIVE_REPORT,LIVE_CATALOG)
  validate_refresh(REPORT,CATALOG)
  r=copy.deepcopy(REPORT);r['checkedAt']='2026-10-25T00:00:00Z'
  for x in r['records']:x['checkedAt']=r['checkedAt']
  validate_refresh(r,CATALOG)
 def test_valid_reordered_and_retained_reports(self):
  for retained in [False,True]:
   for pending_first in [False,True]:
    r=copy.deepcopy(REPORT)
    if retained:
     i=next(i for i,row in enumerate(r['records']) if row['id']=='archived')
     r['records'][i]={'id':'archived','status':'retained-last-good-version','checkedAt':r['checkedAt'],'error':'Synthetic timeout'}
    if pending_first:r['records'].reverse()
    with self.subTest(retained=retained,pending_first=pending_first):validate_refresh(r,CATALOG)
 def test_bad_report_fails(self):
  mutations=[lambda r:r['records'].pop(),lambda r:r['records'].append(r['records'][0]),lambda r:r['records'][0].update(sha256='0'*64),lambda r:r['records'][0].update(status='offline'),lambda r:r.update(checkedAt='tomorrow'),lambda r:r.update(extra='unreviewed'),lambda r:next(x for x in r['records'] if 'sha256' not in x).update(status='unchanged',sha256='0'*64),lambda r:r.update(policy='anything allowed')]
  for mutation in mutations:
   r=copy.deepcopy(REPORT);mutation(r)
   with self.subTest(r=r),self.assertRaises((AssertionError,ValueError)):validate_refresh(r,CATALOG)
 def test_retained_failure(self):
  r=copy.deepcopy(REPORT);i=next(i for i,row in enumerate(r['records']) if row['id']=='archived');r['records'][i]={'id':'archived','status':'retained-last-good-version','checkedAt':r['checkedAt'],'error':'Temporary network error'};validate_refresh(r,CATALOG)
  r['records'][i]['sha256']='a'*64
  with self.assertRaises(AssertionError):validate_refresh(r,CATALOG)
 def test_layout_baselines_are_anchored_to_original_contract(self):
  c=read(ROOT/'tests/ditzler-baseline.json')['unchangedSourceSHA256'];s=read(ROOT/'tests/generated-source-baseline.json')
  for path,expected in s.items():
   self.assertEqual(expected['originalSHA256'],c[path])
   self.assertEqual(digest(canonical_layout(path,read(ROOT/path))),expected['semanticSHA256'])
 def test_contract_preserves_primary_and_layout_tamper_rejection(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'resources').mkdir();(p/'tests').mkdir();expected={}
   for name in ['refresh-report.json','catalog.json','study-layouts.json','study-layout-audit.json']:
    shutil.copyfile(ROOT/'resources'/name,p/'resources'/name)
    expected['resources/'+name]=digest((p/'resources'/name).read_bytes())
   s=read(ROOT/'tests/generated-source-baseline.json');shutil.copyfile(ROOT/'tests/generated-source-baseline.json',p/'tests/generated-source-baseline.json')
   for path in s:expected[path]=s[path]['originalSHA256']
   (p/'resources/source.pdf').write_bytes(b'SYNTHETIC primary source bytes');expected['resources/source.pdf']=digest((p/'resources/source.pdf').read_bytes());check_unchanged_sources(p,expected)
   (p/'resources/source.pdf').write_bytes(b'SYNTHETIC altered source bytes')
   with self.assertRaises(AssertionError):check_unchanged_sources(p,expected)
   (p/'resources/source.pdf').write_bytes(b'SYNTHETIC primary source bytes')
   data=read(p/'resources/study-layouts.json');first=next(iter(data));data[first]['sourceHash']='0'*64;(p/'resources/study-layouts.json').write_text(json.dumps(data))
   with self.assertRaises(AssertionError):check_unchanged_sources(p,expected)
 def test_layout_array_order_and_duplicate_ids(self):
  path='resources/study-layouts.json';data=read(ROOT/'resources/study-layouts.json');before=canonical_layout(path,data)
  key=next(k for k,v in data.items() if len(v['groups'])>1);data[key]['groups'].reverse()
  self.assertNotEqual(before,canonical_layout(path,data))
  audit=read(ROOT/'resources/study-layout-audit.json');audit.append(copy.deepcopy(audit[0]))
  with self.assertRaises(AssertionError):canonical_layout('resources/study-layout-audit.json',audit)
 def test_duplicate_json_key_rejected(self):
  with tempfile.NamedTemporaryFile(mode='w+',suffix='.json') as f:
   f.write('{"x":1,"x":2}');f.flush()
   with self.assertRaises(AssertionError):read(f.name)
if __name__=='__main__':unittest.main(verbosity=2)
