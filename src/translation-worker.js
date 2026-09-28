/* All inference runs in this worker; no text is sent to an API. */
let pipePromise;
const normalize=text=>String(text).normalize('NFKC').replace(/([A-Za-z])\u00ad\s*([A-Za-z])/g,'$1$2').replace(/([a-z])-[ \t]*\n[ \t]*([a-z])/g,'$1$2').replace(/\u00ad/g,'').replace(/\s+/g,' ').trim();
async function getPipe(){
  if(!pipePromise)pipePromise=(async()=>{
    const {pipeline,env}=await import('./vendor/translation/transformers.web.min.js');
    const base=new URL('./',self.location.href);
    env.allowLocalModels=true;env.allowRemoteModels=false;
    env.localModelPath=new URL('vendor/translation/models/',base).href;
    env.useBrowserCache=false;
    env.backends.onnx.wasm.wasmPaths=new URL('vendor/translation/wasm/',base).href;
    env.backends.onnx.wasm.numThreads=1;
    env.backends.onnx.wasm.proxy=false;
    const p=await pipeline('translation','opus-mt-en-zh',{dtype:'q8',device:'wasm',local_files_only:true,progress_callback:x=>{if(x.status==='progress')self.postMessage({type:'loading',file:x.file,progress:x.progress});}});
    return p;
  })().catch(e=>{pipePromise=null;throw e;});
  return pipePromise;
}
function sentences(text){
  if(typeof Intl.Segmenter==='function')return [...new Intl.Segmenter('en',{granularity:'sentence'}).segment(text)].map(x=>x.segment.trim()).filter(Boolean);
  return text.match(/[^.!?]+(?:[.!?]+\s*|$)/g)||[text];
}
async function chunks(p,text){
  const out=[];
  async function split(s){
    // Check actual model tokens, not a character-based guess; never silently truncate.
    const ids=p.tokenizer('>>cmn_Hans<< '+s,{add_special_tokens:true,truncation:false}).input_ids;
    const n=ids?.data?.length||ids?.length||0;
    if(n<=300){out.push(s);return;}
    const words=s.split(/\s+/);
    if(words.length<=1){for(let i=0;i<s.length;i+=180)out.push(s.slice(i,i+180));return;}
    const m=Math.ceil(words.length/2);await split(words.slice(0,m).join(' '));await split(words.slice(m).join(' '));
  }
  for(const sentence of sentences(text))await split(sentence);
  return out;
}
let chain=Promise.resolve();
self.onmessage=event=>{
  const {id,text}=event.data||{};
  chain=chain.then(async()=>{
    try{
      if(typeof text!=='string'||text.length>60000)throw Error('Invalid translation paragraph');
      const source=normalize(text);if(!source)throw Error('Empty source');
      const p=await getPipe(),parts=await chunks(p,source),translated=[];
      for(let i=0;i<parts.length;i++){
        const result=await p('>>cmn_Hans<< '+parts[i],{max_new_tokens:480,num_beams:2,do_sample:false,repetition_penalty:1.02});
        const value=result?.[0]?.translation_text;
        if(!value||typeof value!=='string')throw Error('The model returned no translation');
        translated.push(value.trim());self.postMessage({type:'paragraph-progress',id,done:i+1,total:parts.length});
      }
      const output=translated.join('');
      if(!/[\u3400-\u9fff]/.test(output))throw Error('The model did not return Chinese; original retained');
      self.postMessage({type:'result',id,text:output,segments:parts.length,engine:'OPUS-MT en→zh · q8 · 本机机器译文',reviewed:false});
    }catch(error){self.postMessage({type:'error',id,message:String(error?.message||error)});}
  });
};
