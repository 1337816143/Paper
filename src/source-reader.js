/* Paper Lab local original-paper reader. User-imported files stay on-device. */
(() => {
'use strict';
const DB='paper-lab-source-library-v1', VERSION=1, MAX_BYTES=120*1024*1024;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let dbp;
function db(){
  if(!('indexedDB' in window))return Promise.reject(Error('当前浏览器不支持IndexedDB'));
  if(dbp)return dbp;
  dbp=new Promise((resolve,reject)=>{
    const req=indexedDB.open(DB,VERSION);
    req.onupgradeneeded=()=>{
      const d=req.result;
      if(!d.objectStoreNames.contains('sources'))d.createObjectStore('sources',{keyPath:'paperId'});
      if(!d.objectStoreNames.contains('annotations')){
        const s=d.createObjectStore('annotations',{keyPath:'id'});
        s.createIndex('paperId','paperId',{unique:false});
      }
    };
    req.onsuccess=()=>resolve(req.result);
    req.onerror=()=>reject(req.error||Error('IndexedDB打开失败'));
  });
  return dbp;
}
async function reqValue(store,mode,make){
  const d=await db();
  return new Promise((resolve,reject)=>{
    const tx=d.transaction(store,mode), req=make(tx.objectStore(store));
    req.onsuccess=()=>resolve(req.result);
    req.onerror=()=>reject(req.error||Error('本机资料库读取失败'));
  });
}
async function put(store,value){
  const d=await db();
  return new Promise((resolve,reject)=>{
    const tx=d.transaction(store,'readwrite');tx.objectStore(store).put(value);
    tx.oncomplete=()=>resolve(value);tx.onerror=()=>reject(tx.error||Error('本机资料库写入失败'));
  });
}
async function del(store,key){
  const d=await db();
  return new Promise((resolve,reject)=>{
    const tx=d.transaction(store,'readwrite');tx.objectStore(store).delete(key);
    tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error||Error('本机资料库删除失败'));
  });
}
const getSource=id=>reqValue('sources','readonly',s=>s.get(id));
const listSources=()=>reqValue('sources','readonly',s=>s.getAll());
const deleteSource=id=>del('sources',id);
const getAnnotation=id=>reqValue('annotations','readonly',s=>s.get(id));
const listAnnotations=paperId=>paperId?reqValue('annotations','readonly',s=>s.index('paperId').getAll(paperId)):reqValue('annotations','readonly',s=>s.getAll());
const deleteAnnotation=id=>del('annotations',id);
const uid=()=>crypto.randomUUID?.()||('ann-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,10));
async function hashBlob(blob){
  if(!crypto.subtle||blob.size>64*1024*1024)return null;
  const h=await crypto.subtle.digest('SHA-256',await blob.arrayBuffer());
  return [...new Uint8Array(h)].map(x=>x.toString(16).padStart(2,'0')).join('');
}
function chunks(text,limit=16000){
  const parts=String(text||'').replace(/\r\n?/g,'\n').split(/\n{2,}/), out=[];let cur='';
  for(const p0 of parts){
    const p=p0.trim();if(!p)continue;
    if(cur&&cur.length+p.length+2>limit){out.push(cur);cur='';}
    if(p.length>limit){if(cur){out.push(cur);cur='';}for(let i=0;i<p.length;i+=limit)out.push(p.slice(i,i+limit));}
    else cur+=(cur?'\n\n':'')+p;
  }
  if(cur)out.push(cur);return out.length?out:[''];
}
function htmlToText(raw){
  const doc=new DOMParser().parseFromString(raw,'text/html');
  doc.querySelectorAll('script,style,noscript,iframe,svg,canvas,form').forEach(n=>n.remove());
  const root=doc.querySelector('article,main,[role="main"]')||doc.body||doc.documentElement;
  const blocks=[...root.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,blockquote,pre,figcaption,tr')];
  const lines=[];
  for(const el of blocks){
    if(blocks.some(x=>x!==el&&el.contains(x)))continue;
    const t=(el.textContent||'').replace(/[ \t\f\v]+/g,' ').replace(/\n\s+/g,'\n').trim();
    if(t)lines.push(t);
  }
  return lines.length?lines.join('\n\n'):(root.textContent||'').replace(/\s+/g,' ').trim();
}
async function importFile(paperId,file,meta={},onProgress){
  if(!paperId)throw Error('缺少论文ID');
  if(!(file instanceof Blob))throw Error('请选择本机文件');
  if(file.size>MAX_BYTES)throw Error('单个原文文件暂限120MB');
  if(navigator.storage?.persist)try{await navigator.storage.persist();}catch{}
  const name=file.name||meta.name||'source', lower=name.toLowerCase(), mime=file.type||'';
  let pages,format;
  const existing=await getSource(paperId);
  if(mime==='application/pdf'||lower.endsWith('.pdf')){
    format='pdf';
    pages=existing?.pages?.some(p=>p.text&& !p.text.startsWith('[PDF原文件已保存'))?existing.pages:[{n:1,text:'[PDF原文件已保存到本设备。当前公开版不从第三方复制全文，也不上传你的PDF做OCR。若同时导入HTML/TXT/Markdown全文，就可在本站使用连续阅读、翻页和划线；PDF原文件仍保留用于WPS等外部阅读器。]'}];
  }else{
    const raw=await file.text();
    if(mime.includes('html')||/\.html?$/.test(lower)){format='html';pages=chunks(htmlToText(raw)).map((text,i)=>({n:i+1,text}));}
    else {format=lower.endsWith('.md')?'markdown':'text';pages=chunks(raw).map((text,i)=>({n:i+1,text}));}
  }
  if(!pages.some(p=>p.text.trim()))throw Error('没有提取到可阅读文字。');
  const isPdf=format==='pdf', oldOriginal=existing?.originalBlob||existing?.blob;
  const source={paperId,title:meta.title||paperId,name:isPdf?(existing?.name||name):name,type:isPdf?(existing?.type||mime||'application/pdf'):(mime||({html:'text/html',markdown:'text/markdown'}[format]||'text/plain')),format:isPdf?(existing?.format||'pdf'):format,size:isPdf?(existing?.size||file.size):file.size,sha256:isPdf?(existing?.sha256||await hashBlob(file)):await hashBlob(file),importedAt:new Date().toISOString(),pages,blob:isPdf?(existing?.blob||file):file,originalBlob:isPdf?file:oldOriginal,originalName:isPdf?name:(existing?.originalName||existing?.name),originalType:isPdf?(mime||'application/pdf'):(existing?.originalType||existing?.type),origin:'user-local'};
  await put('sources',source);return source;
}
async function saveAnnotation(v){
  if(!v?.paperId||!Number.isInteger(v.page)||!Number.isInteger(v.start)||!Number.isInteger(v.end)||v.end<=v.start)throw Error('划线位置无效');
  const a={id:v.id||uid(),paperId:v.paperId,page:v.page,start:v.start,end:v.end,quote:String(v.quote||'').slice(0,4000),kind:['highlight','focus','underline','note'].includes(v.kind)?v.kind:'highlight',note:String(v.note||'').slice(0,10000),links:Array.isArray(v.links)?[...new Set(v.links.map(String))]:[],createdAt:v.createdAt||new Date().toISOString(),updatedAt:new Date().toISOString()};
  await put('annotations',a);return a;
}
async function linkAnnotations(aId,bId){
  if(!aId||!bId||aId===bId)return;
  const [a,b]=await Promise.all([getAnnotation(aId),getAnnotation(bId)]);
  if(!a||!b)throw Error('找不到要关联的便签');
  a.links=[...new Set([...(a.links||[]),bId])];b.links=[...new Set([...(b.links||[]),aId])];
  a.updatedAt=b.updatedAt=new Date().toISOString();
  await Promise.all([put('annotations',a),put('annotations',b)]);
}
function renderAnnotatedText(text,anns=[]){
  text=String(text||'');
  const valid=anns.filter(a=>Number.isInteger(a.start)&&Number.isInteger(a.end)&&a.start>=0&&a.end<=text.length&&a.end>a.start);
  const points=[0,text.length,...valid.flatMap(a=>[a.start,a.end])].sort((a,b)=>a-b).filter((v,i,x)=>i===0||v!==x[i-1]);
  let out='';
  for(let i=0;i<points.length-1;i++){
    const s=points[i],e=points[i+1];if(e<=s)continue;
    const active=valid.filter(a=>a.start<=s&&a.end>=e),seg=esc(text.slice(s,e));
    if(!active.length){out+=seg;continue;}
    const classes=[...new Set(active.map(a=>'ann-'+a.kind))].join(' '),ids=active.map(a=>a.id).join(','),title=active.map(a=>a.note).filter(Boolean).join(' ｜ ');
    out+=`<mark class="source-ann ${classes}" data-ann-ids="${esc(ids)}"${title?` title="${esc(title)}"`:''}>${seg}</mark>`;
  }
  return out;
}
function selectionOffsets(body,selection=window.getSelection()){
  if(!body||!selection||selection.rangeCount!==1||selection.isCollapsed)return null;
  const range=selection.getRangeAt(0);
  if(!body.contains(range.startContainer)||!body.contains(range.endContainer))return null;
  const pre=document.createRange();pre.selectNodeContents(body);pre.setEnd(range.startContainer,range.startOffset);
  const start=pre.toString().length,quote=range.toString(),end=start+quote.length;
  return quote.trim()?{start,end,quote}:null;
}
async function shareSource(paperId){
  const s=await getSource(paperId),blob=s?.originalBlob||s?.blob;if(!blob)throw Error('本机尚未保存原文件');
  const f=new File([blob],s.originalName||s.name||paperId,{type:s.originalType||s.type||'application/octet-stream'});
  if(navigator.share&&navigator.canShare?.({files:[f]})){await navigator.share({files:[f],title:s.title||s.name});return 'shared';}
  const u=URL.createObjectURL(f),a=document.createElement('a');a.href=u;a.download=f.name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),30000);return 'downloaded';
}
async function exportSource(paperId){
  const s=await getSource(paperId),blob=s?.originalBlob||s?.blob;if(!blob)throw Error('本机尚未保存原文件');
  const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download=s.originalName||s.name||paperId;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),30000);
}
window.PaperSourceReader={DB,MAX_BYTES,getSource,listSources,deleteSource,importFile,listAnnotations,getAnnotation,saveAnnotation,deleteAnnotation,linkAnnotations,renderAnnotatedText,selectionOffsets,shareSource,exportSource};
})();