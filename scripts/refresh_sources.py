#!/usr/bin/env python3
"""Refresh only previously approved source identities; preserve immutable old versions."""
from pathlib import Path
import json,time,hashlib,re,concurrent.futures
import requests,fitz
from refine_sources import article_license
from compile_sources import convert
ROOT=Path(__file__).resolve().parents[1]

def run():
 p=ROOT/'resources/catalog.json';catalog=json.loads(p.read_text());stamp=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());report=[]
 def check(r):
  if not r.get('bookPath'):
   return {'id':r['id'],'status':'requires-acquisition-or-rights-review','checkedAt':stamp}
  url=r['downloadURL']
  try:
   response=requests.get(url,headers={'User-Agent':'PaperLab noncommercial source version check'},timeout=(15,60));response.raise_for_status()
   raw=response.content
   if len(raw)>45000000 or not raw.startswith(b'%PDF'):raise ValueError('Unexpected original response')
   sha=hashlib.sha256(raw).hexdigest()
   if sha==r['sha256']:return {'id':r['id'],'status':'unchanged','checkedAt':stamp,'sha256':sha}
   d=fitz.open(stream=raw,filetype='pdf');lic,text=article_license(d)
   if not lic:raise ValueError('New version has no confirmed article-wide CC notice')
   doi=r.get('sourceURL','').split('doi.org/')[-1] if 'doi.org/' in r.get('sourceURL','') else ''
   front=''.join(d[i].get_text() for i in range(min(3,len(d))))
   if doi and re.sub(r'\s+','',doi).lower() not in re.sub(r'\s+','',front).lower():raise ValueError('Source identity changed')
   if not doi:raise ValueError('Changed source requires manual identity verification')
   destination=ROOT/'resources/library'/r['id']/sha[:12];destination.mkdir(parents=True,exist_ok=True)
   f=destination/'source.pdf';f.write_bytes(raw)
   prefix='library/'+r['id']+'/'+sha[:12]
   # Compile a candidate with its own version paths; preserve the active catalog
   # if conversion fails. The converter writes this exact record to provenance.
   candidate=dict(r,sha256=sha,license=lic,checkedAt=stamp,bytes=len(raw),pages=len(d),
                  bookPath=prefix+'/book.json',originalPath=prefix+'/source.pdf',epubPath=prefix+'/article.epub')
   convert(f,candidate,destination,prefix)
   r.update(candidate)
   return {'id':r['id'],'status':'new-licensed-version','checkedAt':stamp,'sha256':sha}
  except Exception as e:return {'id':r['id'],'status':'retained-last-good-version','checkedAt':stamp,'error':str(e)[:200]}
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:report=list(pool.map(check,catalog['records']))
 p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 log={'schema':'paper.source.refresh.v2','checkedAt':stamp,'records':report,'policy':'Only already approved identities automatically update; missing rights require review. Old complete copies are never deleted.'}
 (ROOT/'resources/refresh-report.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(log,ensure_ascii=False))
if __name__=='__main__':run()
