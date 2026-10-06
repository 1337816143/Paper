#!/usr/bin/env python3
"""Source-scoped annotation contracts and offline packaging; no private records."""
import hashlib,json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
DATA=read('resources/context-notes-v554.json')
DOCS={d['id']:d for p in (ROOT/'content').glob('*.json') for d in json.loads(p.read_text())}
class ContextData(unittest.TestCase):
 def test_every_annotation_is_explicit_and_source_scoped(self):
  self.assertEqual(len(DATA['entries']),15)
  self.assertEqual(hashlib.sha256(json.dumps(DATA['entries'][:12],ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),'3327ceccbf2344317b9a5565ea892dcd413e7760af57ce3cff675214b954ef9d')
  self.assertEqual(len({x['id'] for x in DATA['entries']}),15)
  for e in DATA['entries']:
   self.assertIn(e['pageId'],DOCS);self.assertRegex(e['sectionId'],r'^s\d+$')
   sec=DOCS[e['pageId']]['sections'][int(e['sectionId'][1:])]
   for p in e['phrases']:self.assertIn(p,sec[0]+' '+sec[2])
   self.assertTrue(e['sourceLocation']);self.assertTrue(e['links']);self.assertTrue(e['sections'])
   for l in e['links']:
    if l['href'].startswith('#/'):
     id=l['href'].split('/')[1]
     self.assertTrue(id in DOCS or id in {'original','lab'},l['href'])
    else:self.assertRegex(l['href'],r'^https://')
 def test_eleven_metrics_are_not_fabricated_or_mixed_with_seven(self):
  e=next(x for x in DATA['entries'] if x['id']=='liang23-eleven');self.assertEqual(len(e['details']),11)
  text=json.dumps(e,ensure_ascii=False)
  for t in ['Table2','Table1是作物','3项','15套价格','CPI','SD','persons/ha/yr','kg AI/ha/yr','QSOC','完整类别映射','没有报告用Delphi']:self.assertIn(t,text if t!='3项' else json.dumps(DOCS['liang-2023-indicator-details'],ensure_ascii=False))
  self.assertEqual(DOCS['liang-2023-indicator-details']['quiz'],[])
  self.assertEqual(DOCS['liang-2023-indicator-details']['sourceId'],'liang-2023')
  self.assertEqual(DOCS['liang-indicator-audit']['sourceId'],'liang-2022')
  self.assertIn('没有运行原作者',e['boundary'])
 def test_no_source_private_storage_or_external_dependency_mutation(self):
  js=(ROOT/'src/context-notes.js').read_text()
  for bad in ['localStorage.setItem','indexedDB','fetch(','XMLHttpRequest','eval(','innerHTML=prompt']:
   self.assertNotIn(bad,js)
  for bad in ['assistant-review.json','github_pat_','ghp_','private/paper-sync']:
   self.assertNotIn(bad,json.dumps(DATA,ensure_ascii=False))
  self.assertIn("button,a,input,textarea,select,pre,code,math,mark",js)
  self.assertIn("d.addEventListener('cancel'",js);self.assertIn("addEventListener('hashchange'",js)
 def test_assets_are_local_and_in_single_file(self):
  out=ROOT/'dist/site'
  if not (out/'context-notes.js').exists():self.skipTest('Build the context branch first')
  self.assertEqual((out/'context-notes.js').read_bytes(),(ROOT/'src/context-notes.js').read_bytes())
  self.assertEqual((out/'context-notes.css').read_bytes(),(ROOT/'src/context-notes.css').read_bytes())
  single=(out/'downloads/Paper-Lab-offline.html').read_text()
  for s in ['window.PAPER_CONTEXT=','window.PaperContext=','liang23-eleven','context-note-dialog']:self.assertIn(s,single)
  self.assertNotIn('<script src="context-notes.js"',single)
  self.assertTrue((out/'read/liang-2023-indicator-details.html').exists())
if __name__=='__main__':unittest.main(verbosity=2)
