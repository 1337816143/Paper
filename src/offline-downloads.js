/* Same-scope hosted downloads use verified bytes and a Blob URL. Native network
   download navigation is not a reliable service-worker offline read path. */
(()=>{'use strict';
 if(!/^https?:$/.test(location.protocol))return;
 const root=new URL('.',document.currentScript?.src||location.href);
 const manifestURL=new URL('offline-manifest.json',root);
 let busy=false,last={state:'idle'},activeTrigger=null,releaseTimers=new Set();
 const digest=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
 function tell(message,state,trigger=activeTrigger){let el=document.getElementById('paper-download-status');if(!el){el=document.createElement('p');el.id='paper-download-status';el.setAttribute('role','status');el.style.overflowWrap='anywhere';}const near=trigger?.isConnected&&(trigger.closest('.actions')||trigger.closest('p')||trigger);if(near)near.after(el);else(document.querySelector('main')||document.body).prepend(el);el.textContent=message;const box=el.getBoundingClientRect?.();if(box&&(box.top>=innerHeight||box.bottom<=0))el.scrollIntoView({block:'nearest'});last={...last,state,message};}
 async function installedPin(){const worker=navigator.serviceWorker?.controller;if(!worker)return null;return new Promise((resolve,reject)=>{const channel=new MessageChannel(),timer=setTimeout(()=>{channel.port1.close();reject(Error('当前离线版本校验响应超时，请稍后重试'));},15000);channel.port1.onmessage=e=>{if(e.data.type==='PROGRESS')return;clearTimeout(timer);channel.port1.close();const pin=e.data.manifestSHA256;if(!/^[a-f0-9]{64}$/.test(pin||'')){reject(Error('离线服务未提供清单校验值，请先更新完整缓存'));return;}resolve(pin);};try{worker.postMessage({type:'STATUS_FAST'},[channel.port2]);}catch(error){clearTimeout(timer);channel.port1.close();channel.port2.close();reject(error);}});}
 function safeName(url){let name=url.pathname.split('/').pop()||'paper-download.bin';try{name=decodeURIComponent(name);}catch{}name=name.replace(/[\\/\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]/g,'_').replace(/[. ]+$/g,'');if(!name||/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(name))name='paper-'+(name||'download.bin');return name;}
 async function read(url,signal){const r=await fetch(url,{cache:'no-store',credentials:'same-origin',signal});if(r.status!==200)throw Error('HTTP '+r.status+'：文件尚未完整缓存或不可用');return {bytes:await r.arrayBuffer(),type:r.headers.get('Content-Type')||'application/octet-stream'};}
 document.addEventListener('click',async event=>{
  const link=event.target?.closest?.('a[download]');
  if(!link||event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
  const target=new URL(link.href,location.href);
  if(!/^https?:$/.test(target.protocol)||target.origin!==root.origin||!target.pathname.startsWith(root.pathname))return;
  event.preventDefault();if(busy){tell('正在准备上一份下载，请稍候再点下一份。','preparing',link);return;}
  busy=true;activeTrigger=link;link.setAttribute('aria-busy','true');link.setAttribute('aria-disabled','true');
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),180000);
  const name=safeName(target);
  last={state:'preparing',name};tell('正在读取并核验 '+name+'；准备完成后会交给浏览器保存。','preparing');
  try{
   target.search='';target.hash='';
   const manifest=await read(manifestURL,controller.signal);
   const pin=await installedPin();if(pin&&await digest(manifest.bytes)!==pin)throw Error('清单与已安装离线版本不一致，请完整缓存后重试');
   const data=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(manifest.bytes));
   if(data.schema!=='paper.offline.v3'||!Array.isArray(data.resources))throw Error('离线资源清单无效');
   const isManifest=target.href===manifestURL.href;
   const spec=data.resources.find(r=>new URL(r.url,root).href===target.href);
   if(!isManifest&&!spec)throw Error('当前版本未包含这个文件；解压版不递归包含ZIP，请查看下载说明');
   const file=isManifest?manifest:await read(target,controller.signal);
   const hash=await digest(file.bytes);
   if(spec&&(file.bytes.byteLength!==spec.bytes||hash!==spec.sha256))throw Error('文件字节数或SHA-256校验失败；请联网完整缓存后重试');
   // The manifest itself is the exact control response validated by the installed
   // worker, or by normal HTTPS when first visiting online; it cannot self-hash.
   const blob=new Blob([file.bytes],{type:'application/octet-stream'}),blobURL=URL.createObjectURL(blob);
   const revoke=setTimeout(()=>{URL.revokeObjectURL(blobURL);releaseTimers.delete(revoke);},60000);releaseTimers.add(revoke);
   const a=document.createElement('a');a.href=blobURL;a.download=name;a.hidden=true;document.body.append(a);try{a.click();}finally{a.remove();}
   last={state:'dispatched',name,bytes:file.bytes.byteLength,sha256:hash,transport:'verified-fetch-to-blob',integrity:isManifest?(pin?'worker-pinned-manifest':'HTTPS-control-response'):'manifest-bytes-sha256'};
   tell(name+(isManifest&&!pin?' 原始清单已取得并交给浏览器保存（':' 已核验并交给浏览器保存（')+(file.bytes.byteLength/1048576).toFixed(1)+' MiB）；请在浏览器下载列表确认保存完成。','dispatched');
  }catch(error){tell('下载未完成：'+(error.name==='AbortError'?'读取超时':error.message)+'。已缓存内容保留，可重试。','error');}
  finally{clearTimeout(timer);busy=false;link.removeAttribute('aria-busy');link.removeAttribute('aria-disabled');}
 });
 window.PaperDownloads={isBusy:()=>busy,state:()=>({...last}),onRoute:()=>{if(last.message){activeTrigger=null;tell(last.message,last.state);}}};
})();
