#!/usr/bin/env python3
"""Prepare actual neural translations; never replace source text or silently truncate.
Public mode strictly excludes ND/restricted licenses. Private mode writes only to
an explicit NON-PUBLISHED output directory. No commercial API or browser keys.
"""
from pathlib import Path
import argparse,collections,datetime,gzip,hashlib,json,os,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
MODEL='Helsinki-NLP/opus-mt-en-zh'
REVISION='c8ce7d3af8eb15938be419f1c4c177dc724ab8ec'
ALLOW={'https://creativecommons.org/licenses/by/4.0/','https://creativecommons.org/licenses/by-nc/4.0/','https://creativecommons.org/licenses/by-sa/4.0/','https://creativecommons.org/publicdomain/zero/1.0/'}
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def normalized(text):
    # Soft hyphen is a layout marker, not an ordinary lexical hyphen.
    return re.sub(r'\s+',' ',re.sub('\u00ad\s*','',text)).strip()
def dump(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def public_allowed(r):return r.get('license',{}).get('url','').replace('http:','https:').rstrip('/')+'/' in ALLOW

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['public','private'],required=True);ap.add_argument('--out');ap.add_argument('--ids',default='');ap.add_argument('--threads',type=int,default=4);a=ap.parse_args()
    out=Path(a.out) if a.out else ROOT/'resources/translations'
    if a.mode=='private' and (not a.out or out.resolve().is_relative_to((ROOT/'resources').resolve())):raise ValueError('Private translations must stay outside all publication inputs')
    catalog=json.loads((ROOT/'resources/catalog.json').read_text());records=[r for r in catalog['records'] if r.get('bookPath') and (public_allowed(r) if a.mode=='public' else not public_allowed(r))]
    ids=set(a.ids.split(',')) if a.ids else set();records=[r for r in records if not ids or r['id'] in ids]
    todo=[];books={};cache={};started=time.time()
    overrides_path=ROOT/'study/translation-overrides.json';overrides=json.loads(overrides_path.read_text()) if overrides_path.exists() else {}
    for r in records:
        p=ROOT/'resources'/r['bookPath'];b=json.loads(p.read_text());key=r['id'];target=out/key/(b['sourceHash'][:12]+'.zh.json')
        prior=json.loads(target.read_text()) if target.exists() else {};old=prior.get('blocks',{}) if prior.get('sourceHash')==b['sourceHash'] else {}
        t={'schema':'paper.translations.v3','docId':key,'sourceHash':b['sourceHash'],'language':'zh-CN','engine':{'model':MODEL,'revision':REVISION,'runtime':'CTranslate2 int8 CPU','review':'machine-draft-with-explicit-curated-overrides'},'license':r.get('license'),'sourceCitation':r.get('citation',''),'sourceURL':r.get('sourceURL',''),'visibility':'public-adaptation' if a.mode=='public' else 'personal-use-only-not-for-publication','blocks':{}}
        books[key]=(r,b,t,target)
        for page in b['pages']:
            for block in page['blocks']:
                if 'text' not in block or not block['text'].strip():continue
                text=normalized(block['text']);h=digest(text);old_entry=old.get(block['id']);override=overrides.get(key,{}).get(block['id'])
                if override and override.get('sourceTextHash')==h:t['blocks'][block['id']]={**override,'status':'reviewed','engine':'source-checked editorial translation'}
                elif old_entry and old_entry.get('sourceTextHash')==h and old_entry.get('zh'):t['blocks'][block['id']]=old_entry
                else:todo.append((key,block['id'],text,h,page['number']))
    print('Translation records',len(records),'pending blocks',len(todo),'mode',a.mode,flush=True)
    if todo:
        import ctranslate2
        from transformers import AutoTokenizer
        modeldir=Path(os.environ.get('PAPER_MT_MODEL','/tmp/paper-mt-en-zh-ct2'))
        if not (modeldir/'model.bin').exists():
            subprocess.run(['ct2-transformers-converter','--model',MODEL,'--revision',REVISION,'--output_dir',str(modeldir),'--quantization','int8','--force'],check=True)
        tokenizer=AutoTokenizer.from_pretrained(MODEL,revision=REVISION)
        translator=ctranslate2.Translator(str(modeldir),device='cpu',compute_type='int8',inter_threads=1,intra_threads=max(1,a.threads))
        def tokens(s):return tokenizer.convert_ids_to_tokens(tokenizer.encode(s,add_special_tokens=True))
        def chunks(s):
            # Length is checked before inference, never truncate=True.
            if len(tokens(s))<=220:return [s]
            sentences=re.split(r'(?<=[.!?;])\s+(?=[A-Z(\"\[])',s);parts=[];current=''
            for sentence in sentences:
                if len(tokens(sentence))>220:
                    words=sentence.split();small=''
                    for word in words:
                        v=(small+' '+word).strip()
                        if len(tokens(v))>210 and small:parts.append(small);small=word
                        else:small=v
                    if small:parts.append(small)
                else:
                    v=(current+' '+sentence).strip()
                    if len(tokens(v))>210 and current:parts.append(current);current=sentence
                    else:current=v
            if current:parts.append(current)
            # Preserve original sentence order (fallback transparent word segmentation).
            if normalized(' '.join(parts))!=s:
                parts=[];current=''
                for word in s.split():
                    v=(current+' '+word).strip()
                    if len(tokens(v))>210 and current:parts.append(current);current=word
                    else:current=v
                if current:parts.append(current)
            assert normalized(' '.join(parts))==s
            assert all(len(tokens(p))<510 for p in parts),'Token split failed, refusing truncation'
            return parts
        replacements={'生态系统业务':'生态系统服务','生态系统服务业':'生态系统服务','作物轮换':'作物轮作','氮剩余':'氮盈余','帕雷托边界':'帕累托前沿','毛幅度':'毛利','毛利润':'毛利','积极偏差':'正向偏离','正偏差方法':'正向偏离方法','利益攸关方':'利益相关者'}
        jobs=[];parts_by_item=[]
        for item in todo:
            ps=chunks(item[2]);parts_by_item.append(ps)
            for p in ps:
                if p not in cache:cache[p]=None;jobs.append(p)
        print('Unique translation chunks',len(jobs),flush=True)
        for start in range(0,len(jobs),24):
            batch=jobs[start:start+24];inputs=[tokens(s) for s in batch]
            result=translator.translate_batch(inputs,beam_size=4,max_batch_size=24,max_input_length=0,max_decoding_length=512,length_penalty=1.0,repetition_penalty=1.1)
            for src,pred in zip(batch,result):
                text=tokenizer.decode(tokenizer.convert_tokens_to_ids(pred.hypotheses[0]),skip_special_tokens=True).strip()
                for wrong,right in replacements.items():text=text.replace(wrong,right)
                if not text:raise ValueError('Empty translation; refusing false completion')
                cache[src]=text
            if start%240==0:print('Translated',min(start+len(batch),len(jobs)),'/',len(jobs),'elapsed',int(time.time()-started),flush=True)
        for (key,bid,text,h,page),ps in zip(todo,parts_by_item):
            zh=''.join(cache[s] for s in ps);nums=lambda s:set(re.findall(r'(?<![A-Za-z])\d+(?:\.\d+)?',s));missing=sorted(nums(text)-nums(zh));flags=[]
            if missing:flags.append('numbers-check')
            if len(re.findall('[A-Za-z]',text))>70 and not re.search('[\u3400-\u9fff]',zh):flags.append('language-check')
            books[key][2]['blocks'][bid]={'zh':zh,'sourceTextHash':h,'status':'machine-draft','page':page,'chunks':len(ps),'flags':flags}
    public_index=[];bundle=[];summary=[]
    for key,(r,b,t,target) in books.items():
        expected=[x for p in b['pages'] for x in p['blocks'] if x.get('text','').strip()]
        assert len(t['blocks'])==len(expected),key+' translation block mismatch'
        t['coverage']={'translatedTextBlocks':len(t['blocks']),'totalTextBlocks':len(expected),'untranslatedTextBlocks':0,'manuallyReviewedBlocks':sum(x.get('status')=='reviewed' for x in t['blocks'].values()),'machineDraftBlocks':sum(x.get('status')=='machine-draft' for x in t['blocks'].values()),'allNumericClaimsManuallyVerified':False}
        dump(target,t);bundle.append(t);summary.append({'id':key,'license':r.get('license',{}).get('name'),'sourceHash':b['sourceHash'],**t['coverage']})
        if a.mode=='public':public_index.append({'id':key,'sourceHash':b['sourceHash'],'path':target.relative_to(ROOT/'resources').as_posix(),'visibility':'public-adaptation'})
    if a.mode=='public':dump(out/'index.json',{'schema':'paper.translation.index.v3','records':public_index,'policy':'Publicly redistributable adaptations only; ND translations require personal bundle'})
    else:
        out.mkdir(parents=True,exist_ok=True)
        with gzip.open(out/'Paper-Chinese-Personal.papertranslations','wb') as f:f.write(json.dumps({'schema':'paper.private.translations.v3','personalUseOnly':True,'translations':bundle},ensure_ascii=False).encode())
    report={'mode':a.mode,'model':MODEL,'revision':REVISION,'minutes':round((time.time()-started)/60,2),'records':summary,'note':'Automatic bilingual reading aid. It is not an author-approved translation or a substitute for original numeric/method evidence.'};dump(out/'translation-report.json',report);print(json.dumps(report,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
