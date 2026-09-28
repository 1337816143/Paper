#!/usr/bin/env python3
"""Sentence-complete translation drafts. Every source sentence gets a separate output.
Never overwrite original text. No-derivatives translations are private-only.
"""
from pathlib import Path
import argparse,json,gzip,re,hashlib,os,subprocess,time
from translate_originals import ROOT,MODEL,REVISION,normalized,digest,dump,public_allowed,symbolic
HEADINGS={'HIGHLIGHTS GRAPHICAL ABSTRACT':'研究亮点 / 图文摘要','ARTICLE INFO':'文章信息','ABSTRACT':'摘要','HIGHLIGHTS':'研究亮点','GRAPHICAL ABSTRACT':'图文摘要'}
REPLACE={'生态系统业务':'生态系统服务','生态系统服务业':'生态系统服务','作物轮换':'作物轮作','氮剩余':'氮盈余','帕雷托边界':'帕累托前沿','毛幅度':'毛利','毛利润':'毛利','毛差':'毛利','积极的偏离':'正向偏离','积极偏离':'正向偏离','积极的偏差':'正向偏离','积极偏差':'正向偏离','正偏差方法':'正向偏离方法','利益攸关方':'利益相关者','北中国平原':'华北平原','北中平原':'华北平原','北华平原':'华北平原'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['public','private'],required=True);ap.add_argument('--out');ap.add_argument('--threads',type=int,default=4);a=ap.parse_args();start=time.time();out=Path(a.out) if a.out else ROOT/'resources/translations'
 if a.mode=='private' and (not a.out or out.resolve().is_relative_to((ROOT/'resources').resolve())):raise ValueError('Private output must remain outside publication')
 import ctranslate2
 from transformers import AutoTokenizer
 folder=Path('/tmp/paper-mt-en-zh-ct2')
 if not (folder/'model.bin').exists():subprocess.run(['ct2-transformers-converter','--model',MODEL,'--revision',REVISION,'--output_dir',str(folder),'--quantization','int8','--force'],check=True)
 tok=AutoTokenizer.from_pretrained(MODEL,revision=REVISION);tok.model_max_length=100000
 model=ctranslate2.Translator(str(folder),device='cpu',compute_type='int8',inter_threads=1,intra_threads=a.threads)
 def tokens(s):return tok.convert_ids_to_tokens(tok.encode(s,add_special_tokens=True))
 def parts(s):
  sentences=re.split(r'(?<=[.!?;])\s+(?=[A-Z•])|\s+(?=•)',s);result=[]
  for sentence in sentences:
   if len(tokens(sentence))<160:result.append(sentence);continue
   cur=''
   for word in sentence.split():
    v=(cur+' '+word).strip()
    if len(tokens(v))>145 and cur:result.append(cur);cur=word
    else:cur=v
   if cur:result.append(cur)
  assert normalized(' '.join(result))==s
  assert all(len(tokens(x))<500 for x in result)
  return result
 records=[r for r in json.loads((ROOT/'resources/catalog.json').read_text())['records'] if r.get('bookPath') and public_allowed(r)==(a.mode=='public')];books=[];work=[];known={}
 for r in records:
  b=json.loads((ROOT/'resources'/r['bookPath']).read_text());t={'schema':'paper.translations.v3','docId':b['id'],'sourceHash':b['sourceHash'],'language':'zh-CN','engine':{'model':MODEL,'revision':REVISION,'runtime':'CTranslate2 int8 CPU','segmentation':'sentence-v2','review':'machine-draft-unless-explicitly-reviewed'},'license':r['license'],'sourceCitation':r.get('citation',''),'sourceURL':r.get('sourceURL',''),'visibility':'public-adaptation' if a.mode=='public' else 'personal-use-only-not-for-publication','blocks':{}};books.append((r,b,t))
  for pg in b['pages']:
   for x in pg['blocks']:
    s=normalized(x.get('text',''))
    if not s:continue
    compressed=re.sub(r'(?<=\b[A-Z]) (?=[A-Z]\b)','',s)
    if s=='A B S T R A C T':compressed='ABSTRACT'
    if 'H I G H L I G H T S' in s:compressed='HIGHLIGHTS GRAPHICAL ABSTRACT' if 'G R A P H I C A L' in s else 'HIGHLIGHTS'
    if s=='A R T I C L E I N F O':compressed='ARTICLE INFO'
    if compressed in HEADINGS:t['blocks'][x['id']]={'zh':HEADINGS[compressed],'sourceTextHash':digest(s),'status':'reviewed','page':pg['number'],'flags':[]};continue
    if symbolic(s):t['blocks'][x['id']]={'zh':s,'sourceTextHash':digest(s),'status':'verbatim-symbols','page':pg['number'],'flags':[]};continue
    ps=parts(s);work.append((t,x['id'],s,ps,pg['number']))
    for part in ps:known.setdefault(part,None)
 jobs=[s for s in known if not symbolic(s)]
 for s in known:
  if symbolic(s):known[s]=s
 print('Articles',len(records),'natural-language blocks',len(work),'sentences',len(jobs),flush=True)
 for i in range(0,len(jobs),32):
  batch=jobs[i:i+32];inputs=[tokens(re.sub(r'\bNCP\b','North China Plain',s).replace('wheat-maize','wheat and maize').replace('wheat–maize','wheat and maize')) for s in batch]
  output=model.translate_batch(inputs,beam_size=4,max_batch_size=32,max_input_length=0,max_decoding_length=512,repetition_penalty=1.05)
  for src,o in zip(batch,output):
   zh=tok.decode(tok.convert_tokens_to_ids(o.hypotheses[0]),skip_special_tokens=True).strip();assert zh,'Empty natural-language sentence'
   for wrong,right in REPLACE.items():zh=zh.replace(wrong,right)
   known[src]=zh
  if i%320==0:print('Sentences',min(i+32,len(jobs)),'/',len(jobs),'seconds',int(time.time()-start),flush=True)
 for t,bid,src,ps,page in work:
  zh='\n'.join(known[s] for s in ps);numbers=lambda s:set(re.findall(r'\d+(?:\.\d+)?',s));flags=[]
  if numbers(src)-numbers(zh):flags.append('numbers-check')
  t['blocks'][bid]={'zh':zh,'sourceTextHash':digest(src),'status':'machine-draft','page':page,'segments':[{'sourceTextHash':digest(s),'zh':known[s]} for s in ps],'sentenceCount':len(ps),'flags':flags}
 index=[];bundle=[];summary=[]
 for r,b,t in books:
  blocks=[x for pg in b['pages'] for x in pg['blocks'] if x.get('text','').strip()];assert len(blocks)==len(t['blocks'])
  t['coverage']={'translatedTextBlocks':sum(x['status']!='verbatim-symbols' for x in t['blocks'].values()),'totalTextBlocks':len(blocks),'untranslatedTextBlocks':0,'symbolsRetainedBlocks':sum(x['status']=='verbatim-symbols' for x in t['blocks'].values()),'manuallyReviewedBlocks':sum(x['status']=='reviewed' for x in t['blocks'].values()),'machineDraftBlocks':sum(x['status']=='machine-draft' for x in t['blocks'].values()),'separatelyTranslatedSentences':sum(x.get('sentenceCount',0) for x in t['blocks'].values()),'allNumericClaimsManuallyVerified':False}
  file=out/b['id']/(b['sourceHash'][:12]+'.zh.json');dump(file,t);bundle.append(t);summary.append({'id':b['id'],'license':r['license']['name'],**t['coverage']})
  if a.mode=='public':index.append({'id':b['id'],'sourceHash':b['sourceHash'],'path':file.relative_to(ROOT/'resources').as_posix(),'visibility':'public-adaptation'})
 if a.mode=='public':dump(out/'index.json',{'schema':'paper.translation.index.v3','records':index,'policy':'Sentence-complete drafts; ND translations remain private imports'})
 else:
  out.mkdir(parents=True,exist_ok=True)
  with gzip.open(out/'Paper-Chinese-Personal.papertranslations','wb') as f:f.write(json.dumps({'schema':'paper.private.translations.v3','personalUseOnly':True,'translations':bundle},ensure_ascii=False).encode())
 report={'mode':a.mode,'model':MODEL,'revision':REVISION,'segmentation':'sentence-v2','minutes':round((time.time()-start)/60,2),'records':summary,'note':'Sentence segmentation prevents omitted source sentences in generation, but machine translation can still contain semantic errors.'};dump(out/'translation-report.json',report);print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
