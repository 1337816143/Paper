#!/usr/bin/env python3
"""Installed as build_reader.py. Ordinary builds use only reviewed local assets."""
from pathlib import Path
import sys,subprocess,argparse,shutil,json,hashlib,html
from package_reader import pack
ROOT=Path(__file__).resolve().parents[1]
def js(name,obj):return 'window.'+name+'='+json.dumps(obj,ensure_ascii=False).replace('<','\\u003c')+';\n'
def main():
 subprocess.run([sys.executable,str(ROOT/'scripts/build_tutorials.py'),*sys.argv[1:]],check=True)
 ap=argparse.ArgumentParser();ap.add_argument('--out',default='dist/site');ap.add_argument('--source-commit',default='local');ap.add_argument('--date');a=ap.parse_args();out=Path(a.out).resolve()
 catalog=json.loads((ROOT/'resources/catalog.json').read_text());study=json.loads((ROOT/'resources/study-v3.json').read_text());layouts=json.loads((ROOT/'resources/study-layouts.json').read_text());model=json.loads((ROOT/'vendor/translation/manifest.json').read_text())
 contracts=json.loads((ROOT/'resources/method-contracts-v54.json').read_text())
 assert len(contracts['contracts'])==21
 research=json.loads((ROOT/'resources/research-v53.json').read_text())
 assert len(research['indicatorRows'])==7 and len({r['id'] for r in research['indicatorRows']})==7
 records={r['id']:r for r in catalog['records']}
 for spec in research['papers'].values():
  source=records.get(spec.get('source'));
  if not source or not source.get('bookPath'):continue
  book=json.loads((ROOT/'resources'/source['bookPath']).read_text()); ids={b['id'] for p in book['pages'] for b in p['blocks']}
  for e in spec.get('evidence',[]):assert set(e.get('blocks',[]))<=ids, 'Missing curated source anchor'
 added_terms=json.loads((ROOT/'resources/research-terms-v53.json').read_text()); existing={t['id'] for t in study['terms']}
 study['terms'] += [t for t in added_terms if t['id'] not in existing]
 for r in catalog['records']:
  if not r.get('bookPath'):continue
  assert r.get('license',{}).get('url','').startswith('https://creativecommons.org/licenses/'),'Unlicensed source'
  p=(ROOT/'resources'/r['originalPath']).resolve();assert p.is_relative_to((ROOT/'resources/library').resolve())
  assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],'Source integrity mismatch'
 for f in model['files']:
  p=(ROOT/f['path']).resolve();assert p.is_relative_to((ROOT/'vendor/translation').resolve())
  assert p.stat().st_size==f['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],'Translation asset hash mismatch'
 shutil.copytree(ROOT/'resources/library',out/'library',dirs_exist_ok=True);shutil.copytree(ROOT/'vendor',out/'vendor',dirs_exist_ok=True)
 for n in ['reader.js','reader.css','study.js','study.css','translation-worker.js','workspace.js','workspace.css','sync.js','comfort.js','comfort.css','release.js','release.css','research.js','research.css','research-review.js','contracts.js','contracts.css','personal.js']:shutil.copyfile(ROOT/'src'/n,out/n)
 (out/'contracts-data.js').write_text(js('PAPER_CONTRACTS',contracts))
 shutil.copyfile(ROOT/'examples/paper_minilab.py',out/'examples/paper_minilab.py')
 (out/'research-data.js').write_text(js('PAPER_RESEARCH',research))
 (out/'resources.js').write_text(js('PAPER_SOURCES',catalog));(out/'study-data.js').write_text(js('PAPER_STUDY',study));(out/'study-layouts.js').write_text(js('PAPER_LAYOUTS',layouts))
 initial_datajs=(out/'data.js').read_text();data=json.loads((out/'data.json').read_text());oldversion=data['version'];digest=hashlib.sha256(oldversion.encode())
 for name in ['resources/catalog.json','resources/study-v3.json','resources/study-layouts.json','vendor/translation/manifest.json','src/reader.js','src/study.js','src/study.css','src/translation-worker.js','src/workspace.js','src/workspace.css','src/sync.js','src/comfort.js','src/comfort.css','src/release.js','src/release.css','src/sw-template.js','resources/application-release.json','resources/research-v53.json','resources/research-terms-v53.json','src/research.js','src/research.css','src/research-review.js','src/personal.js','src/contracts.js','src/contracts.css','resources/method-contracts-v54.json','examples/paper_minilab.py']:
  digest.update(name.encode());digest.update((ROOT/name).read_bytes())
 version=digest.hexdigest()[:12];data['version']=version;application=json.loads((ROOT/'resources/application-release.json').read_text());data['application']=application
 (out/'data.js').write_text(js('PAPER_DATA',data));(out/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 for p in (out/'read').glob('*.html'):
  h=p.read_text()
  for r in catalog['records']:
   for u in set(r.get('aliases',[])+[r.get('sourceURL',''),r.get('downloadURL','')]):
    if u:h=h.replace('href="'+html.escape(u,quote=True)+'"','href="../index.html#/original/'+r['id']+'"')
  p.write_text(h)
 # The lightweight HTML includes study content/tooltips, but not model weights/originals.
 single=(out/'downloads/Paper-Lab-offline.html').read_text().replace(initial_datajs,js('PAPER_DATA',data)).replace(oldversion,version)
 for css in ['reader.css','study.css','workspace.css','comfort.css','release.css','research.css','contracts.css']:single=single.replace('<link rel="stylesheet" href="'+css+'">','<style>'+(out/css).read_text()+'</style>')
 for name in ['resources.js','study-data.js','study-layouts.js','study.js','reader.js','workspace.js','sync.js','comfort.js','release.js','research-review.js','research-data.js','research.js','contracts-data.js','contracts.js','personal.js']:single=single.replace('<script src="'+name+'"></script>','<script>'+(out/name).read_text().replace('</script','<\\/script')+'</script>')
 single=single.replace('href="downloads/','href="./').replace('href="read/index.html"','href="../read/index.html"');(out/'downloads/Paper-Lab-offline.html').write_text(single)
 release=json.loads((out/'release.json').read_text());release.update(version=version,appVersion=application['version'],application=application,automaticUpdate='all-tabs-idle-safe',workspace='private-sync-v5',comfort='liquid-glass-contextual-v5',sync={'backend':'private GitHub Contents API','requiresUserAuthorization':True,'authorizationStorage':'page memory only','configurationRequired':True,'privateDataBranch':'paper-user-data','privateDataPrefix':'private/paper-sync/v5/'},glossaryExamples=sum(bool(t.get('example')) for t in study['terms']),externalPDFsCached=True,reader='reflow-study-v3',originalResourcesIncludedInFullCache=True,archivedOriginals=sum(bool(r.get('bookPath')) for r in catalog['records']),pendingOriginals=sum(not bool(r.get('bookPath')) for r in catalog['records']),originalBytes=sum(p.stat().st_size for p in (out/'library').rglob('*') if p.is_file()),studyFrameworks=len(study['frameworks']),glossaryTerms=len(study['terms']),translation={'mode':'on-device private machine translation; not a pre-reviewed full translation library','offlineModelIncluded':True,'assetBytes':model['totalBytes'],'model':model['model'],'modelRevision':model['revision']},math={'sourceEquationGroups':sum(len(x['groups']) for x in layouts.values()),'mathmlGroups':sum('mathml' in g for x in layouts.values() for g in x['groups']),'mathmlTranscriptions':sum(len(g.get('transcribedNumbers',[])) for x in layouts.values() for g in x['groups']),'sourceTextUnchanged':True})
 release['researchStudio']={'version':'5.3','paperLenses':len(research['papers']),'samplingCards':len(research['samplingCards']),'indicatorDefinitions':len(research['indicatorRows']),'feedback':'local-first plus existing authorized private GitHub sync','automaticSignIn':False,'assistantReviewPath':'private/paper-sync/v5/devices/assistant-review.json'}
 release['methodContracts']={'count':len(contracts['contracts']),'syntheticExercises':21,'masteryInferredFromVisit':False}
 release['personalEntry']={'schema':'paper.personal.entry.v1','requiresManualTokenInput':False,'requiresPrivateEntryOnNewDevice':True,'anonymousPublicAccess':False,'deviceStorage':'authenticated ciphertext plus non-extractable CryptoKey; excluded from backups','realUserTokenStatus':'selected and permission-tested automatically on private entry; not independently verified during public build'}
 release['sync']['automaticConnection']='after-user-held-private-entry'
 release['researchStudio']['automaticSignIn']=False
 release['researchStudio']['privateEntryMode']='user-held-capability'
 release['personalEntry']['provisionedByPublicBuild']=False
 release['personalEntry']['actualUserPATValidated']=False
 release['sync']['encryptedPrivateEntryStorage']='IndexedDB ciphertext with non-extractable CryptoKey; never in public assets or backups'
 (out/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2));(out/'downloads/Paper-Lab-offline.zip').unlink(missing_ok=True);(out/'sw.js').unlink(missing_ok=True)
 files=[p for p in out.rglob('*') if p.is_file() and p.name not in ['.nojekyll','data.json','offline-manifest.json'] and p.suffix!='.zip']
 large=('library/','vendor/translation/')
 core=sorted('./'+p.relative_to(out).as_posix() for p in files if not p.relative_to(out).as_posix().startswith(large))
 lib=sorted('./'+p.relative_to(out).as_posix() for p in files if p.relative_to(out).as_posix().startswith(large))
 books={r['id']:[p for p in lib if p.startswith('./'+str(Path(r['bookPath']).parent)+'/')] for r in catalog['records'] if r.get('bookPath')};books['translation-engine']=[p for p in lib if p.startswith('./vendor/translation/')]
 (out/'offline-manifest.json').write_text(json.dumps({'core':core,'library':lib,'books':books,'bytes':sum(p.stat().st_size for p in files)},ensure_ascii=False,indent=2))
 pack(out)
 # Capture compact build evidence; no notes or private translations included.
 print(json.dumps(release,ensure_ascii=False))
if __name__=='__main__':main()
