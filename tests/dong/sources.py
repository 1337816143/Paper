#!/usr/bin/env python3
"""Immutable legacy identity, scientific scope and actual build contracts."""
from pathlib import Path
import hashlib,json,re,unittest
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads((ROOT/p).read_text())
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
DOCS={d['id']:d for f in (ROOT/'content').glob('*.json') for d in json.loads(f.read_text())}
class Sources(unittest.TestCase):
 def test_preserved_prose_and_annotation_prefix(self):
  contract=read('tests/dong/append-only-contract.json')
  old=read('tests/annual-balance/source-baseline.json')['documents']
  for id,n in [('dong-2026',9),('dong-2026-ledger',6)]:
   d=DOCS[id];c=contract['documents'][id]
   self.assertEqual(c['originalSectionCount'],n);self.assertEqual(len(d['sections']),n+1)
   self.assertEqual(digest(d['sections'][:n]),old[id]['sectionsSha256'])
   self.assertEqual(c['originalSectionsSha256'],old[id]['sectionsSha256'])
   self.assertEqual(digest(d.get('quiz',[])),old[id]['quizSha256'])
   self.assertEqual([s[0] for s in d['sections'][n:]],c['appendedTitles'])
  for f in ['src/app.js','scripts/build_tutorials.py']:
   t=(ROOT/f).read_text();self.assertIn('dong-source-update',t);self.assertIn('不再表示当前状态',t)
 def test_catalog_exact_three_field_addendum_and_source_identity(self):
  catalog=read('resources/catalog.json');c=read('tests/dong/append-only-contract.json')
  d=next(d for d in catalog['records'] if d['id']=='dong-2026');m=d['sourceIdentityMapping']
  self.assertEqual(d['pages'],13);self.assertEqual(d['verifiedPDFPages'],13)
  self.assertEqual(d['sha256'],'cf0b6c31874d95e945d7e3926ba7c64806d719d2aede3b2c13fdb6658aed2b86')
  self.assertEqual(d['status'],'rights-review');self.assertIn(c['catalogOriginalReason'],d['reason'])
  self.assertEqual(m['repositoryWrappedPDF']['pages'],14);self.assertEqual(m['repositoryWrappedPDF']['containerToPrintedPageOffset'],1)
  self.assertEqual(m['repositoryWrappedPDF']['sha256'],'f88fb273a641a0c3dcfe8b190c054809c600b670144285541658a2bab67ec79b')
  self.assertEqual(m['supplementaryDOCX']['sha256'],'e579a1a6791b98f8fab5389781465cbf4a9a4f255be46996b6f02491e630bdde')
  self.assertFalse(m['supplementaryDOCX']['fixedPagination']);self.assertEqual(m['supplementaryLocalRender']['pages'],35)
  self.assertEqual(m['supplementaryDOCX']['sourceURL'],'https://ars.els-cdn.com/content/image/1-s2.0-S0308521X26000636-mmc1.docx')
  d['reason']=c['catalogOriginalReason'];del d['sourceStatusUpdatedAt'];del d['sourceIdentityMapping']
  self.assertEqual(hashlib.sha256((json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest(),c['catalogOriginalSHA256'])
 def test_new_guide_explicit_limits_and_source_scoped_explanations(self):
  d=DOCS['dong-si-boundary-walkthrough'];self.assertEqual(len(d['sections']),7);self.assertEqual(d['quiz'],[])
  self.assertEqual(d['sourceId'],'dong-2026');s=json.dumps(d,ensure_ascii=False)
  for item in ['268','314','436','0.7','398','NH₃','N₂O','NO','S47','S48','S49','合成','原始']:
   self.assertIn(item,s)
  for section in d['sections']:self.assertEqual(len(section),4);self.assertTrue(section[3])
  e=read('resources/context-notes-v554.json')['entries']
  self.assertEqual(digest(e[:15]),'98ab12d5f20e568b4ef3355ae7bc0729de8f8c71775e9bffd48eb321d58fd370')
  self.assertEqual(len(e),18)
  for x in e[-3:]:
   self.assertEqual(x['pageId'],d['id']);self.assertTrue(any('mmc1.docx' in link['href'] for link in x['links']))
 def test_no_remote_data_or_private_storage_added(self):
  for name in ['dong-boundary.js','dong-boundary-model.js']:
   code=(ROOT/'src'/name).read_text()
   for forbidden in ['fetch(','XMLHttpRequest','localStorage','sessionStorage','indexedDB','eval(','private/paper-sync','github_pat_','ghp_']:
    self.assertNotIn(forbidden,code)
  self.assertIn('PaperDong?.isBusy', (ROOT/'src/release.js').read_text())
 def test_build_bytes_single_file_and_prior_root_fix(self):
  out=ROOT/'dist/site'
  for f in ['dong-boundary.js','dong-boundary-model.js','dong-boundary.css']:
   self.assertEqual((out/f).read_bytes(),(ROOT/'src'/f).read_bytes())
  self.assertEqual((out/'examples/dong_boundary_lab.py').read_bytes(),(ROOT/'examples/dong_boundary_lab.py').read_bytes())
  r=json.loads((out/'release.json').read_text());self.assertEqual(r['appVersion'],'5.5.14')
  self.assertEqual(r['documents'],129) if 'documents' in r else None
  self.assertTrue(r['dongBoundary']['syntheticOnly']);self.assertFalse(r['dongBoundary']['authorResultsReproduced'])
  self.assertEqual(r['dongBoundary']['legacyMainSections'],9);self.assertEqual(r['dongBoundary']['legacyLedgerSections'],6)
  single=(out/'downloads/Paper-Lab-offline.html').read_text()
  for token in ['PaperDongModel','g.PaperDong=','data-paper-root="../"','body.single a[download]:not([data-paper-manifest])','href="../offline-manifest.json"']:
   self.assertIn(token,single)
  self.assertNotRegex(single,r'(?:src|href)="dong-boundary[^" ]*\.(?:js|css)"')
  for id,indices in [('dong-2026',[4,5,6,8]),('dong-2026-ledger',[3,5]),('explanation-roadmap',[25])]:
   html=(out/'read'/f'{id}.html').read_text();self.assertEqual(html.count('class="notice dong-source-update"'),len(indices))
   if id!='explanation-roadmap':
    n=4 if id=='dong-2026' else 3;section=re.search(r'<section class="reader" id="s'+str(n)+r'">(.*?)</section>',html).group(1)
    for t in ['268配262','314分别配218、187、174','不能据此把268逐项相除']:self.assertIn(t,section)
    self.assertLess(section.index('dong-source-update'),section.index('class="prose"'))
if __name__=='__main__':unittest.main()
