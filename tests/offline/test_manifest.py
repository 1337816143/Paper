"""Exact final-tree/portable archive contract; no network and no private data."""
from pathlib import Path
import hashlib, json, shutil, sys, tempfile, unittest, zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from seal_site import seal, check, canonical_worker, PIN, sha

class ManifestTests(unittest.TestCase):
 def test_final_tree_and_downloads(self):
  out=ROOT/'dist/site';report=check(out);m=json.loads((out/'offline-manifest.json').read_text())
  paths={r['url'] for r in m['resources']}
  self.assertIn('./data.json',paths);self.assertIn('./.nojekyll',paths);self.assertIn('./offline-downloads.js',paths)
  self.assertIn('offline-downloads.js',(out/'index.html').read_text());self.assertIn('../offline-downloads.js',(out/'downloads/index.html').read_text())
  self.assertIn('verified-fetch-to-blob',(out/'downloads/Paper-Lab-offline.html').read_text())
  self.assertEqual({p.relative_to(out).as_posix() for p in out.rglob('*.zip')},{p[2:] for p in paths if p.endswith('.zip')})
  self.assertGreaterEqual(len(json.loads((out/'data.json').read_text())['documents']),123)
  for p in out.glob('*-validation.json'):self.assertIn('./'+p.name,paths)
  self.assertEqual(len(report['files']),len(m['resources'])+2)
 def test_portable_archives_are_independently_sealed(self):
  out=ROOT/'dist/site';packs=list((out/'downloads').glob('*.zip'));members={}
  for p in packs:
   with zipfile.ZipFile(p) as z:
    self.assertIsNone(z.testzip())
    for n in z.namelist():
     self.assertNotIn(n,members,'Duplicate archive member');members[n]=p
  with zipfile.ZipFile(out/'downloads/Paper-Lab-offline.zip') as z:
   raw=z.read('offline-manifest.json');m=json.loads(raw);sw=z.read('sw.js')
  self.assertIn('offline-downloads.js',members)
  with zipfile.ZipFile(out/'downloads/Paper-Lab-offline.zip') as z:self.assertIn('../offline-downloads.js',z.read('downloads/index.html').decode())
  self.assertEqual(m['mode'],'portable-extracted');self.assertEqual(PIN.search(sw).group(1).decode(),sha(raw))
  self.assertEqual(sha(canonical_worker(sw)),m['controls'][0]['canonicalSha256'])
  self.assertFalse(any(r['url'].endswith('.zip') for r in m['resources']))
  self.assertEqual(set(members),{r['url'][2:] for r in m['resources']}|{'sw.js','offline-manifest.json'})
  for r in m['resources']:
   with zipfile.ZipFile(members[r['url'][2:]]) as z:data=z.read(r['url'][2:])
   self.assertEqual(len(data),r['bytes']);self.assertEqual(sha(data),r['sha256'])
 def test_fail_closed_on_changes_and_unsealed_reports(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'release.json').write_text(json.dumps({'version':'fixture','sourceCommit':'synthetic'}));(p/'index.html').write_text('same size');seal(p)
   original=(p/'index.html').read_bytes();(p/'index.html').write_bytes(b'wrongtext')
   with self.assertRaises(AssertionError):check(p)
   (p/'index.html').write_bytes(original);(p/'new-validation.json').write_text('{}')
   with self.assertRaises(AssertionError):check(p)
   seal(p);self.assertIn('./new-validation.json',{r['url'] for r in json.loads((p/'offline-manifest.json').read_text())['resources']})
   before=(p/'sw.js').read_bytes()
   for changed in [before.replace(b'use strict',b'use Strict',1),before.replace(b'\n',b'\r\n'),before+b"\nconst MANIFEST_SHA='"+b'0'*64+b"';",before.replace(PIN.search(before).group(1),b'0'*64,1),before+b'\xff']:
    (p/'sw.js').write_bytes(changed)
    with self.assertRaises((AssertionError,ValueError)):check(p)
   (p/'sw.js').write_bytes(before);check(p)
   with self.assertRaises(AssertionError):check(p,p/'self-referential-audit.json')

if __name__=='__main__':unittest.main()
