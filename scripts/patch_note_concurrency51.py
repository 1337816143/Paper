from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'src/app.js';s=p.read_text()
old="function persist(){try{localStorage.setItem(KEY,JSON.stringify(store));window.PaperSync?.changed('learning');return true;}catch{blocked=true;return false;}}"
new=r"""let persistedBaseline=JSON.parse(JSON.stringify(store));
function persist(){try{
 const remote=JSON.parse(localStorage.getItem(KEY)||'{}');if(!remote||typeof remote!=='object'||Array.isArray(remote))throw Error('Invalid learning storage');
 const local=store,base=persistedBaseline,merged={...remote},same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);let noteConflict=false;
 for(const name of new Set([...Object.keys(base),...Object.keys(local),...Object.keys(remote)])){
  if(['notes','done','positions'].includes(name)){
   merged[name]={};const B=base[name]||{},L=local[name]||{},R=remote[name]||{};
   for(const id of new Set([...Object.keys(B),...Object.keys(L),...Object.keys(R)])){
    if(['__proto__','constructor','prototype'].includes(id))continue;let value;
    if(same(L[id],R[id]))value=L[id];else if(same(L[id],B[id]))value=R[id];else if(same(R[id],B[id]))value=L[id];
    else if(name==='notes'&&typeof L[id]==='string'&&typeof R[id]==='string'){
     value=L[id].includes(R[id])?L[id]:R[id].includes(L[id])?R[id]:L[id]+'\n\n【另一标签页的并发版本，请核对】\n'+R[id];noteConflict=true;
    }else if(name==='positions')value=(L[id]?.at||0)>(R[id]?.at||0)?L[id]:R[id];else value=L[id]===undefined?R[id]:L[id];
    if(value!==undefined)merged[name][id]=value;
   }
  }else if(!['__proto__','constructor','prototype'].includes(name)){
   const value=same(local[name],base[name])?remote[name]:local[name];if(value===undefined)delete merged[name];else merged[name]=value;
  }
 }
 localStorage.setItem(KEY,JSON.stringify(merged));store=merged;persistedBaseline=JSON.parse(JSON.stringify(merged));
 const field=$('#note'),id=route.split('/')[0];if(field&&typeof merged.notes[id]==='string'&&field.value===local.notes?.[id]&&field.value!==merged.notes[id]){const a=field.selectionStart,b=field.selectionEnd;field.value=merged.notes[id];field.setSelectionRange(a,b);}
 if(noteConflict)toast('同篇笔记有并发编辑，两个版本已并列保留，请核对。');window.PaperSync?.changed('learning');return true;
}catch{blocked=true;return false;}}
// During IME composition preserve DOM input until the final input event; updates remain blocked by focus.
document.addEventListener('compositionend',e=>{if(e.target.id==='note')e.target.dispatchEvent(new InputEvent('input',{bubbles:true,isComposing:false}));});"""
if 'let persistedBaseline=' not in s:
 assert s.count(old)==1;s=s.replace(old,new)
 anchor="if($('#note'))$('#note').oninput=e=>{store.notes[d.id]"
 assert anchor in s;s=s.replace(anchor,"if($('#note'))$('#note').oninput=e=>{if(e.isComposing)return;store.notes[d.id]")
 p.write_text(s)
# Update known public acquisition metadata only; no private bytes or credentials copied.
p=ROOT/'resources/catalog.json';c=json.loads(p.read_text())
for r in c['records']:
 if r['id'] in ['farmsteps-2026','landscape-2018','xu-thesis']:
  r['privateCopyAvailable']=True;r['accessStatus']='private-copy-verified';r['accessCheckedAt']='2026-09-29';r['accessNote']='已核对项目所有者的私有阅读库原件。通过私有同步恢复到当前设备后可阅读全文；未取得公开转载许可，因此不放进公开镜像。'
 if r['id']=='xu-thesis':r['verifiedPDFPages']=322
 if r['id']=='liang-thesis':r['accessStatus']='official-embargo';r['accessNote']='WUR官方Download PDF入口本轮显示暂不开放至2026-12-31。这不是已发表相关文章无全文的证明；章节论文需分别检索。'
 if r['id']=='cheng-thesis':r['accessStatus']='official-embargo';r['accessNote']='WUR官方仓储本轮返回暂不开放日期2027-01-09。已发表的2023、2025论文仍可独立阅读全文。'
p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'src/workspace.js';s=p.read_text()
old="$('#source-research',node).onclick=()=>"
new="if(record.privateCopyAvailable){const help=document.createElement('p');help.className='notice';help.innerHTML='项目所有者的私有库已有完整原件。<a href=\"#/sync\">连接私有阅读库并恢复</a> 后在本设备打开；这不表示匿名访问者可读取私人资料。';node.querySelector('.card')?.prepend(help);}$('#source-research',node).onclick=()=>"
if new not in s:
 assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
# Retain failed-test diagnostics without weakening assertions or including user data.
p=ROOT/'scripts/test_release51.py';s=p.read_text()
s=s.replace("assert condition,name\n checks.append(name)","if not condition:\n  (OUT/'release51-failure.json').write_text(json.dumps({'failed':name,'completed':checks,'testData':'synthetic-only'},indent=2))\n assert condition,name\n checks.append(name)")
p.write_text(s)
print('Cross-tab merge and verified acquisition states updated. Private file contents unchanged.')
