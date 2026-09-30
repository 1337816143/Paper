import {createOAuthClient,encryptedDeviceStore} from './oauth-client.mjs';

const dedicated=(location.protocol==='https:'||location.hostname==='127.0.0.1')
  && !location.hostname.endsWith('.github.io') && location.protocol!=='file:';
let available=false;
if(dedicated){
  try{available=localStorage.getItem('paper-oauth-host-v1')===location.origin;}catch{}
  try{const response=await fetch('/auth/config',{cache:'no-store',credentials:'omit'});if(response.ok&&(await response.json()).mode==='github-app'){available=true;try{localStorage.setItem('paper-oauth-host-v1',location.origin);}catch{}}}catch{}
}
if(available&&window.PaperSync){
  document.body.classList.add('oauth-host');
  const store=encryptedDeviceStore({indexedDB,crypto});
  const client=createOAuthClient({gateway:location.origin,siteOrigin:location.origin,sync:window.PaperSync,store});
  let working=false,saved=false,notice='';
  const sync=()=>window.PaperSync.status();
  const panel=()=>document.querySelector('#paper-oauth-panel');
  function mount(){
    if(location.hash!=='#/sync')return;
    const view=document.querySelector('#view');
    if(!view||panel())return;
    const section=document.createElement('section');
    section.id='paper-oauth-panel';section.className='card paper-oauth-panel';
    section.innerHTML='<div class="paper-oauth-heading"><div><span class="eyebrow">PRIVATE GITHUB VAULT</span><h2>一次登录，自动恢复私人笔记</h2></div><span id="paper-oauth-badge" class="paper-oauth-badge" role="status"></span></div><p>新设备首次使用时，登录你的 GitHub 账号并授权指定私有仓库。以后打开这个专属站点，浏览器会自动恢复连接。只有实际写入并读回后，才显示“云端已确认”。</p><p id="paper-oauth-message" class="paper-oauth-message" role="status" aria-live="polite"></p><div class="actions paper-oauth-actions"><button id="paper-oauth-login" class="primary" type="button">使用 GitHub 登录</button><button id="paper-oauth-sync" type="button">立即核对云端</button><button id="paper-oauth-forget" type="button">移除此设备登录</button></div><details><summary>换设备前要知道</summary><p>旧网址和新网址的本机笔记不会自动搬迁。请先在旧设备导出完整个人备份，或确认旧站已显示“云端已确认”；新设备首次登录后再导入备份或从云端恢复。离线修改仍保存在本机，联网后以顶部同步状态为准。</p></details>';
    view.prepend(section);
    section.querySelector('#paper-oauth-login').onclick=async()=>{working=true;notice='正在打开 GitHub 登录…';draw();try{await client.login();saved=true;notice='';}catch(e){saved=!!await store.read().catch(()=>null);notice=e.message;}finally{working=false;draw();}};
    section.querySelector('#paper-oauth-sync').onclick=async()=>{working=true;notice='正在核对云端…';draw();try{await window.PaperSync.sync();notice='';}catch(e){notice=e.message;}finally{working=false;draw();}};
    section.querySelector('#paper-oauth-forget').onclick=async()=>{if(!confirm('只移除此设备的登录授权；本机笔记与云端数据都保留。继续？'))return;working=true;draw();try{await client.forget();saved=false;notice='此设备已退出；笔记仍保留。';}catch(e){notice=e.message;}finally{working=false;draw();}};
    draw();
  }
  function draw(){
    const p=panel();if(!p)return;
    const state=sync(),badge=p.querySelector('#paper-oauth-badge');
    const cloud=state.state==='synced';
    badge.dataset.state=cloud?'synced':state.state;
    badge.textContent=cloud?'云端已确认':state.busy?'正在核对':state.state==='error'?'同步失败':state.state==='offline'?'离线待同步':state.connected?'等待云端确认':saved?'等待自动恢复':'仅保存在本机';
    p.querySelector('#paper-oauth-message').textContent=notice||state.message;
    p.querySelector('#paper-oauth-login').disabled=working;
    p.querySelector('#paper-oauth-sync').disabled=working||!state.connected||state.busy;
    p.querySelector('#paper-oauth-forget').disabled=working||!saved;
  }
  window.PaperOAuth={client,status:()=>({saved,working,...client.status()}),safeToReload:()=>!working&&!sync().busy&&!sync().dirty&&client.status().connected};
  new MutationObserver(mount).observe(document.querySelector('#view'),{childList:true});
  addEventListener('hashchange',()=>{queueMicrotask(mount);});
  document.addEventListener('paper-sync-status',draw);
  addEventListener('online',()=>{if(saved&&!sync().connected)client.resume().then(draw).catch(e=>{notice=e.message;draw();});});
  mount();
  (async()=>{try{saved=!!await store.read();if(saved){notice='正在自动恢复 GitHub 连接…';draw();await client.resume();notice='';}}catch(e){notice=e.message;}finally{draw();}})();
}

