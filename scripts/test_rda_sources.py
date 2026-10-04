#!/usr/bin/env python3
"""RDA source/legacy/package contracts. No private reader records."""
import csv, hashlib, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(path): return json.loads((ROOT/path).read_text())
DOCS={d['id']:d for p in (ROOT/'content').glob('*.json') for d in json.loads(p.read_text())}
CONFIG=read('resources/rda-walkthrough-v555.json')

class RDASources(unittest.TestCase):
 def test_legacy_sections_and_answers_remain_byte_equivalent_as_strings(self):
  for id, old in read('tests/rda/source-baseline.json').items():
   current=DOCS[id]
   self.assertEqual(current['sections'][:len(old['sections'])],old['sections'],id)
   self.assertEqual(current.get('quiz',[]),old.get('quiz',[]),id)
  self.assertEqual(len(DOCS['rda']['sections']),len(read('tests/rda/source-baseline.json')['rda']['sections']))
  self.assertEqual(len(DOCS['cheng-2023']['sections']),len(read('tests/rda/source-baseline.json')['cheng-2023']['sections']))

 def test_original_pdf_and_figure_unchanged(self):
  source=CONFIG['source'];record=next(r for r in read('resources/catalog.json')['records'] if r['id']=='cheng-2023')
  self.assertEqual(hashlib.sha256((ROOT/'resources'/record['originalPath']).read_bytes()).hexdigest(),source['sourceHash'])
  self.assertEqual(hashlib.sha256((ROOT/'resources'/source['figurePath']).read_bytes()).hexdigest(),source['figureHash'])
  book=read('resources/'+record['bookPath'])
  ids={b['id'] for p in book['pages'] for b in p['blocks']}
  self.assertIn('p9-b5-ee7a849',ids);self.assertIn('p4-b9-c6bf7b4',ids)
  self.assertIn('未取得',source['percentages']);self.assertIn('scaling',source['figureCaption'])

 def test_explicit_source_fields_and_bounded_new_guide(self):
  self.assertEqual(len(CONFIG['variables']),14)
  fields={v['id']:v for v in CONFIG['variables']}
  self.assertEqual(fields['SOM']['unit'],'g/kg');self.assertEqual(fields['EC']['unit'],'dS/m')
  self.assertEqual(fields['SOM']['year'],'2018');self.assertEqual(fields['N_input']['year'],'2020')
  self.assertIn('TFI',fields['TFI']['unit']);self.assertIn('Stevia',fields['Sugar crops']['meaning'])
  self.assertIn('人数',fields['Population']['unit']);self.assertIn('2018',fields['Non-agricultural labour']['year'])
  guide=DOCS[CONFIG['guideId']]
  self.assertEqual(guide['sourceId'],'cheng-2023');self.assertEqual(guide['quiz'],[]);self.assertEqual(len(guide['sections']),13)
  text=json.dumps(guide,ensure_ascii=False)
  for phrase in ['35个村庄','267','Revenue','gross revenue','0.25','11.547005','0.353553','0.907322','0.435815','30.556%','60%','0.272166','0.816497','1000','Table S1/S5','尚未在本轮执行']:
   self.assertIn(phrase,text)

 def test_single_fixture_and_no_private_or_remote_runtime_dependency(self):
  rows=list(csv.DictReader((ROOT/'examples'/CONFIG['csv']).read_text().splitlines()))
  self.assertEqual([r['village_id'] for r in rows],['V1','V2','V3','V4'])
  self.assertEqual(float(rows[-1]['perception_b']),3.75)
  for file in ['src/rda-walkthrough.js','src/rda-model.js']:
   code=(ROOT/file).read_text()
   for disallowed in ['localStorage.setItem','indexedDB','fetch(','XMLHttpRequest','eval(','setInterval(','setTimeout(']:
    self.assertNotIn(disallowed,code)
  for file in ['examples/rda_walkthrough.py','examples/rda_reference.R','examples/rda_synthetic_villages.csv']:
   self.assertTrue((ROOT/file).is_file())

 def test_built_assets_offline_and_release_boundaries(self):
  out=ROOT/'dist/site';self.assertTrue((out/'rda-walkthrough-data.js').exists(),'Build this stage before package tests')
  datajs=(out/'rda-walkthrough-data.js').read_text();data=json.loads(datajs.split('=',1)[1].rstrip(';\n'))
  self.assertEqual(data['source']['figureHash'],CONFIG['source']['figureHash']);self.assertEqual(len(data['records']),4)
  self.assertEqual(data['records'][3]['perception_b'],3.75)
  for name in ['rda-model.js','rda-walkthrough.js','rda-walkthrough.css']:
   self.assertEqual((out/name).read_bytes(),(ROOT/'src'/name).read_bytes())
  for name in ['rda_walkthrough.py','rda_reference.R','rda_synthetic_villages.csv']:
   self.assertEqual((out/'examples'/name).read_bytes(),(ROOT/'examples'/name).read_bytes())
  single=(out/'downloads/Paper-Lab-offline.html').read_text()
  for phrase in ['window.PAPER_RDA=','PaperRDAModel','PaperRDA','rda-walkthrough']:
   self.assertIn(phrase,single)
  self.assertNotIn('<script src="rda-',single)
  release=json.loads((out/'release.json').read_text())
  self.assertEqual(release['appVersion'],'5.5.5');self.assertEqual(release['researchLibrary']['papers'],22)
  self.assertFalse(release['rdaWalkthrough']['authorPlotScalingVerified']);self.assertFalse(release['rdaWalkthrough']['RParityVerified'])
  self.assertTrue((out/'read/cheng-2023-rda-walkthrough.html').exists())

if __name__=='__main__':unittest.main(verbosity=2)
