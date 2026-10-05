#!/usr/bin/env python3
"""Installed as build_reader.py. Ordinary builds use only reviewed local assets."""
from pathlib import Path
import sys,subprocess,argparse,shutil,json,hashlib,html,csv
from package_reader import pack
ROOT=Path(__file__).resolve().parents[1]
def js(name,obj):return 'window.'+name+'='+json.dumps(obj,ensure_ascii=False).replace('<','\\u003c')+';\n'
def main():
 subprocess.run([sys.executable,str(ROOT/'scripts/build_tutorials.py'),*sys.argv[1:]],check=True)
 ap=argparse.ArgumentParser();ap.add_argument('--out',default='dist/site');ap.add_argument('--source-commit',default='local');ap.add_argument('--date');a=ap.parse_args();out=Path(a.out).resolve()
 catalog=json.loads((ROOT/'resources/catalog.json').read_text());study=json.loads((ROOT/'resources/study-v3.json').read_text());layouts=json.loads((ROOT/'resources/study-layouts.json').read_text());model=json.loads((ROOT/'vendor/translation/manifest.json').read_text())
 contracts=json.loads((ROOT/'resources/method-contracts-v54.json').read_text())
 dong_contract=json.loads((ROOT/'resources/method-contracts-dong-2026.json').read_text())
 assert dong_contract['id']=='dong-2026' and dong_contract['id'] not in contracts['contracts']
 contracts['contracts'][dong_contract['id']]=dong_contract
 assert len(contracts['contracts'])==22
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
 for n in ['reader.js','reader.css','study.js','study.css','translation-worker.js','workspace.js','workspace.css','sync.js','comfort.js','comfort.css','release.js','release.css','research.js','research.css','research-review.js','contracts.js','contracts.css','personal.js','research-library.js','research-library.css','context-notes.js','context-notes.css','research-walkthrough.js','research-walkthrough.css','rda-model.js','rda-walkthrough.js','rda-walkthrough.css','q-walkthrough.js','q-walkthrough.css']:shutil.copyfile(ROOT/'src'/n,out/n)
 library={'coverage':json.loads((ROOT/'resources/research-coverage-v55.json').read_text()),'presentation':json.loads((ROOT/'resources/research-presentation.json').read_text())}
 (out/'research-library-data.js').write_text(js('PAPER_LIBRARY',library))
 context=json.loads((ROOT/'resources/context-notes-v554.json').read_text())
 (out/'context-notes-data.js').write_text(js('PAPER_CONTEXT',context))
 rda=json.loads((ROOT/'resources/rda-walkthrough-v555.json').read_text())
 assert Path(rda['csv']).name==rda['csv'],'RDA fixture must be a local example filename'
 with (ROOT/'examples'/rda['csv']).open(newline='',encoding='utf-8') as f:
  rda['records']=[{k:(v if k=='village_id' else float(v)) for k,v in row.items()} for row in csv.DictReader(f)]
 assert len(rda['records'])==4 and len({x['village_id'] for x in rda['records']})==4
 assert hashlib.sha256((ROOT/'resources'/rda['source']['figurePath']).read_bytes()).hexdigest()==rda['source']['figureHash']
 assert records[rda['source']['paperId']]['sha256']==rda['source']['sourceHash']
 (out/'rda-walkthrough-data.js').write_text(js('PAPER_RDA',rda))
 qwalk=json.loads((ROOT/'resources/q-walkthrough-v556.json').read_text())
 assert Path(qwalk['resultsFile']).name==qwalk['resultsFile'],'Q fixture must be a local resource filename'
 qresults=json.loads((ROOT/'resources'/qwalk['resultsFile']).read_text())
 assert qresults['schema']=='paper.q.results.v1'
 by_scenario={s['id']:s['result'] for s in qresults['scenarios']}
 assert set(by_scenario)=={'baseline','reverse-p03'}
 qwalk['scenarios']=[dict(spec,result=by_scenario[spec['id']]) for spec in qwalk['scenarioDefinitions']]
 for spec in qwalk['scenarios']:
  r=spec['result'];assert r['nstat']==20 and r['npeople']==10 and r['retained_factors']==2 and r['author_data_reproduced'] is False
 assert records[qwalk['source']['paperId']]['sha256']==qwalk['source']['sourceHash']
 for fig in qwalk['source']['figures']:
  path=(ROOT/'resources'/fig['path']).resolve();assert path.is_relative_to((ROOT/'resources/library').resolve())
  assert hashlib.sha256(path.read_bytes()).hexdigest()==fig['sha256']
 (out/'q-walkthrough-data.js').write_text(js('PAPER_Q',qwalk))
 (out/'contracts-data.js').write_text(js('PAPER_CONTRACTS',contracts))
 shutil.copyfile(ROOT/'examples/paper_minilab.py',out/'examples/paper_minilab.py')
 (out/'research-data.js').write_text(js('PAPER_RESEARCH',research))
 (out/'resources.js').write_text(js('PAPER_SOURCES',catalog));(out/'study-data.js').write_text(js('PAPER_STUDY',study));(out/'study-layouts.js').write_text(js('PAPER_LAYOUTS',layouts))
 initial_datajs=(out/'data.js').read_text();data=json.loads((out/'data.json').read_text());oldversion=data['version'];digest=hashlib.sha256(oldversion.encode())
 for name in ['resources/catalog.json','resources/study-v3.json','resources/study-layouts.json','vendor/translation/manifest.json','src/reader.js','src/study.js','src/study.css','src/translation-worker.js','src/workspace.js','src/workspace.css','src/sync.js','src/comfort.js','src/comfort.css','src/release.js','src/release.css','src/sw-template.js','resources/application-release.json','resources/research-v53.json','resources/research-terms-v53.json','src/research.js','src/research.css','src/research-review.js','src/personal.js','src/contracts.js','src/contracts.css','resources/method-contracts-v54.json','resources/method-contracts-dong-2026.json','examples/paper_minilab.py','src/research-library.js','src/research-library.css','resources/research-coverage-v55.json','resources/research-presentation.json','resources/context-notes-v554.json','src/context-notes.js','src/context-notes.css','src/research-walkthrough.js','src/research-walkthrough.css','resources/rda-walkthrough-v555.json','src/rda-model.js','src/rda-walkthrough.js','src/rda-walkthrough.css','resources/q-walkthrough-v556.json','resources/q-results-v556.json','src/q-walkthrough.js','src/q-walkthrough.css']:
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
 for css in ['reader.css','study.css','workspace.css','comfort.css','release.css','research.css','contracts.css','research-library.css','context-notes.css','research-walkthrough.css','rda-walkthrough.css','q-walkthrough.css']:single=single.replace('<link rel="stylesheet" href="'+css+'">','<style>'+(out/css).read_text()+'</style>')
 for name in ['resources.js','study-data.js','study-layouts.js','study.js','reader.js','workspace.js','sync.js','comfort.js','release.js','research-review.js','research-data.js','research.js','contracts-data.js','contracts.js','personal.js','research-library-data.js','research-library.js','context-notes-data.js','context-notes.js','research-walkthrough.js','rda-walkthrough-data.js','rda-model.js','rda-walkthrough.js','q-walkthrough-data.js','q-walkthrough.js']:single=single.replace('<script src="'+name+'"></script>','<script>'+(out/name).read_text().replace('</script','<\\/script')+'</script>')
 single=single.replace('href="downloads/','href="./').replace('href="read/index.html"','href="../read/index.html"');(out/'downloads/Paper-Lab-offline.html').write_text(single)
 release=json.loads((out/'release.json').read_text());release.update(version=version,appVersion=application['version'],application=application,automaticUpdate='all-tabs-idle-safe',workspace='private-sync-v5',comfort='liquid-glass-contextual-v5',sync={'backend':'private GitHub Contents API','requiresUserAuthorization':True,'authorizationStorage':'page memory only','configurationRequired':True,'privateDataBranch':'paper-user-data','privateDataPrefix':'private/paper-sync/v5/'},glossaryExamples=sum(bool(t.get('example')) for t in study['terms']),externalPDFsCached=True,reader='reflow-study-v3',originalResourcesIncludedInFullCache=True,archivedOriginals=sum(bool(r.get('bookPath')) for r in catalog['records']),pendingOriginals=sum(not bool(r.get('bookPath')) for r in catalog['records']),originalBytes=sum(p.stat().st_size for p in (out/'library').rglob('*') if p.is_file()),studyFrameworks=len(study['frameworks']),glossaryTerms=len(study['terms']),translation={'mode':'on-device private machine translation; not a pre-reviewed full translation library','offlineModelIncluded':True,'assetBytes':model['totalBytes'],'model':model['model'],'modelRevision':model['revision']},math={'sourceEquationGroups':sum(len(x['groups']) for x in layouts.values()),'mathmlGroups':sum('mathml' in g for x in layouts.values() for g in x['groups']),'mathmlTranscriptions':sum(len(g.get('transcribedNumbers',[])) for x in layouts.values() for g in x['groups']),'sourceTextUnchanged':True})
 release['contextualExplanations']={'version':'5.5.4','annotations':len(context['entries']),'paperPages':len({e['pageId'] for e in context['entries']}),'manualSourceScope':True,'mainWalkthrough':'synthetic-four-farm-input-to-distance','authorDataReproduction':False}
 release['rdaWalkthrough']={'version':'5.5.5','guide':rda['guideId'],'syntheticRecords':len(rda['records']),'responses':2,'predictors':2,'sourceFigureUnchanged':True,'authorPlotScalingVerified':False,'RParityVerified':False}
 release['qWalkthrough']={'version':'5.5.6','guide':qwalk['guideId'],'syntheticStatements':20,'syntheticPeople':10,'retainedFactors':2,'scenarios':2,'sourceFiguresUnchanged':True,'authorResultsReproduced':False,'authorScalingVerified':False,'referenceComparison':'pinned-R-required-in-CI'}
 release['researchStudio']={'version':'5.3','paperLenses':len(research['papers']),'samplingCards':len(research['samplingCards']),'indicatorDefinitions':len(research['indicatorRows']),'feedback':'local-first plus existing authorized private GitHub sync','automaticSignIn':False,'assistantReviewPath':'private/paper-sync/v5/devices/assistant-review.json'}
 release['methodContracts']={'count':len(contracts['contracts']),'syntheticExercises':len(contracts['contracts']),'masteryInferredFromVisit':False}
 release['researchLibrary']={'version':'5.5','papers':len(library['coverage']['papers']),'assessmentRequired':False,'coverageIsReaderScore':False,'legacyStoragePreserved':True}
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
