#!/usr/bin/env python3
"""Source and built-content safeguards for the FarmSTEPS research deepening."""
import hashlib, importlib.util, json, re, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
PAPERS={d['id']:d for d in read('content/papers.json')}
CONTRACT=read('resources/method-contracts-v54.json')['contracts']['farmsteps-2026']
FARM=PAPERS['farmsteps-2026'];TEXT=json.dumps(FARM,ensure_ascii=False)
spec=importlib.util.spec_from_file_location('evidence_check',ROOT/'examples/farmsteps_evidence_check.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ResearchEvidence(unittest.TestCase):
 def test_existing_document_identity_and_sections(self):
  self.assertEqual(FARM['url'],'https://doi.org/10.1007/s13593-026-01097-8')
  self.assertEqual(len(FARM['sections']),12)
  self.assertEqual(FARM['sections'][0][0],'先画出六个模块')
  self.assertEqual(FARM['sections'][5][0],'与海南任务的距离')
  self.assertEqual(len(read('resources/research-coverage-v55.json')['papers']),22)
 def test_real_case_and_algorithm_boundaries(self):
  for x in ['23 ha','Plot3','外部R','eaf::is_nondominated','213679','128','固定','两土地单元']:
   self.assertIn(x,TEXT)
  self.assertIn('候选创新尚未证明原创',CONTRACT['transfer'])
  self.assertIn('未运行FarmSTEPS',CONTRACT['practice']['notReproduced'])
 def test_unresolved_conflicts_are_visible(self):
  for x in ['Suitable plots','520 h','1280 h','2599','444.16','2303','284','不擅改单位']:
   self.assertIn(x,TEXT)
  self.assertFalse(m.audit()['original_model_run'])
 def test_license_independent_from_software(self):
  r=next(r for r in read('resources/catalog.json')['records'] if r['id']=='farmsteps-2026')
  self.assertEqual(r['license']['name'],'CC BY 4.0')
  self.assertEqual(r['status'],'licensed-not-archived')
  self.assertNotIn('bookPath',r)
  self.assertIn('2026-08-30',r['reason'])
  self.assertIn('软件许可',r['reason'])
 def test_no_paper_prompts_require_assessment(self):
  rules=read('resources/research-presentation.json')
  for p in PAPERS.values():
   for s in p['sections']:
    text='\n'.join(s)
    for a,b in sorted(rules.items(),key=lambda x:-len(x[0])):text=text.replace(a,b)
    for term in ['练习','错题','自测','要求能够解释','先完成','然后写出','应能说明']:
     self.assertNotIn(term,text,(p['id'],term))
 def test_all_legacy_contract_note_keys_still_present(self):
  script=(ROOT/'src/contracts.js').read_text()
  for key in ['evidence','inputs','process','reproduction','research','explain','counterexample','next-action']:
   self.assertRegex(script,r"note\([^;]+,'"+key+r"'")
  self.assertIn("'method-contract-'+kind",script)
 def test_frameworks_do_not_request_answers(self):
  for frame in read('resources/study-v3.json')['frameworks'].values():
   self.assertNotIn('先用自己的话回答',frame.get('readingCheck',{}).get('start',''))
 def test_published_fixture_is_not_claimed_reproduction(self):
  spec=importlib.util.spec_from_file_location('minilab',ROOT/'examples/paper_minilab.py')
  lab=importlib.util.module_from_spec(spec);spec.loader.exec_module(lab)
  result=lab.sequence_case()
  self.assertEqual((result['sequences_per_plot'],result['combinations'],result['feasible'],result['non_dominated']),(12,144,100,43))
  self.assertEqual(result['rejected_local_feasible_combination']['labour'],[4,6,14])
 def test_built_content_keeps_original_and_private_boundaries(self):
  if not (ROOT/'dist/site/read/farmsteps-2026.html').exists():self.skipTest('Build before this check')
  html=(ROOT/'dist/site/read/farmsteps-2026.html').read_text()
  for i in range(12):self.assertIn(f'id="s{i}"',html)
  for text in ['1280 h','444.16','CC BY 4.0','研究建议，尚未证明原创']:self.assertIn(text,html)
  self.assertTrue((ROOT/'dist/site/examples/farmsteps_evidence_check.py').exists())
  self.assertNotIn('assistant-review.json',html)
if __name__=='__main__':unittest.main(verbosity=2)
