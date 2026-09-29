/* Automatic releases never embed authorization or equate code version with saved notes. */
(()=>{'use strict';
const $=s=>document.querySelector(s), D=window.PAPER_DATA, meta=D.application||{version:'开发版',date:D.updated,changes:[]};
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const scopeKey='paper-release-v51:'+new URL('.',location.href.split('#')[0]).pathname;
let registration=null,savePosition=()=>{},lastActivity=Date.now()-16000,checking=false,applying=false,reloading=false,lastCheck=0,cacheBusy=false,needsReload=false;
let current={status:'current',message:'当前已安装版本',available:null,lastChecked:null},hadController=!!navigator.serviceWorker?.controller;
function settings(){try{return JSON.parse(localStorage.getItem(scopeKey)||'{}');}catch{return {};}}
function remember(patch){try{localStorage.setItem(scopeKey,JSON.stringify({...settings(),...patch}));}catch{}}
function report(patch){current={...current,...patch};const badge=$('#release-badge');if(badge){badge.dataset.status=current.status;badge.title=current.message;badge.textContent='v'+meta.version+(current.available?' · 新版':'');}const status=$('#release-message');if(status)status.textContent=current.message;const pending=$('#release-available');if(pending)pending.textContent=current.available?'可用版本：'+(current.available.appVersion||current.available.version):'未发现新版本';}
function safeToReload(){
 if(Date.now()-lastActivity<12000)return {ready:false,reason:'等待你暂停操作后自动更新'};
 if(getSelection()?.toString().trim())return {ready:false,reason:'正在选择文字，稍后自动更新'};
 if(document.querySelector('dialog[open],.context-popover,.term-popover,#translation-editor,#release-panel'))return {ready:false,reason:'正在查看或编辑弹窗，稍后自动更新'};
 const a=document.activeElement;if(a&&(a.matches('input,textarea,select')||a.isContentEditable))return {ready:false,reason:'正在输入，已保留当前页面'};
 if(window.PaperResearch?.hasUnsaved?.())return {ready:false,reason:'研究备注尚未确认本机保存，暂不更新'};
 if(window.PaperWorkspace?.isBusy?.())return {ready:false,reason:'正在处理导入或检索，完成后更新'};
 if(window.PaperStudy?.isBusy?.())return {ready:false,reason:'正在处理本机翻译，完成后更新'};
 const s=window.PaperSync?.status?.();if(s?.busy)return {ready:false,reason:'正在保存云端检查点，完成后更新'};
 // v5 keeps authorization only in page memory. Never silently destroy that session.
 if(s?.connected&&!window.PaperPersonal?.safeToReload?.())return {ready:false,reason:'云端会话仍在连接；新版本已准备，断开会话或下次打开时应用'};
 if(document.querySelector('#import-progress'))return {ready:false,reason:'导入页面仍打开，返回阅读后自动更新'};
 return {ready:true,reason:''};
}
function message(worker,data,timeout=7000){return new Promise((ok,no)=>{if(!worker){no(Error('离线服务暂未就绪'));return;}const channel=new MessageChannel(),timer=setTimeout(()=>{channel.port1.close();no(Error('更新服务响应超时；原版本继续可用'));},timeout);channel.port1.onmessage=e=>{clearTimeout(timer);channel.port1.close();ok(e.data);};worker.postMessage(data,[channel.port2]);});}
async function inspectCache(){if(!registration?.active)return;try{const r=await message(registration.active,{type:'STATUS'});if(r.complete)remember({fullCache:true});return r;}catch{return null;}}
async function restoreFullCache(){
 if(cacheBusy||!settings().fullCache||!navigator.onLine||!registration?.active)return;
 const s=await inspectCache();if(!s||s.complete)return;cacheBusy=true;const ch=new MessageChannel();let timer;
 const finish=()=>{clearTimeout(timer);ch.port1.close();cacheBusy=false;};timer=setTimeout(finish,900000);
 ch.port1.onmessage=e=>{if(e.data.type==='DONE'){const x=e.data;finish();remember({lastCacheVersion:x.complete?D.version:settings().lastCacheVersion});if(x.complete)report({message:'已更新；新增离线资源也已补齐'});else report({message:'程序已更新；离线资源尚未齐全，联网后自动重试'});}};
 registration.active.postMessage({type:'CACHE_ALL'},[ch.port2]);
}
function reloadSafely(){needsReload=true;if(reloading)return;const safe=safeToReload();if(!safe.ready){report({status:'deferred',message:safe.reason});return;}try{savePosition();window.PaperReader?.beforeNavigate();}catch{report({status:'deferred',message:'尚未确认阅读位置保存，暂不刷新'});return;}reloading=true;remember({reloadTarget:current.available?.version||'',returnURL:location.href,returnY:scrollY});location.reload();}
async function maybeApply(){
 if(!registration?.waiting||applying||!navigator.onLine)return;
 const safe=safeToReload();if(!safe.ready){report({status:'deferred',message:safe.reason});return;}
 applying=true;try{await inspectCache();const r=await message(registration.waiting,{type:'PAPER_SAFE_ACTIVATE'},6000);if(!r.accepted){report({status:'deferred',message:r.reason||'其他阅读标签页仍在使用，安全后自动更新'});return;}report({status:'applying',message:'阅读位置已保存，正在自动应用新版'});}catch(e){report({status:'deferred',message:e.message});}finally{applying=false;}
}
async function check(force=false){
 if(checking||!navigator.onLine||!registration||!force&&Date.now()-lastCheck<120000)return;checking=true;lastCheck=Date.now();
 try{const c=new AbortController(),t=setTimeout(()=>c.abort(),20000);let r;try{const u=new URL('release.json',location.href.split('#')[0]);u.searchParams.set('release-check',String(Date.now()));const response=await fetch(u,{cache:'no-store',credentials:'omit',signal:c.signal});if(response.ok)r=await response.json();}finally{clearTimeout(t);}if(r&&typeof r.version==='string'){report({available:r.version!==D.version?{version:r.version,appVersion:r.appVersion||r.application?.version}:null,lastChecked:new Date().toISOString()});}
 await registration.update();if(registration.waiting){report({status:'available',message:'新版本已下载，正在等待安全更新时机'});await maybeApply();}else if(!current.available)report({status:'current',message:'已检查，当前为最新发布内容'});
 }catch{report({status:'offline',message:'暂时无法核验新版本；已安装内容和笔记保留'});}finally{checking=false;}
}
function show(){
 $('#release-panel')?.remove();const p=document.createElement('aside');p.id='release-panel';p.className='release-panel';p.setAttribute('role','dialog');p.setAttribute('aria-label','版本与更新');p.innerHTML=`<div class="popover-head"><h2>版本与自动更新</h2><button id="release-close" aria-label="关闭版本说明">×</button></div><strong>Paper Lab v${E(meta.version)}</strong><p>发布说明日期：${E(meta.date)}<br>内容校验值：<code>${E(D.version)}</code></p><p id="release-available"></p><p id="release-message" role="status"></p><div class="release-changes">${(meta.changes||[]).map(s=>'<p>'+E(s)+'</p>').join('')}</div><button id="release-check">立即检查</button><p class="release-boundary">版本号表示程序更新，不表示私人笔记已上云。云端状态请看顶部同步标记。当前免填令牌登录仍待安全服务端接入，不能把授权写进公开网页。</p>`;document.body.append(p);const box=$('#release-badge').getBoundingClientRect();p.style.top=Math.min(box.bottom+10,innerHeight-220)+'px';p.style.right='14px';$('#release-close').onclick=()=>p.remove();$('#release-check').onclick=()=>check(true);report({});
 setTimeout(()=>{const close=e=>{if(!p.isConnected){document.removeEventListener('pointerdown',close,true);return;}if(!p.contains(e.target)&&!e.target.closest('#release-badge')){p.remove();document.removeEventListener('pointerdown',close,true);}};document.addEventListener('pointerdown',close,true);},0);
}
function init(options={}){
 savePosition=options.savePosition||(()=>{});const badge=document.createElement('button');badge.id='release-badge';badge.className='release-badge';badge.type='button';badge.setAttribute('aria-label','查看版本与更新');badge.onclick=show;$('.brand')?.after(badge);report({});const footer=$('#version');if(footer)footer.textContent=`Paper Lab v${meta.version} · ${meta.date} · ${D.version}`;
 const old=$('#update-banner');if(old){old.hidden=true;old.classList.add('auto-release-banner');}if($('#apply-update'))$('#apply-update').onclick=()=>{lastActivity=0;maybeApply();};if($('#check-update'))$('#check-update').onclick=()=>check(true);
 for(const event of ['pointerdown','keydown','input','scroll'])document.addEventListener(event,()=>{lastActivity=Date.now();},{passive:true,capture:true});
 document.addEventListener('keydown',e=>{if(e.key==='Escape')$('#release-panel')?.remove();});
 if(!('serviceWorker'in navigator)||location.protocol==='file:'){report({status:'offline',message:'本地文件版；联网网页版会自动检查更新'});return;}
 navigator.serviceWorker.addEventListener('message',async e=>{if(e.data?.type!=='PAPER_CAN_UPDATE')return;const safe=safeToReload();if(safe.ready){try{savePosition();window.PaperReader?.beforeNavigate();}catch{safe.ready=false;safe.reason='阅读位置尚未保存';}}e.ports[0]?.postMessage(safe);});
 navigator.serviceWorker.addEventListener('controllerchange',()=>{if(!hadController){hadController=true;return;}reloadSafely();});
 navigator.serviceWorker.register('./sw.js',{scope:'./',updateViaCache:'none'}).then(async r=>{registration=r;await navigator.serviceWorker.ready;await inspectCache();restoreFullCache();check(true);r.addEventListener('updatefound',()=>{const w=r.installing;w?.addEventListener('statechange',()=>{if(w.state==='installed'&&r.waiting){report({status:'available',message:'新版本已准备，暂停操作后自动更新'});maybeApply();}});});}).catch(()=>report({status:'offline',message:'离线更新服务暂不可用；不影响已有笔记'}));
 addEventListener('online',()=>{check(true);restoreFullCache();});document.addEventListener('visibilitychange',()=>{if(!document.hidden){check();maybeApply();}});
 setInterval(()=>{if(!document.hidden){check();if(needsReload)reloadSafely();else maybeApply();}},15000);setInterval(()=>restoreFullCache(),180000);
}
window.PaperRelease={init,check,maybeApply,safeToReload,state:()=>({...current,appVersion:meta.version,buildVersion:D.version}),version:meta.version};
})();
