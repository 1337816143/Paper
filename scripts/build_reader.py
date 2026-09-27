#!/usr/bin/env python3
"""Build the tutorial and licensed reflow reader without network access."""
from pathlib import Path
import sys,subprocess,argparse,shutil,json,hashlib,html
from package_reader import pack
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
 shutil.copytree(ROOT/'resources/library',out/'library',dirs_exist_ok=True)
 shutil.copytree(ROOT/'vendor',out/'vendor',dirs_exist_ok=True)
 for n in ['reader.js','reader.css']:shutil.copyfile(ROOT/'src'/n,out/n)
 resources='window.PAPER_SOURCES='+json.dumps(catalog,ensure_ascii=False).replace('<','\\u003c')+';\n';(out/'resources.js').write_text(resources)
 data=json.loads((out/'data.json').read_text());oldversion=data['version']
 version=hashlib.sha256((oldversion+json.dumps(catalog,sort_keys=True)).encode()).hexdigest()[:12];data['version']=version
 (out/'data.js').write_text('window.PAPER_DATA='+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+';\n')
 (out/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 for p in (out/'read').glob('*.html'):
  h=p.read_text()
  for r in catalog['records']:
   for u in set(r.get('aliases',[])+[r.get('sourceURL',''),r.get('downloadURL','')]):
    if u:h=h.replace('href="'+html.escape(u,quote=True)+'"','href="../index.html#/original/'+r['id']+'"')
  p.write_text(h)
 # Embed the reader interface only; original assets belong to full cache/source volumes.
 single=(out/'downloads/Paper-Lab-offline.html').read_text().replace(oldversion,version)
 single=single.replace('<link rel="stylesheet" href="reader.css">','<style>'+(out/'reader.css').read_text()+'</style>')
 single=single.replace('<script src="resources.js"></script>','<script>'+resources+'</script>')
 single=single.replace('<script src="reader.js"></script>','<script>'+(out/'reader.js').read_text().replace('</script','<\\/script')+'</script>')
 single=single.replace('href="downloads/','href="./').replace('href="read/index.html"','href="../read/index.html"')
 (out/'downloads/Paper-Lab-offline.html').write_text(single)
 release=json.loads((out/'release.json').read_text())
 release.update(version=version,externalPDFsCached=True,reader='reflow-v2',originalResourcesIncludedInFullCache=True,archivedOriginals=sum(bool(r.get('bookPath')) for r in catalog['records']),pendingOriginals=sum(not bool(r.get('bookPath')) for r in catalog['records']),originalBytes=sum(p.stat().st_size for p in (out/'library').rglob('*') if p.is_file()))
 (out/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2))
 (out/'downloads/Paper-Lab-offline.zip').unlink(missing_ok=True);(out/'sw.js').unlink(missing_ok=True)
 files=[p for p in out.rglob('*') if p.is_file() and p.name not in ['.nojekyll','data.json','offline-manifest.json']]
 core=sorted('./'+p.relative_to(out).as_posix() for p in files if not p.relative_to(out).as_posix().startswith(('library/','downloads/')))
 lib=sorted('./'+p.relative_to(out).as_posix() for p in files if p.relative_to(out).as_posix().startswith(('library/','downloads/')))
 books={r['id']:[p for p in lib if p.startswith('./'+str(Path(r['bookPath']).parent)+'/')] for r in catalog['records'] if r.get('bookPath')}
 (out/'offline-manifest.json').write_text(json.dumps({'core':core,'library':lib,'books':books,'bytes':sum(p.stat().st_size for p in files)},ensure_ascii=False,indent=2))
 pack(out)
 print(json.dumps(release,ensure_ascii=False))
if __name__=='__main__':main()
