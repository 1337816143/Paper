#!/usr/bin/env python3
"""Public reader build: stdlib only, no network. Existing tutorials stay intact."""
from pathlib import Path
import sys,subprocess,argparse,shutil,json,hashlib,re,zipfile,html
ROOT=Path(__file__).resolve().parents[1]
def main():
 subprocess.run([sys.executable,str(ROOT/'scripts/build_tutorials.py'),*sys.argv[1:]],check=True)
 ap=argparse.ArgumentParser();ap.add_argument('--out',default='dist/site');ap.add_argument('--source-commit',default='local');ap.add_argument('--date');a=ap.parse_args();out=Path(a.out).resolve()
 catalog=json.loads((ROOT/'resources/catalog.json').read_text())
 for r in catalog['records']:
  if not r.get('bookPath'):continue
  assert r.get('license',{}).get('url','').startswith('https://creativecommons.org/licenses/'),'Unlicensed source'
  p=(ROOT/'resources'/r['originalPath']).resolve();assert p.is_relative_to((ROOT/'resources/library').resolve())
  assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],'Source integrity mismatch'
 shutil.copytree(ROOT/'resources/library',out/'library',dirs_exist_ok=True);shutil.copytree(ROOT/'vendor',out/'vendor',dirs_exist_ok=True)
 for n in ['reader.js','reader.css']:shutil.copyfile(ROOT/'src'/n,out/n)
 resources='window.PAPER_SOURCES='+json.dumps(catalog,ensure_ascii=False).replace('<','\\u003c')+';\n';(out/'resources.js').write_text(resources)
 data=json.loads((out/'data.json').read_text());version=hashlib.sha256((data['version']+json.dumps(catalog,sort_keys=True)).encode()).hexdigest()[:12];data['version']=version
 datajs='window.PAPER_DATA='+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+';\n';(out/'data.js').write_text(datajs);(out/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 # Static tutorial original links also lead to the reader, never directly to a remote PDF.
 for p in (out/'read').glob('*.html'):
  h=p.read_text()
  for r in catalog['records']:
   for u in set(r.get('aliases',[])+[r.get('sourceURL',''),r.get('downloadURL','')]):
    if u:h=h.replace('href="'+html.escape(u,quote=True)+'"','href="../index.html#/original/'+r['id']+'"')
  p.write_text(h)
 # True standalone tutorial file; full originals remain in full ZIP/cache, not falsely embedded.
 single=(out/'downloads/Paper-Lab-offline.html').read_text()
 single=single.replace('<link rel="stylesheet" href="reader.css">','<style>'+(out/'reader.css').read_text()+'</style>')
 single=single.replace('<script src="resources.js"></script>','<script>'+resources+'</script>').replace('<script src="reader.js"></script>','<script>'+(out/'reader.js').read_text().replace('</script','<\\/script')+'</script>')
 single=single.replace('window.PAPER_DATA='+json.dumps(json.loads((out/'data.json').read_text()),ensure_ascii=False),'window.PAPER_DATA='+json.dumps(data,ensure_ascii=False)) if False else single
 single=single.replace('href="downloads/','href="./').replace('href="read/index.html"','href="../read/index.html"')
 (out/'downloads/Paper-Lab-offline.html').write_text(single)
 release=json.loads((out/'release.json').read_text());release.update(version=version,reader='reflow-v2',originalResourcesIncludedInFullCache=True,archivedOriginals=sum(bool(r.get('bookPath')) for r in catalog['records']),pendingOriginals=sum(not bool(r.get('bookPath')) for r in catalog['records']),originalBytes=sum(p.stat().st_size for p in (out/'library').rglob('*') if p.is_file()))
 (out/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2))
 # Rebuild archives/worker after adding originals. A duplicate full ZIP is not itself cached.
 (out/'downloads/Paper-Lab-offline.zip').unlink(missing_ok=True);(out/'sw.js').unlink(missing_ok=True)
 files=[p for p in out.rglob('*') if p.is_file() and p.name not in ['.nojekyll','data.json','offline-manifest.json']]
 core=sorted('./'+p.relative_to(out).as_posix() for p in files if not p.relative_to(out).as_posix().startswith(('library/','downloads/')))
 lib=sorted('./'+p.relative_to(out).as_posix() for p in files if p.relative_to(out).as_posix().startswith(('library/','downloads/')))
 books={r['id']:[p for p in lib if p.startswith('./'+str(Path(r['bookPath']).parent)+'/')] for r in catalog['records'] if r.get('bookPath')}
 sw=(ROOT/'src/sw-template.js').read_text().replace('__VERSION__',json.dumps(version)).replace('__CORE__',json.dumps(core)).replace('__LIBRARY__',json.dumps(lib)).replace('__BOOKS__',json.dumps(books));(out/'sw.js').write_text(sw)
 (out/'offline-manifest.json').write_text(json.dumps({'core':core,'library':lib,'books':books,'bytes':sum(p.stat().st_size for p in files)},ensure_ascii=False,indent=2))
 with zipfile.ZipFile(out/'downloads/Paper-Lab-offline.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(out.rglob('*')):
   if p.is_file() and p.suffix!='.zip':z.write(p,p.relative_to(out).as_posix())
 print(json.dumps(release,ensure_ascii=False))
if __name__=='__main__':main()
