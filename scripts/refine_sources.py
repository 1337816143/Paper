#!/usr/bin/env python3
import acquire_sources as base
import json,re,time,concurrent.futures
base.SLUGS.update({'ditzler-2019':'a-model-to-examine-farm-household-trade-offs-and-synergies-with-a','landscape-2018':'exploring-ecosystem-services-trade-offs-in-agricultural-landscape','xu-data-2024':'survey-data-on-livelihoods-and-inputs-and-outputs-of-crop-product'})
base.ALLOWED=tuple(x for x in base.ALLOWED if '?' not in x)+('linkinghub.elsevier.com','media.springernature.com','www.ncbi.nlm.nih.gov','ftp.ncbi.nlm.nih.gov')
original=base.license_from_pdf

def article_license(doc):
 lic,text=original(doc)
 if lic:return lic,text
 for i,p in enumerate(doc):
  t=re.sub(r'\s+',' ',p.get_text())
  # Explicit article-wide statement, not an incidental reference to licensing.
  patterns=[r'This (?:is an open access article|article is licensed under)[\s\S]{0,650}',r'Open Access[\s\S]{0,30}This article[\s\S]{0,650}']
  for pat in patterns:
   m=re.search(pat,t,re.I)
   if not m:continue
   fragment=m.group(0);flat=re.sub(r'\s+','',fragment)
   url=re.search(r'creativecommons\.org/licenses/(by(?:-nc)?(?:-nd|-sa)?)/(\d\.\d)',flat,re.I)
   if url:key,ver=url.group(1).lower(),url.group(2)
   else:
    if not re.search(r'Creative Commons Attribution|CC BY',fragment,re.I):continue
    key='by'
    if re.search('NonCommercial|Non-Commercial|BY-NC',fragment,re.I):key+='-nc'
    if re.search('NoDerivatives|No-Derivatives|NC-ND|BY-ND',fragment,re.I):key+='-nd'
    if re.search('ShareAlike|Share-Alike|BY-SA',fragment,re.I):key+='-sa'
    v=re.search(r'\b(4\.0|3\.0|2\.5)\b',fragment)
    if not v:continue
    ver=v.group(1)
   return {'name':'CC '+key.upper()+' '+ver,'url':f'https://creativecommons.org/licenses/{key}/{ver}/','evidence':fragment,'page':i+1},text
 return None,text
base.license_from_pdf=article_license
if __name__=='__main__':
 papers=json.loads((base.ROOT/'content/papers.json').read_text())
 direct={'farmsteps-2026':'713946','cheng-2023':'640654','cheng-2025':'680477','qu-2025':'677886','breure-2024':'652132'}
 for p in papers:
  if p['id'] in direct:p['pdf']='https://edepot.wur.nl/'+direct[p['id']]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(base.acquire,papers))
 (base.OUT/'acquisition.json').write_text(json.dumps({'schema':'paper.sources.acquisition.v1','records':records},ensure_ascii=False,indent=2)+'\n')
 print('Licensed:',sum(r['status']=='licensed' for r in records))
