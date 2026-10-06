#!/usr/bin/env python3
"""Official-SI arithmetic from published tables; never author raw-data replication."""
import hashlib,json,sys,unittest
from fractions import Fraction
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'examples'))
from q_pipeline import analyze

def read(p):return json.loads((ROOT/p).read_text())
class SIChecks(unittest.TestCase):
 def test_all_72_published_category_values_and_strict_priority(self):
  d=read('tests/q/cheng-published-arrays.json');self.assertEqual(len(d['rows']),18)
  slots=[1]*2+[2]*4+[3]*8+[4]*4+[5]*2;counts=d['categoryCounts'];priority=[0]*4;seen=set()
  for row in d['rows']:
   self.assertNotIn(row['perspective'],seen);seen.add(row['perspective'])
   values=row['factorScores'];self.assertEqual(sorted(values),slots)
   pos=0
   for k,n in enumerate(counts):
    lo,hi=sum(slots[:n]),sum(slots[-n:]);total=sum(values[pos:pos+n]);pos+=n
    score=100*Fraction(total-lo,hi-lo)
    self.assertEqual(f'{float(score):.2f}',f'{row["reportedCategoryScores"][k]:.2f}',(row['perspective'],k))
    self.assertEqual(score,100*(Fraction(total,n)-Fraction(lo,n))/(Fraction(hi,n)-Fraction(lo,n)))
    priority[k]+=score>50
  self.assertEqual(priority,[11,9,4,7]);self.assertEqual(len(seen),18)
  company=next(row for row in d['rows'] if row['perspective']=='Company_2')
  self.assertEqual(company['reportedCategoryScores'][2],50);self.assertFalse(company['reportedCategoryScores'][2]>50)
 def test_positive_common_scale_invariance_for_existing_two_scenarios(self):
  for scenario in ['baseline','reverse-p03']:
   r=analyze(scenario=scenario);D=np.array(r['data']);w=np.array(r['weights']);T=np.array(r['weighted_totals'])
   c=10/w.max(axis=0);self.assertTrue(np.all(c>0));W=w*c;self.assertTrue(np.allclose(W.max(axis=0),10))
   scaled=D@W;Z=(scaled-scaled.mean(axis=0))/scaled.std(axis=0,ddof=1)
   self.assertTrue(np.allclose(Z,r['statement_z'],atol=1e-12,rtol=0));self.assertTrue(np.allclose(scaled,T*c,atol=1e-12,rtol=0))
   for ddof in [0,1]:
    z=(T-T.mean(axis=0))/T.std(axis=0,ddof=ddof)
    self.assertTrue(np.allclose((scaled-scaled.mean(axis=0))/scaled.std(axis=0,ddof=ddof),z,atol=1e-12,rtol=0))
    self.assertTrue(np.allclose((-T+T.mean(axis=0))/(-T).std(axis=0,ddof=ddof),-z,atol=1e-12,rtol=0))
   different=w.copy();different[0,0]*=2;changed=D@different
   self.assertFalse(np.allclose((changed-changed.mean(axis=0))/changed.std(axis=0,ddof=1),r['statement_z']))
 def test_si_evidence_and_unchanged_synthetic_input_contract(self):
  config=read('resources/q-walkthrough-v556.json');si=config['source']['supplement']
  self.assertTrue(si['authorScalingVerified']);self.assertFalse(si['authorResultsReproduced']);self.assertEqual(si['formulaPages'],[3,4,5]);self.assertEqual(si['categoryTablePage'],14)
  self.assertEqual(hashlib.sha256((ROOT/'examples/q_synthetic.csv').read_bytes()).hexdigest(),read('tests/q/reference-manifest.json')['input']['sha256'])
  g=read('content/q-walkthrough-v556.json')[0];self.assertEqual(g['quiz'],[]);self.assertEqual(len(g['sections']),23)
  self.assertIn('旧正文',g['evidence']);self.assertIn('s0–s19',g['sections'][20][2]);self.assertIn('SD口径',g['sections'][21][2]);self.assertIn('Company_2',g['sections'][22][2])
 def test_public_recalculation_matches_independently_transcribed_test_fixture(self):
  import q_si_categories
  public=read('examples/q_published_tables.json');independent=read('tests/q/cheng-published-arrays.json')
  for key in ['rows','categoryOrder','categoryCounts']:self.assertEqual(public[key],independent[key])
  result=q_si_categories.analyze(public)
  self.assertEqual(result['matchedCells'],72);self.assertEqual(result['strictPriorityCounts'],[11,9,4,7])
  self.assertFalse(result['authorRawDataReproduced'])
  self.assertEqual(read('resources/q-walkthrough-v556.json')['source']['publishedTables'],public)
  for name in ['q_si_categories.py','q_published_tables.json']:
   self.assertEqual((ROOT/'examples'/name).read_bytes(),(ROOT/'dist/site/examples'/name).read_bytes())
 def test_append_contract_keeps_original_baseline_hash_and_all_old_anchors(self):
  g=read('content/q-walkthrough-v556.json')[0];c=read('tests/q/append-only-contract.json')
  old=read('tests/annual-balance/source-baseline.json')['documents'][g['id']]
  digest=lambda x:hashlib.sha256(json.dumps(x,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
  self.assertEqual(c['preservedSectionCount'],20);self.assertEqual(old['sectionCount'],20)
  self.assertEqual(digest(g['sections'][:20]),old['sectionsSha256']);self.assertEqual(c['preservedSectionsSha256'],old['sectionsSha256'])
  self.assertEqual(len(g['sections']),23);self.assertEqual([s[0] for s in g['sections'][20:]],c['appendedTitles'])
  text=(ROOT/'dist/site/read/cheng-2025-q-walkthrough.html').read_text()
  for anchor in c['preservedAnchors']+c['appendedAnchors']:self.assertEqual(text.count('id="'+anchor+'"'),1)
 def test_direct_legacy_anchors_expose_current_source_status_before_old_prose(self):
  import re,subprocess
  static=(ROOT/'dist/site/read/cheng-2025-q-walkthrough.html').read_text()
  for i in [16,19]:
   section=re.search(r'<section class="reader" id="s'+str(i)+r'">(.*?)</section>',static).group(1)
   self.assertLess(section.index('q-si-legacy-update'),section.index('class="prose"'))
   for value in ['不再表示当前状态','href="#s20"','href="#s22"']:self.assertIn(value,section)
  code=(ROOT/'src/app.js').read_text();function=re.search(r'function qSourceCorrection\(d,i\).*?(?=\nfunction article)',code).group(0)
  check=function+";const d={id:'cheng-2025-q-walkthrough'};for(const i of [16,19])if(!qSourceCorrection(d,i).includes('不再表示当前状态'))throw Error(i);for(const i of [0,15,20])if(qSourceCorrection(d,i))throw Error(i);if(qSourceCorrection({id:'another'},16))throw Error('scope');console.log('anchor notice passed');"
  self.assertEqual(subprocess.run(['node','-e',check],capture_output=True,text=True).returncode,0)
  self.assertIn('${qSourceCorrection(d,i)}<div class="prose">',code)
if __name__=='__main__':unittest.main(verbosity=2)
