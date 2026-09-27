#!/usr/bin/env python3
"""Technical PDF format conversion, not editing/translation. No OCR. Keep exact originals.
Build reads precompiled output without PyMuPDF; this converter runs only on acquisition/refresh.
"""
from pathlib import Path
import json,hashlib,re,shutil,html,zipfile,collections
import fitz
ROOT=Path(__file__).resolve().parents[1]
def jw(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def render(page,rect,path,scale):page.get_pixmap(matrix=fitz.Matrix(scale,scale),clip=fitz.Rect(rect)&page.rect,alpha=False).save(path)
def convert(pdf,record,out,prefix):
 raw=pdf.read_bytes();sha=hashlib.sha256(raw).hexdigest();out.mkdir(parents=True,exist_ok=True);(out/'source.pdf').write_bytes(raw);d=fitz.open(pdf)
 b={'schema':'paper.original.v2','id':record['id'],'lessonId':record.get('lessonId',record['id']),'title':record['title'],'citation':record.get('citation',''),'origin':record.get('sourceURL',''),'sourceHash':sha,'license':record.get('license'),'originalPath':prefix+'/source.pdf','originalType':'pdf','epubPath':prefix+'/article.epub','convertedBy':'Technical format conversion; all text blocks and original page images; no editorial rewrite','pages':[]};rawtext=[];kept=[];graphics=0
 for pi,page in enumerate(d):
  blocks=[];textblocks=[];images=[];fonts=collections.Counter()
  for bi,x in enumerate(page.get_text('dict')['blocks']):
   if x['type']==0:
    text='\n'.join(''.join(s['text'] for s in l['spans']) for l in x['lines']).strip();rawtext.append(text)
    if not text:continue
    spans=[s for l in x['lines'] for s in l['spans']]
    for s in spans:fonts[round(s['size'],1)]+=len(s['text'])
    textblocks.append((bi,x,text,spans))
   elif x['type']==1:
    r=fitz.Rect(x['bbox'])
    if r.width>28 and r.height>18:images.append(r)
  try:
   for r in page.cluster_drawings(x_tolerance=12,y_tolerance=12):
    r=fitz.Rect(r)
    if r.width>90 and r.height>55 and r.get_area()<page.rect.get_area()*.93 and not any((r&p).get_area()/max(1,min(r.get_area(),p.get_area()))>.75 for p in images):images.append(r)
  except Exception:pass
  size=fonts.most_common(1)[0][0] if fonts else 10
  for bi,x,text,spans in textblocks:
   if len(text)<220 and re.search(r'\(\d+[a-z]?\)\s*$',text) and re.search('[=∑√∫−×≤≥]',text):images.append(fitz.Rect(x['bbox']))
  visual=[]
  for j,r in enumerate(images):
   r=(r+(-2,-2,2,2))&page.rect;name=f'p{pi+1}-figure{j+1}.png';render(page,r,out/name,2)
   visual.append((r,{'id':f'p{pi+1}-figure{j+1}','kind':'image','path':prefix+'/'+name,'alt':f'Original source page {pi+1}, graphic {j+1}','caption':f'原文第{pi+1}页图形 / 公式切片；完整原排版见本页末核对图'}));graphics+=1
  used=set()
  for bi,x,text,spans in textblocks:
   r=fitz.Rect(x['bbox'])
   if re.match(r'(?:Fig(?:ure)?\.?|Table)\s*\d',text,re.I):
    for j,(vr,obj) in enumerate(visual):
     if j not in used and vr.x0<r.x1 and vr.x1>r.x0 and vr.y1<=r.y0+12 and r.y0-vr.y1<100:blocks.append(obj);used.add(j)
   largest=max(s['size'] for s in spans) if spans else size
   heading=len(text)<190 and (bool(re.match(r'^\d+(?:\.\d+)*\.?\s+[A-Z]',text)) or text.lower() in ['abstract','references','conclusions','acknowledgements','acknowledgments','data availability'] or largest>size*1.28)
   blocks.append({'id':f'p{pi+1}-b{bi}-'+hashlib.sha256(text.encode()).hexdigest()[:7],'kind':'heading' if heading else 'paragraph','text':text,'bbox':list(x['bbox'])});kept.append(text)
  blocks += [obj for j,(_,obj) in enumerate(visual) if j not in used]
  snapshot=f'page-{pi+1}.png';render(page,page.rect,out/snapshot,1.65);b['pages'].append({'number':pi+1,'blocks':blocks,'snapshot':prefix+'/'+snapshot})
 norm=lambda s:re.sub(r'\s+','',s).replace('\xad','')
 assert norm(''.join(rawtext))==norm(''.join(kept)),record['id']+' text coverage mismatch'
 b['audit']={'pageCount':len(d),'pageSnapshots':len(b['pages']),'allTextBlocksRetained':True,'textCharacters':len(''.join(kept)),'normalizedCharacterCoverage':1.0,'graphicSnippets':graphics,'sourceSHA256':sha,'manualCharacterReview':False,'limitations':'Reading order, tables and equations can require visual checking. Full-page images and original PDF preserve complete visual content.'}
 jw(out/'book.json',b);jw(out/'provenance.json',record);(out/'source-extracted.txt').write_text('\n\n'.join(rawtext));epub(b,out);return b

def epub(b,out):
 e=html.escape;items=[];spine=[];pages=[]
 for p in b['pages']:
  body=[]
  for x in p['blocks']:
   if x['kind']=='image':body.append('<figure><img src="'+e(Path(x['path']).name)+'" alt="'+e(x['alt'])+'"/><figcaption>'+e(x['caption'])+'</figcaption></figure>')
   else:
    tag='h2' if x['kind']=='heading' else 'p';body.append(f'<{tag} id="{x["id"]}">'+e(re.sub(r'\s+',' ',x['text']))+f'</{tag}>')
  body.append('<h3>Original layout for visual verification</h3><img src="'+Path(p['snapshot']).name+'" alt="Complete source page"/>')
  fn=f'page{p["number"]}.xhtml';pages.append((fn,'<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" lang="en"><head><title>Source page '+str(p['number'])+'</title><style>body{font-family:serif;line-height:1.7}img{max-width:100%;height:auto}p{margin-bottom:1em}</style></head><body>'+''.join(body)+'</body></html>'));items.append(f'<item id="p{p["number"]}" href="{fn}" media-type="application/xhtml+xml"/>');spine.append(f'<itemref idref="p{p["number"]}"/>')
 images=sorted(out.glob('*.png'))
 for i,f in enumerate(images):items.append(f'<item id="img{i}" href="{f.name}" media-type="image/png"/>')
 items.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
 nav='<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Contents</title></head><body><h1>'+e(b['title'])+'</h1><p>'+e(b.get('citation',''))+'</p><p>'+e((b.get('license') or {}).get('name','Personal local copy'))+'</p><nav epub:type="toc"><ol>'+''.join(f'<li><a href="{fn}">{fn}</a></li>' for fn,_ in pages)+'</ol></nav></body></html>'
 opf='<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="bookid">urn:sha256:'+b['sourceHash']+'</dc:identifier><dc:title>'+e(b['title'])+'</dc:title><dc:language>en</dc:language><dc:source>'+e(b.get('origin',''))+'</dc:source><dc:rights>'+e((b.get('license') or {}).get('name','Personal local copy'))+'</dc:rights><meta property="dcterms:modified">2026-09-28T00:00:00Z</meta></metadata><manifest>'+''.join(items)+'</manifest><spine>'+''.join(spine)+'</spine></package>'
 with zipfile.ZipFile(out/'article.epub','w') as z:
  z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED);z.writestr('META-INF/container.xml','<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>');z.writestr('OEBPS/content.opf',opf);z.writestr('OEBPS/nav.xhtml',nav)
  for fn,data in pages:z.writestr('OEBPS/'+fn,data,compress_type=zipfile.ZIP_DEFLATED)
  for f in images:z.write(f,'OEBPS/'+f.name,compress_type=zipfile.ZIP_DEFLATED)

def main():
 papers={x['id']:x for x in json.loads((ROOT/'content/papers.json').read_text())};records=json.loads((ROOT/'resources/acquisition.json').read_text())['records'];result=[]
 prior={r['id']:r for r in json.loads((ROOT/'resources/catalog.json').read_text())['records']} if (ROOT/'resources/catalog.json').exists() else {}
 for r in records:
  p=papers.get(r['id'],{});r['aliases']=list(dict.fromkeys(x for x in [p.get('url'),p.get('pdf'),r.get('sourceURL'),r.get('downloadURL'),r.get('metadataURL')] if x))
  if r['status']=='licensed':
   base=Path('library')/r['id']/r['sha256'][:12];out=ROOT/'resources'/base
   if not (out/'book.json').exists():convert(ROOT/'resources'/r['id']/'source.pdf',r,out,base.as_posix())
   r.update(bookPath=(base/'book.json').as_posix(),originalPath=(base/'source.pdf').as_posix(),epubPath=(base/'article.epub').as_posix(),scope='所获主文PDF内全部页；不自动包含站外补充材料',technicalChanges='Format conversion only; no editorial rewrite',noncommercial=True)
  elif prior.get(r['id'],{}).get('bookPath'):
   old=prior[r['id']];old['lastCheckStatus']=r['status'];old['lastCheckedAt']=r['checkedAt'];result.append(old);continue
  if r['id']=='farmsteps-2026':r['reason']='出版页当前为订阅访问，尚未确认可再分发的开放许可；此前称开放全文的表述更正。可导入合法取得的本机原件。';r['status']='rights-review'
  result.append(r)
 extra=[{'id':'quzhou-dataset','title':'曲周原始CSV数据及数据字典','sourceURL':'https://data.mendeley.com/datasets/jp3v9859cx/1','status':'unavailable','reason':'数据论文全文已归档；原始数据包及其许可尚未取得，不把论文正文冒充数据包。'},{'id':'farmsteps-software','title':'FarmSTEPS官方代码与说明','sourceURL':'https://git.wur.nl/jeroen.groot/farmsteps.package','status':'rights-review','reason':'软件许可需独立核验；论文许可不自动授权源码与文档镜像。'}]
 for x in extra:x['aliases']=[x['sourceURL']];result.append(x)
 jw(ROOT/'resources/catalog.json',{'schema':'paper.source.catalog.v2','records':result,'policy':'Noncommercial scholarly archive; explicit licenses, exact originals; private imports stay local.'})
 print('Converted originals:',sum(bool(r.get('bookPath')) for r in result))
if __name__=='__main__':main()
