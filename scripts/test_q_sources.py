#!/usr/bin/env python3
"""Public Q source, frozen lesson, computed fixture and byte-preserving packaging contracts."""
import hashlib,json,re,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads((ROOT/path).read_text())
DOCS={d['id']:d for p in (ROOT/'content').glob('*.json') for d in json.loads(p.read_text())}
CONFIG=read('resources/q-walkthrough-v556.json')

class QSources(unittest.TestCase):
 def test_old_lessons_and_answers_preserved(self):
  for id,old in read('tests/q/source-baseline.json').items():
   self.assertEqual(DOCS[id]['sections'],old['sections'],id)
   self.assertEqual(DOCS[id].get('quiz',[]),old['quiz'],id)
   self.assertIn(CONFIG['guideId'],DOCS[id]['related'])
   static=(ROOT/'dist/site/read'/f'{id}.html').read_text()
   self.assertIn('q-coverage-update',static);self.assertIn('更新说明（5.5.6）',static)

 def test_paper_and_all_figures_have_unchanged_bytes(self):
  record=next(r for r in read('resources/catalog.json')['records'] if r['id']=='cheng-2025')
  self.assertEqual(hashlib.sha256((ROOT/'resources'/record['originalPath']).read_bytes()).hexdigest(),CONFIG['source']['sourceHash'])
  for fig in CONFIG['source']['figures']:
   self.assertEqual(hashlib.sha256((ROOT/'resources'/fig['path']).read_bytes()).hexdigest(),fig['sha256'])
   self.assertEqual(struct.unpack('>II',(ROOT/'resources'/fig['path']).read_bytes()[16:24]),(fig['width'],fig['height']))
   self.assertTrue(fig['anchor'].startswith('#/original/cheng-2025/'))
   self.assertTrue(fig['meaning']);self.assertTrue(fig['boundary'])
  self.assertEqual([f['id'] for f in CONFIG['source']['figures']],['fig3','fig4','fig5'])

 def test_author_arithmetic_distinguishes_verified_si_and_raw_replication(self):
  categories=CONFIG['source']['categoryExample']['categories']
  self.assertEqual([r['count'] for r in categories],[2,7,4,7])
  self.assertEqual([sum(r['scores']) for r in categories],[10,20,10,20])
  for row in categories:
   self.assertEqual(len(row['members']),row['count']);self.assertEqual(len(row['scores']),row['count'])
   self.assertAlmostEqual(row['mean'],sum(row['scores'])/row['count'])
  body=json.dumps(DOCS[CONFIG['guideId']],ensure_ascii=False)
  for phrase in ['327','Farmer_1','20/7','反推候选','不是图上印刷','第三特征值','Kaiser','负权重','0.639461','0.840434','不是第四个','SD、SE或95%CI','41.663%']:
   self.assertIn(phrase,body)
  self.assertEqual(DOCS[CONFIG['guideId']]['quiz'],[])
  self.assertEqual(DOCS[CONFIG['guideId']]['sourceId'],'cheng-2025')

 def test_both_scenarios_are_complete_and_source_linked(self):
  fixture=read('resources/q-results-v556.json')
  self.assertEqual(fixture['schema'],'paper.q.results.v1')
  self.assertEqual([x['id'] for x in fixture['scenarios']],['baseline','reverse-p03'])
  a,b=[x['result'] for x in fixture['scenarios']]
  self.assertFalse(a['author_data_reproduced']);self.assertFalse(b['author_data_reproduced'])
  self.assertEqual(a['nstat'],20);self.assertEqual(a['npeople'],10)
  self.assertEqual(a['factor_arrays'],b['factor_arrays']);self.assertLess(b['weights'][2][0],0)
  self.assertEqual(a['participants'],b['participants']);self.assertEqual(a['statements'],b['statements'])
  for index,row in enumerate(a['data']):
   for person,value in enumerate(row):self.assertEqual(b['data'][index][person],6-value if person==2 else value)

 def test_no_private_storage_or_remote_runtime_dependency(self):
  code=(ROOT/'src/q-walkthrough.js').read_text()
  for bad in ['localStorage.setItem','indexedDB','fetch(','XMLHttpRequest','eval(']:self.assertNotIn(bad,code)
  for good in ['mountedHash','revokeObjectURL','data-no-terms','geometry','isBusy']:self.assertIn(good,code)
  self.assertIn('q_method_readme.md',CONFIG['downloads']);self.assertIn('q_method_sources.json',CONFIG['downloads'])
  for name in CONFIG['downloads']:self.assertTrue((ROOT/'examples'/name).is_file())
  manifest=read('tests/q/reference-manifest.json')
  self.assertEqual(manifest['runtime'],{'R':'4.4.3','qmethod':'1.8.4','psych':'2.5.6','numpy':'2.3.5'})
  self.assertTrue(manifest['declared_before_r_execution'])

 def test_build_preserves_all_example_bytes_and_offline_code(self):
  out=ROOT/'dist/site';self.assertTrue((out/'q-walkthrough-data.js').exists(),'Build this stage before package checks')
  q=json.loads((out/'q-walkthrough-data.js').read_text().split('=',1)[1].rstrip(';\n'))
  self.assertEqual(len(q['scenarios']),2)
  for name in ['q-walkthrough.js','q-walkthrough.css']:
   self.assertEqual((out/name).read_bytes(),(ROOT/'src'/name).read_bytes())
  data=json.loads((out/'data.json').read_text())
  for path in (ROOT/'examples').iterdir():
   if path.is_file() and path.suffix in {'.py','.R','.csv','.md','.json'}:
    self.assertEqual((out/'examples'/path.name).read_bytes(),path.read_bytes(),path.name)
    self.assertEqual(data['files'][path.name].encode('utf-8'),path.read_bytes(),path.name)
  expected=read('tests/q/reference-manifest.json')['input']['sha256']
  self.assertEqual(hashlib.sha256((out/'examples/q_synthetic.csv').read_bytes()).hexdigest(),expected)
  self.assertIn(b'\r\n',(out/'examples/q_synthetic.csv').read_bytes())
  single=(out/'downloads/Paper-Lab-offline.html').read_text()
  for text in ['window.PAPER_Q=','PaperQWalkthrough','reverse-p03','q-scroll-hint']:self.assertIn(text,single)
  self.assertNotIn('<script src="q-walkthrough',single)
  release=json.loads((out/'release.json').read_text());self.assertEqual(release['appVersion'],read('resources/application-release.json')['version']);self.assertEqual(release['qWalkthrough']['version'],'5.5.6')
  self.assertEqual(release['researchLibrary']['papers'],22);self.assertEqual(release['qWalkthrough']['scenarios'],2)
  self.assertTrue(release['qWalkthrough']['authorScalingVerified']);self.assertFalse(release['qWalkthrough']['authorResultsReproduced'])
  self.assertEqual(release['qWalkthrough']['referenceComparison'],'pinned-R-required-in-CI')

if __name__=='__main__':unittest.main(verbosity=2)
