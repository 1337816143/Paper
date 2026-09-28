#!/usr/bin/env python3
"""Source-faithful math overlays. No OCR or change to source strings/block IDs.
A region can contain several equations: render ALL their verified transcriptions,
or retain the exact full crop. Never select only the last equation in a region.
"""
from pathlib import Path
import json,re,hashlib,collections
import fitz
ROOT=Path(__file__).resolve().parents[1]
MNS='http://www.w3.org/1998/Math/MathML'
def sub(a,b):return f'<msub><mi>{a}</mi><mi>{b}</mi></msub>'
def mml(eq):return '<math xmlns="'+MNS+'" display="block">'+eq+'</math>'
D='<msub><mi>d</mi><mrow><mi>k</mi><mo>,</mo><mi>c</mi></mrow></msub>'
SUM='<munderover><mo>∑</mo><mrow><mi>k</mi><mo>=</mo><mn>1</mn></mrow><mi>n</mi></munderover>'
MATH={
 '9':mml(sub('MIDIP','c')+'<mo>=</mo><msqrt><mrow>'+SUM+'<msup>'+D+'<mn>2</mn></msup></mrow></msqrt>'),
 '10':mml(D+'<mo>=</mo><mo>|</mo><mfrac><mrow><msub><mi>p</mi><mrow><mi>k</mi><mo>,</mo><mi>c</mi></mrow></msub><mo>−</mo>'+sub('q','k')+'</mrow>'+sub('md','k')+'</mfrac><mo>|</mo>'),
 '11':mml(sub('md','k')+'<mo>=</mo>'+sub('maximum','k')+'<mo>−</mo>'+sub('minimum','k')),
 '12':mml(sub('HDIP','c')+'<mo>=</mo><msqrt><mfrac><mrow>'+SUM+'<msup><mrow><mo>(</mo>'+D+'<mo>−</mo><msub><mover><mi>d</mi><mo>¯</mo></mover><mi>c</mi></msub><mo>)</mo></mrow><mn>2</mn></msup></mrow><mrow><mi>n</mi><mo>−</mo><mn>1</mn></mrow></mfrac></msqrt>')
}
EXPECTED={'9':'MIDIP','10':'md','11':'maximum','12':'HDIP'}
def transcription(article,raw,numbers):
 if article!='liang-2022' or not numbers:return None
 if any(n not in MATH or EXPECTED[n].lower() not in raw.lower() for n in numbers):return None
 if len(numbers)==1:return MATH[numbers[0]].replace('<math ','<math data-equation-number="'+numbers[0]+'" ',1)
 rows=[]
 for n in numbers:
  inner=MATH[n].split('>',1)[1].rsplit('</math>',1)[0]
  rows.append('<mtr data-equation-number="'+n+'"><mtd><mrow>'+inner+'</mrow></mtd><mtd><mtext>('+n+')</mtext></mtd></mtr>')
 return mml('<mtable columnalign="left right" columnspacing="1em" rowspacing="1em">'+''.join(rows)+'</mtable>')
def norm(s):return re.sub(r'\s+',' ',s).strip()
def letters(s):return len(re.findall(r'[A-Za-z]{3,}',s))
def is_math(b):
 t=norm(b['text'])
 return len(t)<360 and letters(t)<=10 and bool(re.search(r'[=∑√∫∏≤≥≈]',t)) and not re.search(r'\b(?:where|which|including|respectively|calculated|defined)\b',t,re.I)
def is_fragment(b):
 t=norm(b['text'])
 return len(t)<120 and letters(t)<=3 and not re.search(r'\b(?:Fig|Table|References)\b',t,re.I)
def rect(b):return fitz.Rect(b['bbox'])
def gap(a,b):return max(0,a.y0-b.y1,b.y0-a.y1)
def main():
 catalog=json.loads((ROOT/'resources/catalog.json').read_text());layouts={};audit=[]
 for r in catalog['records']:
  if not r.get('bookPath'):continue
  bp=ROOT/'resources'/r['bookPath'];book=json.loads(bp.read_text());pdf=ROOT/'resources'/r['originalPath'];doc=fitz.open(pdf)
  groups=[];inline={}
  for pi,page in enumerate(doc):
   original=[b for b in book['pages'][pi]['blocks'] if b.get('text') and b.get('bbox')]
   candidates=[b for b in original if is_math(b)];used=set()
   for seed in candidates:
    if seed['id'] in used:continue
    region=rect(seed);col=0 if region.x0<page.rect.width/2 else 1
    xlo=0 if not col else page.rect.width/2-6;xhi=page.rect.width/2+6 if not col else page.rect.width
    members=[seed]
    for _ in range(5):
     change=False
     for other in original:
      if other in members or other['id'] in used or not is_fragment(other):continue
      rr=rect(other)
      if rr.x0<xlo or rr.x1>xhi or gap(rr,region)>7:continue
      union=region|rr
      if union.height>145 or union.width>page.rect.width*.62:continue
      members.append(other);region=union;change=True
     if not change:break
    members.sort(key=lambda x:original.index(x));raw=' '.join(norm(x['text']) for x in members)
    numbers=list(dict.fromkeys(re.findall(r'\((\d{1,2})\)',raw)))
    number=numbers[0] if len(numbers)==1 else ('–'.join(numbers) if numbers else '')
    if not number and len(raw)<5:continue
    used.update(x['id'] for x in members)
    pad=(region+(-5,-5,5,5))&page.rect
    fingerprint=hashlib.sha256((r['sha256']+str(list(pad))).encode()).hexdigest()[:12]
    name='math-v3-'+fingerprint+'.png';page.get_pixmap(matrix=fitz.Matrix(2.8,2.8),clip=pad,alpha=False).save(bp.parent/name)
    g={'id':r['id']+'-'+fingerprint,'page':pi+1,'number':number,'numbers':numbers,'blocks':[x['id'] for x in members],'bbox':list(pad),'path':str(Path(r['bookPath']).parent/name),'method':'exact PDF region; no reconstructed symbols','rawEvidence':raw}
    native=transcription(r['id'],raw,numbers)
    if native:
     g.update(mathml=native,transcribedNumbers=numbers,method='all numbered expressions transcribed; complete source crop retained')
     if len(numbers)>1:g['number']=''
     assert re.findall(r'data-equation-number="(\d+)"',native)==numbers,'Incomplete native formula region'
    groups.append(g)
   rawblocks={}
   for block in page.get_text('dict')['blocks']:
    if block.get('type')==0:
     text='\n'.join(''.join(s['text'] for s in line['spans']) for line in block['lines']).strip();rawblocks[text]=block
   for b in original:
    rb=rawblocks.get(b['text']);out=[]
    if not rb or b['id'] in used:continue
    flat=norm(b['text']);cursor=0
    for line in rb['lines']:
     spans=line['spans'];sizes=collections.Counter()
     for s in spans:sizes[round(s['size'],1)]+=len(s['text'])
     if not sizes:continue
     base_size=sizes.most_common(1)[0][0];primary=[s for s in spans if abs(s['size']-base_size)<.2]
     baseline=sum(s['origin'][1] for s in primary)/len(primary)
     for s in spans:
      t=norm(s['text'])
      if not t:continue
      start=flat.find(t,cursor)
      if start<0:continue
      cursor=start+len(t);dy=s['origin'][1]-baseline
      tag='sup' if s['flags']&1 or (s['size']<base_size*.94 and dy<-1.1) else ('sub' if s['size']<base_size*.94 and dy>1.1 else None)
      if tag and len(t)<32 and not re.search(r'\s\w{3}',t):out.append({'start':start,'end':cursor,'tag':tag,'text':t})
    if out:inline[b['id']]=out
  layouts[r['id']]={'sourceHash':r['sha256'],'groups':groups,'inline':inline,'scope':'Layout overlays only; machine-detected display equations may still require visual review.'}
  audit.append({'id':r['id'],'sourceSHA256':r['sha256'],'equationGroups':len(groups),'mathmlGroups':sum('mathml' in g for g in groups),'mathmlTranscriptions':sum(len(g.get('transcribedNumbers',[])) for g in groups),'multiEquationGroups':sum(len(g.get('numbers',[]))>1 for g in groups),'inlineBlocks':len(inline),'originalUnchanged':hashlib.sha256(pdf.read_bytes()).hexdigest()==r['sha256']})
  doc.close()
 (ROOT/'resources/study-layouts.json').write_text(json.dumps(layouts,ensure_ascii=False,indent=2)+'\n')
 (ROOT/'resources/study-layout-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(audit,ensure_ascii=False))
if __name__=='__main__':main()
