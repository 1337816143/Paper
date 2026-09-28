"""Final hardening. Derived abbreviation expansions quote only the current local document."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def patch(name,old,new):
 p=ROOT/name;s=p.read_text()
 if new in s:return
 if old not in s:raise ValueError(name+' missing '+old[:90])
 p.write_text(s.replace(old,new,1))
def main():
 source_terms=r'''function clearSourceTerms(){for(const [id,t] of termsById)if(t.sourceBlock)termsById.delete(id);rebuildTerms();}
function addSourceTerms(rows){clearSourceTerms();for(const t of rows.slice(0,80)){if(!t||!/^sourceabbr-[a-f0-9]+-\d+$/.test(t.id)||typeof t.definition!=='string'||t.definition.length>1500||!Array.isArray(t.aliases)||t.aliases.some(a=>typeof a!=='string'||a.length>180))continue;termsById.set(t.id,t);}rebuildTerms();decorate(document.querySelector('#original-text'));}
'''
 patch('src/study.js','function hideTerm(){',source_terms+'function hideTerm(){')
 patch('src/study.js','window.PaperStudy={addTerms,','window.PaperStudy={addSourceTerms,addTerms,')
 patch('src/study.js','function leave(){run++;current=null;','function leave(){run++;current=null;clearSourceTerms();')
 patch('src/study.js','<small>术语 · 本站教学释义</small>','<small>${t.sourceBlock?\'原文定义的缩写\':t.custom?\'本机自定义（未核验）\':\'术语 · 本站教学释义\'}</small>')
 patch('src/study.js','<div class="term-sources">${(t.sources||[])','${t.sourceBlock?`<p class="term-boundary">以下为原文提供的展开，不等于已核验完整专业定义。</p><a href="#/original/${E(t.docId)}/${E(t.sourceBlock)}">核对原文定义位置 ↗</a>`:\'\'}<div class="term-sources">${(t.sources||[])')
 derive=r'''function definedAbbreviations(book){const rows=[],seen=new Set();for(const p of book.pages)for(const b of p.blocks){if(!b.text||b.text.length>60000)continue;const text=norm(b.text);for(const m of text.matchAll(/\(([A-Z][A-Z0-9-]{1,9})\)/g)){const abbr=m[1];if(seen.has(abbr))continue;const before=text.slice(Math.max(0,m.index-180),m.index).replace(/[;:.!?].*$/,'$&'),words=before.match(/[A-Za-z]+(?:-[A-Za-z]+)*/g)||[];let expansion='';for(let count=2;count<=Math.min(10,words.length);count++){const slice=words.slice(-count),initials=slice.filter(w=>!['of','the','and','for','in','to','a','an'].includes(w.toLowerCase())).flatMap(w=>w.split('-')).map(w=>w[0]).join('').toUpperCase();if(initials===abbr.replace(/-/g,'')){expansion=slice.join(' ');break;}}if(!expansion)continue;seen.add(abbr);rows.push({id:'sourceabbr-'+book.sourceHash.slice(0,12)+'-'+rows.length,en:abbr,zh:abbr+' · 原文缩写',aliases:[abbr,expansion],definition:'作者在本段将 '+expansion+' 写作 '+abbr+'。请结合下方原文位置理解其在本研究中的具体含义。',explanation:'从当前原文的“全称（缩写）”形式提取。仅在字母对应关系明确时标记；不根据常见缩写猜测含义。',sourceBlock:b.id,docId:book.id,sources:[]});if(rows.length>=80)return rows;}}return rows;}
'''
 patch('src/workspace.js','async function enhanceOriginal(b){',derive+'async function enhanceOriginal(b){')
 patch('src/workspace.js',"const root=$('#original-text');if(!root)return;const controls=", "const root=$('#original-text');if(!root)return;window.PaperStudy.addSourceTerms(definedAbbreviations(b));const controls=")
 patch('src/workspace.js',"$('#reader-mode').disabled=on;", "$('#reader-mode').disabled=on;const chinese=$('#toggle-chinese');if(chinese){chinese.disabled=on;chinese.title=on?'中文对照请返回重排文字':'';}")
 patch('src/workspace.js',"id:ref?.id||'local-'", "id:ref?.id||'local-'") if False else None
 # Conflict workbooks remain attached to the same paper; imported differing fields are retained.
 patch('src/workspace.js',"if(old&&JSON.stringify(old)!==JSON.stringify(r)){await put(name,{...r,id:r.id+'-copy-'+crypto.randomUUID().slice(0,8)});}", "if(old&&JSON.stringify(old)!==JSON.stringify(r)){if(name==='workbooks'){const values={...(old.values||{})};for(const [k,v] of Object.entries(r.values||{})){if(typeof v!=='string'||v.length>20000)throw Error('工作表字段无效');if(!values[k])values[k]=v;else if(v&&values[k]!==v&&!values[k].includes(v))values[k]+='\\n\\n【导入副本】\\n'+v;}await put(name,{...old,values,updatedAt:now()});}else if(name==='references'){await put(name,{...old,backupVariants:[...(old.backupVariants||[]),r].slice(-5)});}else await put(name,{...r,id:r.id+'-copy-'+crypto.randomUUID().slice(0,8)});}")
 patch('src/workspace.js',"async function route(id,parts){", "async function route(id,parts,restoreY=0){")
 patch('src/workspace.js',"if(id==='glossary')await glossary();}catch(e)", "if(id==='glossary')await glossary();if(t===state.epoch)requestAnimationFrame(()=>scrollTo(0,restoreY));}catch(e)")
 patch('src/app.js',"window.PaperWorkspace.route(id,route.split('/'));scrollTo(0,0);return;", "$$('.sidebar a').forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#/'+id));window.PaperWorkspace.route(id,route.split('/'),restore?(history.state?.y||0):0);scrollTo(0,0);return;")
 # A full restore refreshes the original application's in-memory learning-state cache.
 patch('src/workspace.js',"notice('恢复已完成；现有校订优先，冲突笔记保留副本。');go('#/my-library');", "sessionStorage.setItem('paper-restored-v4','完整个人备份已恢复；当前内容优先，冲突笔记已保留。');location.hash='#/my-library';location.reload();")
 patch('src/workspace.js',"async function myLibrary(){const ticket=", "async function myLibrary(){const restored=sessionStorage.getItem('paper-restored-v4');if(restored){notice(restored);sessionStorage.removeItem('paper-restored-v4');}const ticket=")
 # Register better primary-source paths, retaining individual access results rather than blanket denials.
 p=ROOT/'resources/catalog.json';cat=json.loads(p.read_text())
 for r in cat['records']:
  if r['id']=='ditzler-2019':
   r['candidateURL']='https://www.sciencedirect.com/science/article/pii/S0308521X18307340/pdfft';r['metadataURL']='https://research.wur.nl/en/publications/a-model-to-examine-farm-household-trade-offs-and-synergies-with-a/';r['accessNote']='WUR官方记录标注CC BY，出版商页面提供View PDF入口。此前没有归档不等于没有开放全文；可打开出版商下载，直链仍可能受跨域或平台访问限制。';r['accessStatus']='open-access-reported'
  if r['id']=='farmdesign-2012':r['candidateURL']='https://www.sciencedirect.com/science/article/pii/S0308521X12000558';r['accessNote']='出版商记录提供机构访问入口；WUR公开记录当前未列出独立仓储PDF。可通过机构订阅获取后导入，不把未取得原件写成全文不存在。'
  if r['id'] in ['liang-thesis','cheng-thesis']:
   r['accessNote']='WUR官方学位论文记录提供Download PDF入口。本轮服务器直读曾返回HTTP 400；这是一次技术请求失败，不等于你没有权限，也不代表无全文。可从官方记录进入下载后导入本机。'
  if r['id']=='xu-thesis':r['accessNote']='已知WUR原件入口有响应，但本轮访问审计在45MB检测上限处停止，未归类为权限问题。个人PDF导入支持单文件120MB和最多400页；超过限制请分卷。'
 p.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n')
 # Keep field help consistent with the actual backup and term behavior.
 p=ROOT/'content/navigation.json';docs=json.loads(p.read_text());guide=next(d for d in docs if d['id']=='reader-guide');guide['sections'][4][2]+=' 对新导入论文，还会在原文明确提供全称（缩写）且字母对应时，自动标出作者定义的缩写，并提供原文定位；不猜测未定义缩写的学术含义。'
 # Avoid repeating appended explanations on a repeated preparation run.
 guide['sections'][4][2]=guide['sections'][4][2].split(' 对新导入论文，还会')[0]+' 对新导入论文，还会在原文明确提供全称（缩写）且字母对应时，自动标出作者定义的缩写，并提供原文定位；不猜测未定义缩写的学术含义。'
 p.write_text(json.dumps(docs,ensure_ascii=False,indent=2)+'\n')
 # Evidence counts are produced from current data, not optimistic fixed strings.
 print('Final workspace hardening applied.')
if __name__=='__main__':main()
