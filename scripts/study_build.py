"""Deterministic study assets. Only catalog-matched, adaptation-permitted translations publish."""
from pathlib import Path
import hashlib,json,shutil,re
ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'https://creativecommons.org/licenses/by/4.0/','https://creativecommons.org/licenses/by-nc/4.0/','https://creativecommons.org/licenses/by-sa/4.0/','https://creativecommons.org/publicdomain/zero/1.0/'}
def read(p):return json.loads(p.read_text())
def study_assets(out,catalog):
 out=Path(out);records={r['id']:r for r in catalog['records'] if r.get('bookPath')};public=read(ROOT/'resources/translations/index.json');formula=read(ROOT/'resources/formulas/index.json')
 for r in public['records']:
  source=records[r['id']];assert r['sourceHash']==source['sha256'];license=source['license']['url'].replace('http:','https:').rstrip('/')+'/'
  assert license in ALLOWED,'Translations require adaptation permission'
  p=(ROOT/'resources'/r['path']).resolve();assert p.is_relative_to((ROOT/'resources/translations').resolve());t=read(p);assert t['sourceHash']==source['sha256'];assert t['visibility']=='public-adaptation';assert '-nd' not in t['license']['url'];b=read(ROOT/'resources'/source['bookPath']);blocks={x['id']:x for pg in b['pages'] for x in pg['blocks'] if x.get('text','').strip()}
  assert set(blocks)==set(t['blocks']),'Incomplete paragraph translation asset'
  for k,v in t['blocks'].items():
   text=re.sub(r'\s+',' ',re.sub('\u00ad'+r'\s*','',blocks[k]['text'])).strip();assert hashlib.sha256(text.encode()).hexdigest()==v['sourceTextHash'];assert v['zh'].strip();assert v['status'] in ['machine-draft','verbatim-symbols','reviewed']
  target=out/r['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 for r in formula['records']:
  source=records[r['id']];assert r['sourceHash']==source['sha256'];p=(ROOT/'resources'/r['path']).resolve();assert p.is_relative_to((ROOT/'resources/formulas').resolve());d=read(p);assert d['sourceHash']==source['sha256'];b=read(ROOT/'resources'/source['bookPath']);blocks={x['id'] for pg in b['pages'] for x in pg['blocks']}
  target=out/r['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
  for eq in d['equations']:
   assert set(eq['members']).issubset(blocks);assert eq['first'] in eq['members'];assert 1<=eq['page']<=len(b['pages']);image=(ROOT/'resources'/eq['path']).resolve();assert image.is_relative_to(p.parent) and image.suffix=='.png';to=out/eq['path'];to.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(image,to)
   if eq.get('mathML'):assert r['id']=='liang-2022' and eq['label'] in ['9','10','11','12'] and '<script' not in eq['mathML'] and 'http' not in eq['mathML'].replace('http://www.w3.org/1998/Math/MathML','')
 framework=read(ROOT/'study/frameworks.json');glossary=read(ROOT/'study/glossary.json');papers=read(ROOT/'content/papers.json');assert {p['id'] for p in papers}==set(framework['papers'])
 for p in papers:
  used=[i for g in framework['papers'][p['id']]['stages'] for i in g['details']];assert sorted(used)==list(range(len(p['sections']))),p['id']+' framework loses or duplicates original sections'
 payload={'schema':'paper.study.v3','glossary':glossary,'frameworks':framework,'formulaIndex':formula,'translationIndex':public}
 script='window.PAPER_STUDY='+json.dumps(payload,ensure_ascii=False).replace('<','\\u003c')+';\n';(out/'study-data.js').write_text(script)
 for name in ['study.js','study.css']:shutil.copyfile(ROOT/'src'/name,out/name)
 seed=hashlib.sha256(script.encode())
 for p in sorted([out/'study.js',out/'study.css',out/'reader.js',out/'reader.css',*out.glob('translations/**/*.json'),*out.glob('formulas/**/*.json')]):seed.update(p.read_bytes())
 return script,seed.hexdigest(),{'bilingualPublicOriginals':len(public['records']),'bilingualParagraphs':sum(len(read(out/r['path'])['blocks']) for r in public['records']),'sourceEquationRegions':sum(r['equationCount'] for r in formula['records']),'frameworkFirstPapers':len(framework['papers']),'glossaryTerms':len(glossary['terms']),'chineseQuality':'machine-draft-with-explicit-reviewed-overrides','NDTranslations':'personal-import-only'}
