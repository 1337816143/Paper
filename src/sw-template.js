'use strict';
const VERSION=__VERSION__;
const MANIFEST_SHA='__MANIFEST_SHA__';
const SCOPE=new URL(self.registration.scope),PREFIX='paper-lab:'+SCOPE.pathname+':';
// Content addressed objects are shared only within this exact Paper path scope.
const CACHE=PREFIX+'manifest-v3:'+MANIFEST_SHA,LIB=PREFIX+'sha256-v3';
const url=p=>new URL(p,SCOPE).href,objectKey=r=>url('.paper-offline/sha256/'+r.sha256);
const receipts=url('.paper-offline/verified-complete');
let manifestPromise=null,manifestRaw=null,operation=Promise.resolve();
const jobs=new Map(),inflight=new Map();
const checked=new Set();
const digest=async b=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b)),x=>x.toString(16).padStart(2,'0')).join('');
const send=(p,x)=>{try{p?.postMessage(x);}catch{}};
function serial(fn){const task=operation.then(fn);operation=task.catch(()=>{});return task;}
function within(u){return u.origin===SCOPE.origin&&u.pathname.startsWith(SCOPE.pathname);}
function validManifest(m){
 if(m.schema!=='paper.offline.v3'||m.version!==VERSION||!Array.isArray(m.resources))throw Error('离线清单版本不匹配');
 const seen=new Set();for(const r of m.resources){const u=new URL(r.url,SCOPE);if(!within(u)||u.search||u.hash||!r.url.startsWith('./')||r.url.includes('..')||seen.has(u.href)||!Number.isSafeInteger(r.bytes)||r.bytes<0||!/^[a-f0-9]{64}$/.test(r.sha256))throw Error('离线清单资源无效');seen.add(u.href);}
 if(!m.controls||m.controls.length!==1||m.controls[0].url!=='./sw.js'||m.controls[0].algorithm!=='sha256-zero-manifest-pin-v1')throw Error('离线控制协议无效');
 return m;
}
async function manifest(){
 if(!manifestPromise)manifestPromise=(async()=>{
  const c=await caches.open(CACHE);let r=await c.match(url('offline-manifest.json'));
  if(r&&await digest(await r.clone().arrayBuffer())!==MANIFEST_SHA)r=null;
  if(!r){r=await network(url('offline-manifest.json'));const b=await r.clone().arrayBuffer();if(await digest(b)!==MANIFEST_SHA)throw Error('离线清单SHA-256不匹配；部署可能尚未同步，请稍后重试');validManifest(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(b)));await c.put(url('offline-manifest.json'),r.clone());}
  const b=await r.arrayBuffer(),m=validManifest(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(b)));m.manifestBytes=b.byteLength;manifestRaw=b;return m;
 })().catch(e=>{manifestPromise=null;throw e;});return manifestPromise;
}
async function network(u,onChunk){
 const controller=new AbortController();let timer;const arm=()=>{clearTimeout(timer);timer=setTimeout(()=>controller.abort(),60000);};arm();
 try{const r=await fetch(new Request(u,{cache:'no-store',credentials:'same-origin',signal:controller.signal}));if(!r.ok||r.status!==200||r.type==='opaque')throw Error('HTTP '+r.status);
  if(!r.body)return r;
  const chunks=[],reader=r.body.getReader();let length=0;
  for(;;){const {done,value}=await reader.read();if(done)break;arm();chunks.push(value);length+=value.byteLength;onChunk?.(value.byteLength);}
  const body=new Blob(chunks);chunks.length=0;
  const headers=new Headers(r.headers);headers.delete('Content-Encoding');headers.delete('Transfer-Encoding');headers.set('Content-Length',String(length));
  return new Response(body,{status:200,headers});
 }finally{clearTimeout(timer);}
}
async function verify(r,spec){if(!r||r.status!==200)return false;const b=await r.clone().arrayBuffer();return b.byteLength===spec.bytes&&await digest(b)===spec.sha256;}
async function cached(spec,deep=false){const c=await caches.open(LIB),key=objectKey(spec),r=await c.match(key);if(!r)return null;

 if(await verify(r,spec)){checked.add(key);return r;}checked.delete(key);return null;
}
async function putVerified(spec,r){if(!await verify(r,spec))throw Error('SHA-256 / 字节数不匹配');
 const c=await caches.open(LIB);await c.put(objectKey(spec),r.clone());
 // Read back after put: a failed/quota-limited write cannot become a receipt.
 if(!await verify(await c.match(objectKey(spec)),spec))throw Error('缓存写后校验失败');checked.add(objectKey(spec));
}
async function obtainResource(spec,onChunk){
 if(await cached(spec,true))return false;
 // Migrate public legacy cache objects only after exact bytes pass the NEW hash.
 for(const name of await caches.keys())if(name.startsWith(PREFIX)&&name!==LIB&&name!==CACHE){const hit=await (await caches.open(name)).match(url(spec.url));if(hit&&await verify(hit,spec)){await putVerified(spec,hit);return false;}}
 const r=await network(url(spec.url),onChunk);await putVerified(spec,r);return true;
}
function obtain(spec,onChunk){const key=objectKey(spec);if(inflight.has(key))return inflight.get(key);const task=obtainResource(spec,onChunk).finally(()=>inflight.delete(key));inflight.set(key,task);return task;}
async function controlWorker(m,fetchMissing){
 const c=await caches.open(CACHE),u=url('sw.js'),spec=m.controls[0];let r=await c.match(u);
 async function valid(response){try{if(!response)return false;const b=new Uint8Array(await response.clone().arrayBuffer());if(b.byteLength!==spec.bytes)return false;
  const text=new TextDecoder('utf-8',{fatal:true}).decode(b),pattern=/const MANIFEST_SHA='([a-f0-9]{64})';/g,matches=[...text.matchAll(pattern)];
  if(matches.length!==1||matches[0][1]!==MANIFEST_SHA)return false;
  // ASCII pin only. Verify the UTF-8 round trip before canonicalizing raw bytes.
  const encoded=new TextEncoder().encode(text);if(encoded.length!==b.length||encoded.some((v,i)=>v!==b[i]))return false;
  const prefix=new TextEncoder().encode(text.slice(0,matches[0].index+"const MANIFEST_SHA='".length)).length;
  b.fill(48,prefix,prefix+64);return await digest(b)===spec.canonicalSha256;
 }catch{return false;}}
 if(r&&await valid(r))return r;
 if(!fetchMissing)throw Error('sw.js控制文件未通过完整性检查');
 r=await network(u);if(!await valid(r))throw Error('sw.js控制文件与此版本清单不一致');await c.put(u,r.clone());if(!await valid(await c.match(u)))throw Error('sw.js写后校验失败');return r;
}
async function manifestControl(repair=false){const c=await caches.open(CACHE),u=url('offline-manifest.json');let r=await c.match(u);if(r&&await digest(await r.clone().arrayBuffer())===MANIFEST_SHA)return r;
 if(!repair)throw Error('offline-manifest.json丢失或SHA-256不匹配');
 // The in-memory buffer was checked against the running worker pin at load time.
 if(manifestRaw&&await digest(manifestRaw)===MANIFEST_SHA)r=new Response(manifestRaw,{headers:{'Content-Type':'application/json'}});else r=await network(u);
 if(await digest(await r.clone().arrayBuffer())!==MANIFEST_SHA)throw Error('离线清单版本不一致');await c.put(u,r.clone());return r;
}
async function status(deep=false,notify=()=>{}){
 const m=await manifest(),c=await caches.open(LIB),keys=new Set((await c.keys()).map(x=>x.url));let count=0,verifiedBytes=0;const failed=[];
 for(const spec of m.resources){let good=keys.has(objectKey(spec));if(good&&deep)good=!!await cached(spec,true);if(good){count++;verifiedBytes+=spec.bytes;}else if(deep)failed.push({url:spec.url,error:keys.has(objectKey(spec))?'缓存字节或SHA-256不匹配':'尚未缓存',bytes:spec.bytes});
  if(deep)notify({type:'PROGRESS',phase:'verify',done:count,total:m.resources.length+2,verifiedBytes,totalBytes:m.bytes+m.controls[0].bytes+m.manifestBytes,failed:failed.length});
 }
 let controls=0;try{await manifestControl(false);controls++;}catch(e){if(deep)failed.push({url:'./offline-manifest.json',error:e.message,bytes:m.manifestBytes});}
 try{await controlWorker(m,false);controls++;}catch(e){if(deep)failed.push({url:'./sw.js',error:e.message,bytes:m.controls[0].bytes});}
 verifiedBytes+=(controls===2?m.manifestBytes+m.controls[0].bytes:0);count+=controls;
 const previous=await (await caches.open(CACHE)).match(receipts);let lastVerified=null;if(previous)try{lastVerified=(await previous.json()).at;}catch{}
 const allPresent=count===m.resources.length+2,complete=deep&&allPresent&&!failed.length;
 if(deep&&!complete){await (await caches.open(CACHE)).delete(receipts);lastVerified=null;}
 return {complete,mode:m.mode,allPresent,previouslyVerified:!!lastVerified,lastVerified,verification:deep?'sha256-all-resources':'inventory-only',count,expected:m.resources.length+2,version:VERSION,manifestSHA256:MANIFEST_SHA,verifiedBytes,totalBytes:m.bytes+m.controls[0].bytes+m.manifestBytes,sourceResources:m.library.length,failed};
}
async function cacheResources(ids,notify){
 const m=await manifest(),list=ids?m.resources.filter(r=>ids.includes(r.url)):m.resources;
 let done=0,verifiedBytes=0,transferredBytes=0;const failed=[],totalBytes=list.reduce((n,r)=>n+r.bytes,0);let cursor=0,quotaHit=false,lastUpdate=0;
 const update=(extra,force=false)=>{if(!force&&Date.now()-lastUpdate<150)return;lastUpdate=Date.now();notify({type:'PROGRESS',phase:'download',done,total:list.length,verifiedBytes,totalBytes,transferredBytes,failed:failed.length,...extra});};
 await Promise.all([0].map(async()=>{while(cursor<list.length){const spec=list[cursor++];if(quotaHit){failed.push({url:spec.url,bytes:spec.bytes,error:'容量不足后暂停，释放空间后可继续'});continue;}try{await obtain(spec,n=>{transferredBytes+=n;update({current:spec.url});});verifiedBytes+=spec.bytes;}catch(e){if(e.name==='QuotaExceededError')quotaHit=true;failed.push({url:spec.url,bytes:spec.bytes,error:e.name==='QuotaExceededError'?'QuotaExceededError: 浏览器空间不足；已保存内容和旧版保留':e.message});}done++;update({current:spec.url},true);}}));
 try{await manifestControl(true);await controlWorker(m,true);}catch(e){failed.push({url:'./sw.js',error:e.message,bytes:m.controls[0].bytes});}
 const result=await status(!ids,notify);
 // Only a full exact readback, not a URL count, produces a complete checkpoint.
 if(result.complete){const c=await caches.open(CACHE);try{await c.put(receipts,new Response(JSON.stringify({manifestSHA256:MANIFEST_SHA,at:new Date().toISOString()}),{headers:{'Content-Type':'application/json'}}));}catch(e){failed.push({url:'offline checkpoint',error:e.message});result.complete=false;}}
 // No automatic deletion: old versions, other scopes and all private DBs survive failures.
 return {type:'DONE',...result,failed:[...failed,...result.failed.filter(r=>!failed.some(f=>f.url===r.url))],done,total:list.length,transferredBytes};
}
function queued(port,fn){send(port,{type:'PROGRESS',phase:'queued',done:0,total:0});const timer=setInterval(()=>send(port,{type:'PROGRESS',phase:'queued',done:0,total:0}),15000);return serial(()=>{clearInterval(timer);return fn();}).finally(()=>clearInterval(timer));}
function startJob(ids,port){
 const key=ids?JSON.stringify(ids):'all';
 if(jobs.has(key)){const job=jobs.get(key);job.ports.add(port);if(job.latest)send(port,job.latest);return job.promise;}
 const job={key,ports:new Set([port]),latest:null};const notify=x=>{job.latest=x;for(const p of job.ports)send(p,x);};
 job.promise=queued({postMessage:notify},()=>cacheResources(ids,notify)).then(x=>{notify(x);return x;}).catch(e=>notify({type:'DONE',complete:false,failed:[{url:'offline-manifest.json',error:e.message}],error:e.message})).finally(()=>{jobs.delete(key);});jobs.set(key,job);return job.promise;
}
self.addEventListener('install',e=>e.waitUntil(serial(async()=>{const m=await manifest();for(const spec of m.resources.filter(r=>r.kind==='core'))await obtain(spec);await controlWorker(m,true);})));
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
self.addEventListener('message',e=>{
 const t=e.data?.type,p=e.ports[0];
 if(t==='STATUS'||t==='STATUS_FAST')e.waitUntil((t==='STATUS_FAST'?status(false):queued(p,()=>status(true,x=>send(p,x)))).then(s=>send(p,{type:'DONE',...s})).catch(err=>send(p,{type:'DONE',complete:false,error:err.message,failed:[{url:'offline-manifest.json',error:err.message}]})));
 if(t==='CACHE_ALL')e.waitUntil(startJob(null,p));
 if(t==='CACHE_BOOK')e.waitUntil(manifest().then(m=>{const ids=m.books[e.data.id];if(!ids?.length){send(p,{type:'DONE',complete:false,failed:[{url:String(e.data.id),error:'没有已合法归档的资源清单'}]});return;}return startJob(ids,p);}));
});
async function ranged(hit,range){
 if(!range)return hit;const match=/^bytes=(\d*)-(\d*)$/.exec(range);if(!match||!match[1]&&!match[2])return hit;
 const bytes=await hit.arrayBuffer(),length=bytes.byteLength;let start=match[1]?Number(match[1]):Math.max(0,length-Number(match[2])),end=match[1]?(match[2]?Math.min(Number(match[2]),length-1):length-1):length-1;
 if(start>end||start>=length||!Number.isSafeInteger(start)||!Number.isSafeInteger(end))return new Response(null,{status:416,headers:{'Content-Range':'bytes */'+length}});
 const h=new Headers(hit.headers);h.delete('Content-Encoding');h.set('Content-Range',`bytes ${start}-${end}/${length}`);h.set('Content-Length',String(end-start+1));h.set('Accept-Ranges','bytes');return new Response(bytes.slice(start,end+1),{status:206,headers:h});
}
self.addEventListener('fetch',e=>{
 const u=new URL(e.request.url);if(e.request.method!=='GET'||!within(u))return;
 e.respondWith((async()=>{
  // Release probes must reach the server; never cache future bytes in the installed release.
  if(u.pathname===new URL('release.json',SCOPE).pathname&&u.searchParams.has('release-check'))try{return await fetch(e.request);}catch{}
  u.search='';u.hash='';if(u.pathname.endsWith('/'))u.pathname+='index.html';
  const m=await manifest(),spec=m.resources.find(r=>url(r.url)===u.href);
  if(spec){let hit=await cached(spec);if(!hit){try{await obtain(spec);hit=await cached(spec);}catch{return new Response('此资源未通过当前版本完整性校验。联网后在离线中心重试；旧版与私人笔记仍保留。',{status:503,headers:{'Content-Type':'text/plain;charset=utf-8'}});}}return ranged(hit,e.request.headers.get('Range'));}
  if(u.href===url('offline-manifest.json'))return manifestControl(false);
  if(u.href===url('sw.js'))return controlWorker(m,false);
  try{return await fetch(e.request);}catch{return new Response('这项在线服务或资源不在已部署离线清单内。',{status:503,headers:{'Content-Type':'text/plain;charset=utf-8'}});}
 })().catch(()=>new Response('离线清单暂不可用；请联网重试。',{status:503,headers:{'Content-Type':'text/plain;charset=utf-8'}})));
});
/* Negotiate with every same-scope page before switching code beneath it. */
async function safeActivate(event){
 const sender=event.source;try{const u=new URL(sender?.url||'');if(u.origin!==SCOPE.origin||!u.pathname.startsWith(SCOPE.pathname))return;}catch{return;}
 const windows=(await self.clients.matchAll({type:'window',includeUncontrolled:true})).filter(c=>{try{const u=new URL(c.url);return u.origin===SCOPE.origin&&u.pathname.startsWith(SCOPE.pathname);}catch{return false;}});
 const answers=await Promise.all(windows.map(c=>new Promise(resolve=>{const channel=new MessageChannel();const timer=setTimeout(()=>{channel.port1.close();resolve({ready:false,reason:'另一个标签页尚未支持安全更新，请关闭不用的旧标签页'});},2500);channel.port1.onmessage=e=>{clearTimeout(timer);channel.port1.close();resolve(e.data?.ready===true?{ready:true}:{ready:false,reason:e.data?.reason||'其他标签页正在使用'});};c.postMessage({type:'PAPER_CAN_UPDATE',version:VERSION},[channel.port2]);})));
 const blocked=answers.find(a=>!a.ready);event.ports[0]?.postMessage(blocked?{accepted:false,reason:blocked.reason}:{accepted:true,version:VERSION});if(!blocked)await self.skipWaiting();
}
self.addEventListener('message',e=>{if(e.data?.type==='PAPER_SAFE_ACTIVATE')e.waitUntil(safeActivate(e));});
