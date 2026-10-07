/* Runtime-only tools for stable method-transfer blocks; no storage or text rewrites. */
(()=>{'use strict';
function parseTarget(hash,paper){
  if(!/^[a-z0-9-]+$/.test(paper))return null;
  const parts=String(hash||'').replace(/^#\//,'').split('/');
  if(parts.length!==2||parts[0]!==paper)return null;
  const base='method-transfer-'+paper,target=parts[1];
  return target===base||target.startsWith(base+'-')?target:null;
}
function sourceAccess(record,standalone=false){
  const result=record?.bookPath?{
    kind:'public-archive',label:'站内归档原文（篇级）',
    text:'本站已有许可归档正文，此链接打开论文入口。各步骤的页码与公式编号是定位文字，不是逐页直达链接。'
  }:{
    kind:'source-status',label:'来源状态 / 本机原文（篇级）',
    text:'本站未公开托管本篇全文。此链接按本机已有原件打开，或显示来源状态与合法导入入口；不表示已公开全文。页码与公式编号仅作定位说明。'
  };
  if(standalone)result.text+=' 当前单HTML不包含原件，请使用完整网站/离线包，或本机合法导入的原件。';
  return result;
}
function openParents(target,root){
  if(!target||!root||!root.contains(target))return false;
  for(let node=target;node&&node!==root;node=node.parentElement)if(node.tagName==='DETAILS')node.open=true;
  return true;
}
function install(win){
  const doc=win.document,view=doc.getElementById('view');
  if(!view||win.__paperMethodTransferUIInstalled)return;
  win.__paperMethodTransferUIInstalled=true;
  const mounted=new WeakSet();let backNavigation=false;
  function enhance(){
    for(const root of view.querySelectorAll('[data-method-transfer]')){
      const paper=root.dataset.methodTransfer;
      if(mounted.has(root)||root.id!=='method-transfer-'+paper||!Object.hasOwn(win.PAPER_DATA?.methodTransfers||{},paper))continue;
      mounted.add(root);
      const preservePosition=backNavigation||Number(win.history.state?.y)>0;
      // This scope owns explicit paragraph IDs and never joins .prose numbering.
      root.removeAttribute('data-no-terms');
      for(const heading of root.querySelectorAll('summary,h2,h3'))heading.setAttribute('data-no-terms','');
      win.PaperStudy?.terms(root);
      const record=(win.PAPER_SOURCES?.records||[]).find(row=>row.id===paper),access=sourceAccess(record,doc.body.classList.contains('single'));
      const originalHref='#/original/'+paper;
      for(const link of root.querySelectorAll('a[href]'))if(link.getAttribute('href')===originalHref)link.textContent=access.label;
      const notice=doc.createElement('p');notice.className='source-note method-transfer-access';notice.dataset.methodSourceStatus=access.kind;notice.dataset.noTerms='true';notice.textContent=access.text;
      const source=root.querySelector('.source-note');if(source)source.after(notice);else root.append(notice);
      root.dataset.methodTransferReady='v1';
      const targetID=parseTarget(win.location.hash,paper),target=targetID?doc.getElementById(targetID):null;
      if(!openParents(target,root)||preservePosition)continue;
      const requestedHash=win.location.hash;
      // Run after the existing route renderer's two frames. A newer route wins.
      win.requestAnimationFrame(()=>win.requestAnimationFrame(()=>{
        if(!root.isConnected||win.location.hash!==requestedHash)return;
        target.scrollIntoView({block:'start',behavior:'instant'});
        target.setAttribute('tabindex','-1');target.focus({preventScroll:true});
      }));
    }
  }
  win.addEventListener('popstate',()=>{backNavigation=true;win.setTimeout(()=>{backNavigation=false;},0);});
  const observer=new win.MutationObserver(records=>{
    if(records.some(record=>[...record.addedNodes].some(node=>node.nodeType===1&&(node.matches?.('[data-method-transfer]')||node.querySelector?.('[data-method-transfer]')))))enhance();
  });
  observer.observe(view,{childList:true,subtree:true});enhance();
}
const api=Object.freeze({parseTarget,sourceAccess,openParents,install});
if(typeof module==='object'&&module.exports){module.exports=api;return;}
window.PaperMethodTransferUI=api;install(window);
})();
