/* Runs the real shared download handler against DOM/fetch fixtures, not a browser. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const source=fs.readFileSync('src/offline-downloads.js','utf8');
const root='https://paper.test/Paper/',zip=Buffer.from('synthetic ZIP bytes'),hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const manifest=Buffer.from(JSON.stringify({schema:'paper.offline.v3',resources:[{url:'./downloads/test.zip',bytes:zip.length,sha256:hash(zip)}]}));
let listener,bad=false,wrongPin=false,hold=null,fetchCount=0;const elements=new Map(),downloads=[],blobs=[],timers=new Map();let timerID=0;
class Element{constructor(tag){this.tagName=tag;this.attrs={};this.textContent='';this.style={};this.isConnected=true;}setAttribute(n,v){this.attrs[n]=v;}getAttribute(n){return this.attrs[n]??null;}removeAttribute(n){delete this.attrs[n];}closest(selector){return selector==='a[download]'?this:null;}after(e){e.placedAfter=this;if(e.id)elements.set(e.id,e);}prepend(e){this.append(e);}append(e){if(e.id)elements.set(e.id,e);}remove(){}click(){downloads.push({href:this.href,name:this.download});}}
const body=new Element('body'),document={currentScript:{src:root+'offline-downloads.js'},body,querySelector:()=>body,getElementById:id=>elements.get(id),createElement:tag=>new Element(tag),addEventListener:(name,fn)=>{assert.equal(name,'click');listener=fn;}};
class Channel{constructor(){this.port1={close(){}};this.port2={close(){},postMessage:data=>queueMicrotask(()=>this.port1.onmessage?.({data}))};}}
const URLFixture=class extends URL{};URLFixture.createObjectURL=blob=>{const u=URL.createObjectURL(blob);blobs.push(u);return u;};URLFixture.revokeObjectURL=u=>URL.revokeObjectURL(u);
const context=vm.createContext({window:{},document,location:{href:root+'downloads/index.html',protocol:'https:'},navigator:{serviceWorker:{controller:{postMessage:(data,ports)=>ports[0].postMessage({type:'DONE',manifestSHA256:wrongPin?'0'.repeat(64):hash(manifest)})}}},URL:URLFixture,crypto:crypto.webcrypto,MessageChannel:Channel,TextDecoder,Blob,AbortController,Uint8Array,setTimeout:(fn,ms)=>{timers.set(++timerID,{fn,ms});return timerID;},clearTimeout:id=>timers.delete(id),fetch:async url=>{fetchCount++;if(hold)await hold;const path=String(url);if(path===root+'offline-manifest.json')return new Response(manifest,{headers:{'Content-Type':'application/json'}});if(path===root+'downloads/test.zip')return new Response(bad?Buffer.alloc(zip.length,88):zip,{headers:{'Content-Type':'application/zip'}});throw Error('Unexpected request '+path);}});
vm.runInContext(source,context);
const safeName=vm.runInNewContext('('+source.match(/function safeName\(url\)\{.*$/m)[0]+')');
assert.equal(safeName(new URL(root+'downloads/CON.zip')),'paper-CON.zip');
assert.equal(safeName(new URL(root+'downloads/a%2Fb%5Cc%00.zip')),'a_b_c_.zip');
assert.equal(safeName(new URL(root+'downloads/%E2%80%AEhtml.zip')),'_html.zip');

function click(href){const a=new Element('a');a.href=href;a.attrs.download='';let prevented=false;const event={target:a,button:0,preventDefault(){prevented=true;}};return {a,event,run:()=>listener(event),prevented:()=>prevented};}
(async()=>{try{
 for(const url of ['blob:https://paper.test/fake','data:text/plain,private-note','https://paper.test/Farm/file.zip','https://outside.test/file.zip']){const c=click(url);await c.run();assert.equal(c.prevented(),false);}
 assert.equal(fetchCount,0,'Never request blob/data/private exports or other scopes');
 const first=click(root+'downloads/test.zip');await first.run();assert(first.prevented());assert.equal(context.window.PaperDownloads.state().transport,'verified-fetch-to-blob');assert.equal(context.window.PaperDownloads.isBusy(),false);assert.equal(downloads.length,1);assert(downloads[0].href.startsWith('blob:'));const firstBlob=await fetch(downloads[0].href);assert.equal(firstBlob.headers.get('Content-Type'),'application/octet-stream');assert.deepEqual(Buffer.from(await firstBlob.arrayBuffer()),zip);assert.equal(first.a.getAttribute('aria-busy'),null);assert.equal(elements.get('paper-download-status').placedAfter,first.a,'Feedback is beside the actual triggering link');context.window.PaperDownloads.onRoute();assert(context.window.PaperDownloads.state().message.includes('test.zip'),'Route changes retain the original download identity');
 const control=click(root+'offline-manifest.json');await control.run();assert.equal(context.window.PaperDownloads.state().integrity,'worker-pinned-manifest');assert.deepEqual(Buffer.from(await(await fetch(downloads[1].href)).arrayBuffer()),manifest);
 bad=true;await click(root+'downloads/test.zip').run();assert.equal(downloads.length,2);assert.equal(context.window.PaperDownloads.state().state,'error');assert.equal(context.window.PaperDownloads.isBusy(),false);bad=false;await click(root+'downloads/test.zip').run();assert.equal(downloads.length,3);
 wrongPin=true;await click(root+'downloads/test.zip').run();assert.equal(downloads.length,3);assert(context.window.PaperDownloads.state().message.includes('清单与已安装离线版本不一致'));wrongPin=false;
 await click(root+'downloads/not-in-manifest.zip').run();assert.equal(downloads.length,3);assert(context.window.PaperDownloads.state().message.includes('当前版本未包含'));
 let resume;hold=new Promise(resolve=>resume=resolve);const pending=click(root+'downloads/test.zip').run();assert.equal(context.window.PaperDownloads.isBusy(),true);await click(root+'downloads/test.zip').run();assert.equal(downloads.length,3);hold=null;resume();await pending;assert.equal(downloads.length,4);assert.equal(context.window.PaperDownloads.isBusy(),false);
 const normalPost=context.navigator.serviceWorker.controller.postMessage;const timerCount=timers.size;context.navigator.serviceWorker.controller.postMessage=()=>{throw Error('synthetic port failure');};await click(root+'downloads/test.zip').run();assert.equal(context.window.PaperDownloads.isBusy(),false);assert.equal(timers.size,timerCount,'Synchronous postMessage failure must clear its timer');context.navigator.serviceWorker.controller.postMessage=normalPost;
 const savedController=context.navigator.serviceWorker.controller;context.navigator.serviceWorker.controller=null;await click(root+'offline-manifest.json').run();assert.equal(context.window.PaperDownloads.state().integrity,'HTTPS-control-response');assert(context.window.PaperDownloads.state().message.includes('原始清单已取得'));context.navigator.serviceWorker.controller=savedController;
 assert([...timers.values()].every(x=>x.ms===60000),'Only delayed Blob releases remain, not read timeouts');for(const {fn} of [...timers.values()])fn();assert.equal(timers.size,downloads.length); // Fake timer registry does not auto-remove fired handles.
 // The same handler is inlined in downloads/Paper-Lab-offline.html. Its
 // explicit build-time root must resolve to the site, not downloads/.
 document.currentScript={src:'',dataset:{paperRoot:'../'}};
 context.location.href=root+'downloads/Paper-Lab-offline.html';
 vm.runInContext(source,context);
 const inlineCount=downloads.length;await click(root+'offline-manifest.json').run();
 assert.equal(downloads.length,inlineCount+1);assert.equal(context.window.PaperDownloads.state().integrity,'worker-pinned-manifest');
 await click(root+'downloads/test.zip').run();assert.equal(downloads.length,inlineCount+2);
 // file: single HTML has embedded teaching downloads, no hosted manifest fetch.
 const fileFetches=fetchCount;listener=null;delete context.window.PaperDownloads;
 context.location.href='file:///saved/Paper-Lab-offline.html';context.location.protocol='file:';
 vm.runInContext(source,context);assert.equal(listener,null);assert.equal(context.window.PaperDownloads,undefined);assert.equal(fetchCount,fileFetches);
 console.log('PASS real download-handler VM: exact Blob bytes, pinned manifest, wrong bytes/pin rejection, retry, duplicate busy guard, delayed release, blob/data/external/scope exclusion (not browser acceptance)');
 }finally{for(const u of blobs)URL.revokeObjectURL(u);}})().catch(e=>{console.error(e);process.exitCode=1;});
