#!/usr/bin/env python3
"""Acquire allowlisted public research sources; never publish a PDF without an explicit CC license.
Raw files without verified redistribution terms stay temporary and are discarded.
"""
import json, re, time, hashlib, concurrent.futures, argparse
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
import fitz

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'resources'; OUT.mkdir(exist_ok=True)
PORTAL='https://research.wur.nl/en/publications/'
SLUGS={
 'liang-2022':'identifying-exemplary-sustainable-cropping-systems-using-a-positi',
 'liang-2023':'designing-diversified-crop-rotations-to-advance-sustainability-a-',
 'farmsteps-2026':'farmsteps-a-model-for-spatial-temporal-exploration-of-diversified',
 'cheng-2023':'farmers-perceive-diminishing-ecosystem-services-but-overlook-dis-',
 'cheng-2025':'stakeholder-perspectives-on-ecosystem-services-in-agricultural-la',
 'xu-2024':'comparing-the-sustainability-of-smallholder-and-business-farms-in',
 'farmdesign-2012':'multi-objective-optimization-and-design-of-farming-systems',
 'landscape-2018':'exploring-ecosystem-services-trade-offs-in-agricultural-landscapes',
 'novotny-2024':'exploring-nutrient-sensitive-landscape-configurations-for-rural-c',
 'ditzler-2019':'a-model-to-examine-farm-household-trade-offs-and-synergies-with-an',
 'qu-2025':'improved-manure-management-moves-trade-off-and-synergy-relationsh',
 'breure-2024':'a-systematic-review-of-the-methodology-of-trade-off-analysis-in-a',
 'toorop-2023':'analyzing-antifragility-among-smallholder-farmers-in-bihar-india-a',
 'verdouw-2021':'digital-twins-in-smart-farming',
 'liang-thesis':'exploring-sustainable-and-diversified-crop-production-systems-for',
 'cheng-thesis':'multifunctional-and-stakeholder-informed-agricultural-landscape-r',
 'xu-thesis':'exploring-options-for-a-more-sustainable-crop-production-on-the-n',
}
HEADERS={'User-Agent':'PaperLab-ResearchReader/2.0 (noncommercial scholarly library; public sources only)'}
ALLOWED=('edepot.wur.nl','research.wur.nl','www.nature.com','nature.com','link.springer.com','link.springer.rp?','www.cambridge.org','pmc.ncbi.nlm.nih.gov','www.sciencedirect.com','api.elsevier.com','api.crossref.org','europepmc.org','www.ebi.ac.uk')

def get(url):
 h=urlparse(url).hostname or ''
 if not any(h==d or h.endswith('.'+d) for d in ALLOWED): raise ValueError('Host not allowlisted: '+h)
 r=requests.get(url,headers=HEADERS,timeout=(15,50))
 r.raise_for_status()
 if len(r.content)>40_000_000: raise ValueError('Resource exceeds 40MB')
 return r

def license_from_pdf(doc):
 text='\n'.join(p.get_text() for p in doc)
 # Do not count references to CC licenses in the middle of scientific text as an article license.
 # Look only at first two and last two pages, with an open-access/copyright context.
 boundary='\n'.join(doc[i].get_text() for i in sorted(set([0,min(1,len(doc)-1),max(0,len(doc)-2),len(doc)-1])))
 compact=re.sub(r'\s+',' ',boundary)
 matches=list(re.finditer(r'creativecommons\.org/licenses/(by(?:-nc)?(?:-nd|-sa)?)/(\d\.\d)',compact,re.I))
 for m in matches:
  around=compact[max(0,m.start()-500):m.end()+300]
  if re.search(r'open.access|license|licence|creative commons|author\(s\)|authors|copyright',around,re.I):
   key=m.group(1).lower(); version=m.group(2)
   return {'name':'CC '+key.upper()+' '+version,'url':f'https://creativecommons.org/licenses/{key}/{version}/','evidence':around[:800],'pageScope':'first/last pages of acquired article'},text
 return None,text

def acquire(p):
 ident=p['id']; current=OUT/ident/'source.pdf'; record={'id':ident,'title':p.get('en',p['title']),'citation':p.get('citation',''),'sourceURL':p.get('url',''),'checkedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'unavailable','attempts':[]}
 candidates=[]
 if p.get('pdf'): candidates.append(p['pdf'])
 if ident=='xu-data-2024': candidates.extend(['https://pmc.ncbi.nlm.nih.gov/articles/PMC10964062/pdf/main.pdf','https://europepmc.org/articles/PMC10964062?pdf=render'])
 url=p.get('url','')
 if '10.1007/' in url: candidates.append('https://link.springer.com/content/pdf/'+url.split('doi.org/')[-1]+'.pdf')
 if '10.1038/' in url: candidates.append('https://www.nature.com/articles/'+url.rsplit('/',1)[-1]+'.pdf')
 if ident in SLUGS:
  portal=PORTAL+SLUGS[ident]+'/'
  try:
   page=get(portal).text
   candidates += [x.replace('&amp;','&') for x in re.findall(r'https?://edepot\.wur\.nl/\d+',page)]
   record['metadataURL']=portal
  except Exception as e: record['attempts'].append({'url':portal,'error':str(e)[:140]})
 # Resolve DOI for official download links, when needed.
 if not candidates or ident in ('toorop-2023','mixed-2026'):
  doi=url.split('doi.org/')[-1]
  try:
   cross=get('https://api.crossref.org/works/'+doi).json()['message']
   record['metadataTitle']=cross.get('title',[''])[0]
   for link in cross.get('link',[]):
    if link.get('content-type')=='application/pdf': candidates.append(link['URL'])
   landing=cross.get('resource',{}).get('primary',{}).get('URL')
   if landing:
    html=get(landing).text
    for match in re.findall(r'(?:href|content)=[\"\']([^\"\']+\.pdf(?:\?[^\"\']*)?)[\"\']',html,re.I): candidates.append(urljoin(landing,match.replace('&amp;','&')))
  except Exception as e: record['attempts'].append({'url':url,'error':str(e)[:140]})
 for pdfurl in dict.fromkeys(candidates):
  try:
   res=get(pdfurl)
   if not res.content.startswith(b'%PDF'): raise ValueError('Not a PDF response')
   doc=fitz.open(stream=res.content,filetype='pdf')
   if len(doc)==0 or len(doc)>400: raise ValueError('Unexpected page count')
   lic,text=license_from_pdf(doc)
   if not lic:
    record.update(status='rights-review',candidateURL=pdfurl,pages=len(doc),reason='No explicit article-wide CC redistribution license found; file not stored.')
    record['attempts'].append({'url':pdfurl,'error':'license-not-confirmed'})
    continue
   # Identity gate: DOI must occur in first pages except for data paper whose canonical entry is PMC.
   doi=url.split('doi.org/')[-1] if 'doi.org/' in url else ''
   front=' '.join(doc[i].get_text() for i in range(min(3,len(doc))))
   if doi and re.sub(r'\s+','',doi).lower() not in re.sub(r'\s+','',front).lower(): raise ValueError('DOI not found in front matter; identity review required')
   dest=OUT/ident; dest.mkdir(exist_ok=True)
   (dest/'source.pdf').write_bytes(res.content)
   record.update(status='licensed',downloadURL=pdfurl,license=lic,pages=len(doc),sha256=hashlib.sha256(res.content).hexdigest(),bytes=len(res.content),textCharacters=len(text))
   (dest/'provenance.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
   print(ident,record['status'],lic['name'],len(doc),flush=True)
   return record
  except Exception as e: record['attempts'].append({'url':pdfurl,'error':str(e)[:180]})
 print(ident,record['status'],flush=True)
 return record

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--ids',default='');args=ap.parse_args()
 papers=json.loads((ROOT/'content/papers.json').read_text())
 if args.ids: papers=[p for p in papers if p['id'] in args.ids.split(',')]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: records=list(pool.map(acquire,papers))
 (OUT/'acquisition.json').write_text(json.dumps({'schema':'paper.sources.acquisition.v1','records':records},ensure_ascii=False,indent=2)+'\n')
 print('Licensed sources:',sum(r['status']=='licensed' for r in records),'/',len(records))
