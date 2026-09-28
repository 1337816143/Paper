"""Check public source candidates. Never archive unreviewed full texts in this repository."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import json,urllib.request,urllib.error,re,hashlib
ROOT=Path(__file__).resolve().parents[1]
MAX=45_000_000

def inspect(record):
 result={'id':record['id'],'title':record['title'],'publicArchive':bool(record.get('bookPath')),'routes':[]}
 if result['publicArchive']:return result
 for url in list(dict.fromkeys(x for x in [record.get('downloadURL'),record.get('candidateURL')] if x)):
  route={'url':url,'authenticated':False};result['routes'].append(route)
  try:
   if not url.startswith('https://'):route['status']='https-required';continue
   req=urllib.request.Request(url,headers={'User-Agent':'Paper-Lab-public-access-audit/4'})
   with urllib.request.urlopen(req,timeout=25) as r:
    raw=r.read(MAX+1);route['http']=r.status;route['finalURL']=r.url
   if len(raw)>MAX:route['status']='size-limit';continue
   if b'%PDF-' not in raw[:1024]:route['status']='landing-page-not-pdf';continue
   import fitz
   doc=fitz.open(stream=raw,filetype='pdf');first=' '.join(p.get_text() for p in list(doc)[:2]);route.update(status='public-pdf-readable',pages=len(doc),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),identityCheck='DOI/title evidence retained as brief matching metadata only')
   route['detectedDOIs']=list(dict.fromkeys(re.findall(r'10\.\d{4,9}/[^\s<>]+',first)))[:6]
   route['licenseMarkers']=list(dict.fromkeys(re.findall(r'(?:creativecommons\.org/licenses/[^\s)]+|Taverne|All rights reserved)',first,re.I)))
   doc.close()
  except Exception as e:route.update(status='request-failed',error=str(e)[:250])
 return result

def main():
 p=ROOT/'resources/catalog.json';catalog=json.loads(p.read_text());records=[r for r in catalog['records'] if not r.get('bookPath')]
 with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(inspect,records))
 date=datetime.now(timezone.utc).isoformat();by={x['id']:x for x in results}
 for r in records:
  checks=by[r['id']]['routes'];r['accessCheckedAt']=date;r['accessAttempts']=checks
  readable=next((a for a in checks if a['status']=='public-pdf-readable'),None)
  if readable:
   r['accessStatus']='public-pdf-readable';r['candidateURL']=readable['url'];r['accessNote']='本轮无需登录即可读取此来源的完整PDF（'+str(readable['pages'])+'页）。全文访问和本站公开转载分别处理：可从来源下载并导入个人阅读库；未将许可待确认的原件公开镜像。'
   if r['id']=='farmsteps-2026':r['accessNote']+=' WUR官方记录标注Taverne。'
  elif not r.get('accessNote'):r['accessNote']='本站尚未保存原文。已知来源的本轮读取状态见下方；请求失败不能判断你是否有机构访问权限。可打开原站或用题名重新检索。'
 p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 report={'checkedAt':date,'authenticated':False,'noPrivateCredentialsUsed':True,'scope':'Public source reachability only, not a new public redistribution license','records':results}
 (ROOT/'resources/access-audit-v4.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('ACCESS_AUDIT='+json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
