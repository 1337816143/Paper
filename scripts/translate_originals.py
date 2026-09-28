#!/usr/bin/env python3
"""Offline paragraph translation preparation. Public mode excludes ND licenses.
Private output must be outside publication inputs. No paid API, no credentials.
Original text and identifiers remain immutable; never truncate model inputs.
"""
from pathlib import Path
import argparse,gzip,hashlib,json,os,re,subprocess,time
ROOT=Path(__file__).resolve().parents[1]
MODEL='Helsinki-NLP/opus-mt-en-zh';REVISION='c8ce7d3af8eb15938be419f1c4c177dc724ab8ec'
ALLOW={'https://creativecommons.org/licenses/by/4.0/','https://creativecommons.org/licenses/by-nc/4.0/','https://creativecommons.org/licenses/by-sa/4.0/','https://creativecommons.org/publicdomain/zero/1.0/'}
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def normalized(text):return re.sub(r'\s+',' ',re.sub('\u00ad'+r'\s*','',text)).strip()
def dump(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def public_allowed(r):return r.get('license',{}).get('url','').replace('http:','https:').rstrip('/')+'/' in ALLOW
def symbolic(s):return not re.search(r'[A-Za-z]{4,}',s) or bool(re.fullmatch(r'(?:https?://\S+|[\w.+-]+@[\w.-]+)',s))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['public','private'],required=True);ap.add_argument('--out');ap.add_argument('--ids',default='');ap.add_argument('--threads',type=int,default=4);a=ap.parse_args();out=Path(a.out) if a.out else ROOT/'resources/translations'
 if a.mode=='private' and (not a.out or out.resolve().is_relative_to((ROOT/'resources').resolve())):raise ValueError('Private output inside publication boundary')
 catalog=json.loads((ROOT/'resources/catalog.json').read_text());records=[r for r in catalog['records'] if r.get('bookPath') and (public_allowed(r) if a.mode=='public' else not public_allowed(r))]
 ids=set(a.ids.split(',')) if a.ids else set();records=[r for r in records if not ids or r['id'] in ids];todo=[];books={};cache={};started=time.time()
 op=ROOT/'study/translation-overrides.json';overrides=json.loads(op.read_text()) if op.exists() else {}
 for r in records:
  b=json.loads((ROOT/'resources'/r['bookPath']).read_text());key=r['id'];target=out/key/(b['sourceHash'][:12]+'.zh.json');prior=json.loads(target.read_text()) if target.exists() else {};old=prior.get('blocks',{}) if prior.get('sourceHash')==b['sourceHash'] else {}
  t={'schema':'paper.translations.v3','docId':key,'sourceHash':b['sourceHash'],'language':'zh-CN','engine':{'model':MODEL,'revision':REVISION,'runtime':'CTranslate2 int8 CPU','review':'machine-draft-with-explicit-curated-overrides'},'license':r.get('license'),'sourceCitation':r.get('citation',''),'sourceURL':r.get('sourceURL',''),'visibility':'public-adaptation' if a.mode=='public' else 'personal-use-only-not-for-publication','blocks':{}};books[key]=(r,b,t,target)
  for page in b['pages']:
   for block in page['blocks']:
    if not block.get('text','').strip():continue
    text=normalized(block['text']);h=digest(text);o=old.get(block['id']);v=overrides.get(key,{}).get(block['id'])
    if v and v.get('sourceTextHash')==h:t['blocks'][block['id']]={**v,'status':'reviewed','engine':'source-checked editorial translation'}
    elif o and o.get('sourceTextHash')==h and o.get('zh'):t['blocks'][block['id']]=o
    elif symbolic(text):t['blocks'][block['id']]={'zh':text,'sourceTextHash':h,'status':'verbatim-symbols','page':page['number'],'flags':[]}
    else:todo.append((key,block['id'],text,h,page['number']))
 print('Translation records',len(records),'pending blocks',len(todo),'mode',a.mode,flush=True)
 if todo:
  import ctranslate2
  from transformers import AutoTokenizer
  modeldir=Path(os.environ.get('PAPER_MT_MODEL','/tmp/paper-mt-en-zh-ct2'))
  if not (modeldir/'model.bin').exists():subprocess.run(['ct2-transformers-converter','--model',MODEL,'--revision',REVISION,'--output_dir',str(modeldir),'--quantization','int8','--force'],check=True)
  tokenizer=AutoTokenizer.from_pretrained(MODEL,revision=REVISION);tokenizer.model_max_length=100000
  translator=ctranslate2.Translator(str(modeldir),device='cpu',compute_type='int8',inter_threads=1,intra_threads=max(1,a.threads))
  def tokens(s):return tokenizer.convert_ids_to_tokens(tokenizer.encode(s,add_special_tokens=True))
  def chunks(s):
   if len(tokens(s))<=220:return [s]
   sentences=re.split(r'(?<=[.!?;])\s+(?=[A-Z(\"\[])',s);parts=[];cur=''
   for sentence in sentences:
    if len(tokens(sentence))>220:
     if cur:parts.append(cur);cur=''
     for word in sentence.split():
      v=(cur+' '+word).strip()
      if len(tokens(v))>210 and cur:parts.append(cur);cur=word
      else:cur=v
     if cur:parts.append(cur);cur=''
    else:
     v=(cur+' '+sentence).strip()
     if len(tokens(v))>210 and cur:parts.append(cur);cur=sentence
     else:cur=v
   if cur:parts.append(cur)
   assert normalized(' '.join(parts))==s,'Source sentence order changed'
   assert all(len(tokens(p))<510 for p in parts),'Refusing input truncation'
   return parts
  substitutions={'生态系统业务':'生态系统服务','生态系统服务业':'生态系统服务','作物轮换':'作物轮作','氮剩余':'氮盈余','帕雷托边界':'帕累托前沿','毛幅度':'毛利','毛利润':'毛利','积极偏差':'正向偏离','正偏差方法':'正向偏离方法','利益攸关方':'利益相关者'}
  jobs=[];parts_by_item=[]
  for item in todo:
   ps=chunks(item[2]);parts_by_item.append(ps)
   for p in ps:
    if p not in cache:
     if symbolic(p):cache[p]=p
     else:cache[p]=None;jobs.append(p)
  print('Unique chunks',len(jobs),flush=True)
  for start in range(0,len(jobs),24):
   batch=jobs[start:start+24];inputs=[tokens(s) for s in batch];result=translator.translate_batch(inputs,beam_size=4,max_batch_size=24,max_input_length=0,max_decoding_length=512,length_penalty=1.0,repetition_penalty=1.1)
   for src,pred in zip(batch,result):
    text=tokenizer.decode(tokenizer.convert_tokens_to_ids(pred.hypotheses[0]),skip_special_tokens=True).strip()
    if not text:
     retry=translator.translate_batch([tokens(src)],beam_size=1,min_decoding_length=1,max_input_length=0,max_decoding_length=512)[0];text=tokenizer.decode(tokenizer.convert_tokens_to_ids(retry.hypotheses[0]),skip_special_tokens=True).strip()
    if not text:raise ValueError('Empty translation for natural language: '+repr(src[:150]))
    for wrong,right in substitutions.items():text=text.replace(wrong,right)
    cache[src]=text
   if start==0:print('SAMPLE',json.dumps([{'en':s[:160],'zh':cache[s][:220]} for s in batch[:3]],ensure_ascii=False),flush=True)
   if start%240==0:print('Translated',min(start+len(batch),len(jobs)),'/',len(jobs),'elapsed',int(time.time()-started),flush=True)
  for (key,bid,text,h,page),ps in zip(todo,parts_by_item):
   zh=''.join(cache[s] for s in ps);nums=lambda s:set(re.findall(r'(?<![A-Za-z])\d+(?:\.\d+)?',s));flags=[]
   if nums(text)-nums(zh):flags.append('numbers-check')
   if len(re.findall('[A-Za-z]',text))>70 and not re.search('[\u3400-\u9fff]',zh):flags.append('language-check')
   books[key][2]['blocks'][bid]={'zh':zh,'sourceTextHash':h,'status':'machine-draft','page':page,'chunks':len(ps),'flags':flags}
 public_index=[];bundle=[];summary=[]
 for key,(r,b,t,target) in books.items():
  expected=[x for p in b['pages'] for x in p['blocks'] if x.get('text','').strip()];assert len(t['blocks'])==len(expected),key+' block count mismatch'
  t['coverage']={'translatedTextBlocks':sum(v.get('status')!='verbatim-symbols' for v in t['blocks'].values()),'totalTextBlocks':len(expected),'untranslatedTextBlocks':0,'symbolsRetainedBlocks':sum(v.get('status')=='verbatim-symbols' for v in t['blocks'].values()),'manuallyReviewedBlocks':sum(v.get('status')=='reviewed' for v in t['blocks'].values()),'machineDraftBlocks':sum(v.get('status')=='machine-draft' for v in t['blocks'].values()),'allNumericClaimsManuallyVerified':False}
  dump(target,t);bundle.append(t);summary.append({'id':key,'license':r.get('license',{}).get('name'),'sourceHash':b['sourceHash'],**t['coverage']})
  if a.mode=='public':public_index.append({'id':key,'sourceHash':b['sourceHash'],'path':target.relative_to(ROOT/'resources').as_posix(),'visibility':'public-adaptation'})
 if a.mode=='public':dump(out/'index.json',{'schema':'paper.translation.index.v3','records':public_index,'policy':'ND translations are personal imports, not public adaptations'})
 else:
  out.mkdir(parents=True,exist_ok=True)
  with gzip.open(out/'Paper-Chinese-Personal.papertranslations','wb') as f:f.write(json.dumps({'schema':'paper.private.translations.v3','personalUseOnly':True,'translations':bundle},ensure_ascii=False).encode())
 report={'mode':a.mode,'model':MODEL,'revision':REVISION,'minutes':round((time.time()-started)/60,2),'records':summary,'note':'Automatic reading aid, not author-approved or human-verified translation.'};dump(out/'translation-report.json',report);print(json.dumps(report,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
