#!/usr/bin/env python3
"""Idempotent upgrade of original tutorial shell; generated source changes remain reviewable."""
from pathlib import Path
import json,re
R=Path(__file__).resolve().parents[1]
p=R/'scripts/build.py'
if not (R/'scripts/build_tutorials.py').exists():p.rename(R/'scripts/build_tutorials.py')
p.write_text("from build_reader import main\nif __name__ == '__main__': main()\n")
p=R/'src/index.html';s=p.read_text()
if 'reader.css' not in s:s=s.replace('<link rel="stylesheet" href="style.css">','<link rel="stylesheet" href="style.css"><link rel="stylesheet" href="reader.css">')
if 'resources.js' not in s:s=s.replace('<script src="app.js"></script>','<script src="resources.js"></script><script src="reader.js"></script><script src="app.js"></script>')
if 'href="#/resources"' not in s:s=s.replace('<a href="#/methods">方法工具箱</a>','<a href="#/methods">方法工具箱</a><a href="#/resources">原文书架 · 离线资料</a><a href="#/annotations">划线批注 · 便签</a>')
p.write_text(s)
p=R/'src/app.js';s=p.read_text()
if 'PaperReader.init' not in s:
 s=s.replace('function savePosition(){','function savePosition(){window.PaperReader?.beforeNavigate();')
 s=s.replace('function render(restore=false){','function render(restore=false){window.PaperReader?.beforeNavigate();')
 s=s.replace("const [id,section]=route.split('/');","const [id,section]=route.split('/');if(['original','annotations','resources'].includes(id)){$('#sidebar').classList.remove('open');$('#menu').setAttribute('aria-expanded','false');window.PaperReader.route(id,route.split('/'));return;}window.PaperReader?.leave();")
 s=s.replace("$('#view').innerHTML=out;bind();","$('#view').innerHTML=out;bind();window.PaperReader?.attachLesson();")
 s=s.replace("render(true);\nif('serviceWorker'", "window.PaperReader.init({go,toast,byId,route:()=>route});render(true);\nif('serviceWorker'")
 old="${[['url','论文与来源'],['pdf','原文PDF入口'],['dataUrl','作者数据入口']].filter(([k])=>d[k]).map(([k,t])=>`<a href=\"${esc(safeUrl(d[k]))}\" target=\"_blank\" rel=\"noopener noreferrer\">${t} ↗</a>`).join('')}"
 new="${d.url?`<a href=\"#/original/${d.id}\">站内原文 · 可划线批注</a>`:''}${d.dataUrl?`<a href=\"#/original/quzhou-dataset\">数据与附件资源</a>`:''}"
 assert old in s,'Original link block changed';s=s.replace(old,new)
 s=s.replace('<a href="${esc(safeUrl(d.url))}" target="_blank" rel="noopener noreferrer">原文 ↗</a>','<a href="#/original/${d.id}">原文 · 站内阅读</a>')
 s=s.replace("function rich(s)","function localRef(u){const r=window.PAPER_SOURCES?.records.find(r=>(r.aliases||[]).includes(u)||r.sourceURL===u||r.downloadURL===u);return r?'#/original/'+r.id:null;}\nfunction rich(s)")
 s=s.replace('u=>`<a href="${esc(safeUrl(u))}" target="_blank" rel="noopener noreferrer">${u}</a>`','u=>`<a href="${esc(localRef(u)||safeUrl(u))}" ${localRef(u)?\'\':\'target="_blank" rel="noopener noreferrer"\'}>${u}</a>`')
 s=s.replace('外部期刊、论文PDF与作者代码不在本站缓存内。','包括已归档的完整原文、图表、原始文件和阅读器。尚未取得或不允许转载的资料需本机导入。')
 s=s.replace('正文、搜索、方法和交互教学一起保存；','正文、搜索、方法、完整原文与全部原图一起保存；')
 s=s.replace('单文件HTML无需服务器和第三方资源。','单文件HTML包含带读和教学；原文、原图及PDF在完整ZIP与完整缓存中，不包含在这个轻量单文件内。')
 s=s.replace('外部论文不在其中。','已归档原文、图表和原件已包含；未取得的外链不在其中。')
 s=s.replace('await navigator.serviceWorker.ready;await cacheStatus();',"await navigator.serviceWorker.ready;await cacheAll();")
 s=s.replace('async function cacheStatus(){',"async function cacheAll(){const r=await navigator.serviceWorker.ready;const w=r.active;if(!w)throw Error('离线服务未激活');return new Promise((resolve,reject)=>{const ch=new MessageChannel(),t=setTimeout(()=>reject(Error('缓存超时，已下载内容保留')),900000);ch.port1.onmessage=e=>{const x=e.data;if(x.type==='PROGRESS')$('#cache-status').textContent=`正在缓存原文与图表 ${x.done}/${x.total}，请保持网络。`;if(x.type==='DONE'){clearTimeout(t);$('#cache-status').textContent=x.complete?`已完整缓存 ${x.count} 个资源，可测试断网刷新。`:`部分资源未完成（${x.count}/${x.expected}），请联网重试；已缓存内容保留。`;resolve(x);}};w.postMessage({type:'CACHE_ALL'},[ch.port2]);});}\nasync function cacheStatus(){")
 s=s.replace("Error('缓存状态检查超时')),12000)","Error('缓存状态检查超时')),30000)")
 p.write_text(s)
p=R/'scripts/test_browser.py';s=p.read_text();s=s.replace("page.locator('#check-cache').click();page.wait_for_function(\"document.querySelector('#cache-status').textContent.includes('已完整缓存')\")","page.locator('#cache-site').click();page.wait_for_function(\"document.querySelector('#cache-status').textContent.includes('已完整缓存')\",timeout=300000)");p.write_text(s)
# Update documentation instead of retaining the old false boundary statement.
p=R/'content/session-log.json';d=json.loads(p.read_text());ident='reader-offline-update'
if not any(x['id']==ident for x in d):d.append({'id':ident,'type':'guide','title':'原文阅读与离线资料升级','stage':'更新记录','minutes':5,'summary':'站内原文、连续/翻页阅读、划线批注、关联便签、本机原件导入和完整原文缓存。','sections':[['公开与本机边界','使用说明','许可明确的原文按原始内容归档；无公开许可的原件只允许本机导入，不以摘要替代。'],['完整性说明','证据边界','正文保留可提取文字、图形切片、逐页原排版核对图及不变的原始文件。复杂公式表格仍需核对图；站外补充材料未自动包括。'],['版本更正','核验记录','FarmSTEPS出版页当前是订阅访问，不能沿用此前“开放全文”的称呼。可导入合法取得的原件阅读。'],['便签数据','使用说明','批注只在本机，不上传公开仓库。支持标签、相互链接、原文位置返回和JSON/Markdown导出；WPS等外部阅读器不自动同步这些网页批注。']]});p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print('Reader integrated; old tutorial notes and learning progress retained.')
