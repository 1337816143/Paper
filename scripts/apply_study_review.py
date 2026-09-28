#!/usr/bin/env python3
"""Apply narrowly reviewed source translations, never hide a machine draft as reviewed."""
from pathlib import Path
import json,re,hashlib
ROOT=Path(__file__).resolve().parents[1]
def norm(s):return re.sub(r'\s+',' ',re.sub('\u00ad'+r'\s*','',s)).strip()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
 review=json.loads((ROOT/'study/curated-translations.json').read_text());catalog=json.loads((ROOT/'resources/catalog.json').read_text());record=next(r for r in catalog['records'] if r['id']==review['docId']);book=json.loads((ROOT/'resources'/record['bookPath']).read_text());assert book['sourceHash']==review['sourceHash'],'Review requires new source verification'
 path=ROOT/'resources/translations'/book['id']/(book['sourceHash'][:12]+'.zh.json');t=json.loads(path.read_text());bs={b['id']:b for p in book['pages'] for b in p['blocks'] if b.get('text')}
 for bid,v in review['blocks'].items():
  src=norm(bs[bid]['text']);assert src.startswith(v['starts']),bid+' source no longer matches';h=hashlib.sha256(src.encode()).hexdigest();assert h==t['blocks'][bid]['sourceTextHash'];t['blocks'][bid]={**t['blocks'][bid],'zh':v['zh'],'status':'reviewed','engine':'source-paragraph checked translation','flags':[]};t['blocks'][bid].pop('segments',None)
 t['coverage']['manuallyReviewedBlocks']=sum(v['status']=='reviewed' for v in t['blocks'].values());t['coverage']['machineDraftBlocks']=sum(v['status']=='machine-draft' for v in t['blocks'].values());dump(path,t)
 p=ROOT/'resources/translations/translation-report.json';report=json.loads(p.read_text())
 for r in report['records']:
  if r['id']==book['id']:r.update(t['coverage'])
 report['sourceReviewedParagraphs']=len(review['blocks']);dump(p,report)
 p=ROOT/'content/papers.json';papers=json.loads(p.read_text());liang=next(x for x in papers if x['id']=='liang-2022');liang['sections'][3][3]='§2.5.2（Clustering- and distance-based selection），公式9—12；零范围处理为实现补充';dump(p,papers)
 # Only count/apply matching current blocks; local PDF parsing may create different paragraph IDs.
 p=ROOT/'src/study.js';s=p.read_text();old="translation={...t,blocks:{...t.blocks}};await Promise.all(book.pages.flatMap(p=>p.blocks).filter(b=>b.text&&translation.blocks[b.id]).map(async b=>{if(translation.blocks[b.id].sourceTextHash!==await hash(norm(b.text)))delete translation.blocks[b.id];}));"
 new="translation={...t,blocks:{}};const byHash=new Map(Object.values(t.blocks).map(v=>[v.sourceTextHash,v]));await Promise.all(book.pages.flatMap(p=>p.blocks).filter(b=>b.text).map(async b=>{const h=await hash(norm(b.text)),v=t.blocks[b.id]||byHash.get(h);if(v?.sourceTextHash===h)translation.blocks[b.id]=v;}));if(!Object.keys(translation.blocks).length)translation=null;"
 if old in s:s=s.replace(old,new,1)
 elif new not in s:raise ValueError('Study translation validation hook changed')
 p.write_text(s)
 print('Reviewed original paragraph translations:',len(review['blocks']))
if __name__=='__main__':main()
