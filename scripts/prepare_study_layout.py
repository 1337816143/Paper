#!/usr/bin/env python3
"""Recover mathematical display regions, keeping source text, hashes and old anchors.
No OCR, no invented formula. Exact PDF crops are the fallback; four Liang-2022
expressions have explicit source-checked MathML. This never deletes a source block.
"""
from pathlib import Path
import hashlib,json,re,collections
import fitz
ROOT=Path(__file__).resolve().parents[1]
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def text(b):return b.get('text','')
def mathlike(s):
 s=re.sub(r'\s+',' ',s).strip();words=re.findall(r'[A-Za-z]{4,}',s)
 if len(s)>700:return False
 if re.search(r'\b(where|defined|calculated|represents|respectively|therefore|indicator|which|using|equation|Table|Figure)\b',s,re.I):return False
 if re.search('[=∑Σ√∫∏≤≥]',s) and len(words)<=6:return True
 return len(s)<90 and len(words)<=1 and not re.search(r'\b(and|the|was|are|for|from|with)\b',s,re.I)
def rect(b):return fitz.Rect(b['bbox'])
def native(label):
 sub=lambda a,b:'<msub><mi>'+a+'</mi><mrow>'+b+'</mrow></msub>'
 dc=sub('d','<mi>k</mi><mo>,</mo><mi>c</mi>');summ='<munderover><mo>∑</mo><mrow><mi>k</mi><mo>=</mo><mn>1</mn></mrow><mi>n</mi></munderover>';mc=sub('md','<mi>k</mi>')
 eq={
 '9':sub('MIDIP','<mi>c</mi>')+'<mo>=</mo><msqrt><mrow>'+summ+'<msup>'+dc+'<mn>2</mn></msup></mrow></msqrt>',
 '10':dc+'<mo>=</mo><mrow><mo>|</mo><mfrac><mrow>'+sub('p','<mi>k</mi><mo>,</mo><mi>c</mi>')+'<mo>−</mo>'+sub('q','<mi>k</mi>')+'</mrow>'+mc+'</mfrac><mo>|</mo></mrow>',
 '11':mc+'<mo>=</mo>'+sub('maximum','<mi>k</mi>')+'<mo>−</mo>'+sub('minimum','<mi>k</mi>'),
 '12':sub('HDIP','<mi>c</mi>')+'<mo>=</mo><msqrt><mfrac><mrow>'+summ+'<msup><mrow><mo>(</mo>'+dc+'<mo>−</mo><msub><mover><mi>d</mi><mo>¯</mo></mover><mi>c</mi></msub><mo>)</mo></mrow><mn>2</mn></msup></mrow><mrow><mi>n</mi><mo>−</mo><mn>1</mn></mrow></mfrac></msqrt>'}
 gloss={'9':'对n个指标到理想点的范围标准化距离平方求和，再开根号；c表示案例群组。','10':'群组中心与该指标理想值之差，除以全体观测的指标范围，再取绝对值。','11':'指标k在全体观测中的最大值与最小值之差。','12':'各指标距离相对其平均距离的样本标准差；分母为n−1。'}
 return ('<math xmlns="http://www.w3.org/1998/Math/MathML" display="block"><mrow>'+eq[label]+'</mrow></math>',gloss[label]) if label in eq else (None,None)
def main():
 catalog=json.loads((ROOT/'resources/catalog.json').read_text());index={'schema':'paper.formula.index.v3','records':[]};report=[]
 for r in catalog['records']:
  if not r.get('bookPath'):continue
  b=json.loads((ROOT/'resources'/r['bookPath']).read_text());pdf=fitz.open(ROOT/'resources'/r['originalPath']);dest=ROOT/'resources/formulas'/b['id']/b['sourceHash'][:12];dest.mkdir(parents=True,exist_ok=True);equations=[];blockmap={};classified={};headings=[]
  for p in b['pages']:
   page=pdf[p['number']-1];w,h=page.rect.width,page.rect.height;bs=[x for x in p['blocks'] if x.get('bbox') and x.get('text')]
   # Rendering classification is an overlay: repeated running headers/footers remain in proofs.
   for x in bs:
    rr=rect(x);s=re.sub(r'\s+',' ',text(x)).strip()
    if (rr.y0<55 or rr.y1>h-24) and len(s)<180:classified[x['id']]='running-metadata'
    if x['kind']=='heading' and (re.match(r'^\d+(?:\.\d+)*\.?\s+[A-Za-z]',s) or s.lower() in ['abstract','references','conclusions','conclusion','acknowledgements','acknowledgments','data availability','declaration of competing interest']):headings.append(x['id'])
   seeds=[]
   for x in bs:
    if not mathlike(text(x)):continue
    m=re.search(r'\((\d{1,2}[a-z]?)\)\s*$',text(x))
    if m:seeds.append((x,m.group(1)))
   used=set()
   for seed,label in seeds:
    if seed['id'] in used:continue
    sr=rect(seed);cy=(sr.y0+sr.y1)/2;left=sr.x1<w*.57;xlo=0 if left else w*.46;xhi=w*.55 if left else w
    candidates=[x for x in bs if x['id'] not in used and mathlike(text(x)) and rect(x).x0>=xlo-5 and rect(x).x1<=xhi+10 and abs((rect(x).y0+rect(x).y1)/2-cy)<65]
    anchors=[x for x in candidates if re.search('[=∑Σ√∫∏]',text(x))]
    if not anchors:continue
    # Equation labels separate adjacent expressions; do not absorb a neighbouring equation.
    other_y=[(rect(x).y0+rect(x).y1)/2 for x,l in seeds if x['id']!=seed['id'] and (rect(x).x1<w*.57)==left]
    lo=max([cy-70]+[(y+cy)/2 for y in other_y if y<cy-2]);hi=min([cy+30]+[(y+cy)/2 for y in other_y if y>cy+2])
    members=[x for x in candidates if lo-3<=((rect(x).y0+rect(x).y1)/2)<=hi+3]
    if not any(re.search('[=∑Σ√∫∏]',text(x)) for x in members):continue
    if seed not in members:members.append(seed)
    members.sort(key=lambda x:p['blocks'].index(x));roi=rect(members[0])
    for x in members[1:]:roi|=rect(x)
    if roi.height>160 or roi.get_area()>page.rect.get_area()*.3:continue
    roi=(roi+(-3,-3,3,3))&page.rect;fn='p'+str(p['number'])+'-eq-'+label+'-'+hashlib.sha256('|'.join(x['id'] for x in members).encode()).hexdigest()[:6]+'.png';page.get_pixmap(matrix=fitz.Matrix(3,3),clip=roi,alpha=False).save(dest/fn)
    eq={'id':'formula-p'+str(p['number'])+'-'+label,'page':p['number'],'label':label,'first':members[0]['id'],'members':[x['id'] for x in members],'path':(dest/fn).relative_to(ROOT/'resources').as_posix(),'bbox':list(roi),'sourceText':'\n'.join(text(x) for x in members),'source':'Original PDF equation region, not OCR or reconstruction','render':'source-crop','proofPage':p['number']}
    if b['id']=='liang-2022' and b['sourceHash'].startswith('bfbde3ef50d6') and label in ['9','10','11','12']:
     ml,zh=native(label);eq.update(mathML=ml,gloss=zh,render='source-checked-mathml-with-original-crop',location='§2.5.2, equation ('+label+')')
    equations.append(eq)
    for x in members:used.add(x['id']);blockmap[x['id']]=eq['id']
   report.append({'id':b['id'],'page':p['number'],'equations':[{'label':e['label'],'blocks':e['members'],'text':e['sourceText'][:260]} for e in equations if e['page']==p['number']]})
  layout={'schema':'paper.layout.v3','docId':b['id'],'sourceHash':b['sourceHash'],'equations':equations,'blockMap':blockmap,'classification':classified,'sectionHeadingIds':headings,'policy':'Display overlay only. Exact source file and original text blocks unchanged; prior annotation anchors retained.'};dump(dest/'layout.json',layout);index['records'].append({'id':b['id'],'sourceHash':b['sourceHash'],'path':(dest/'layout.json').relative_to(ROOT/'resources').as_posix(),'equationCount':len(equations)})
  assert len(b['pages'])==len(pdf);pdf.close()
 dump(ROOT/'resources/formulas/index.json',index);dump(ROOT/'resources/formulas/report.json',{'records':report,'total':sum(x['equationCount'] for x in index['records'])});print(json.dumps(index,ensure_ascii=False))
if __name__=='__main__':main()
