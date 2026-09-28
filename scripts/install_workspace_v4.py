"""One-time, idempotent integration; abort if a reviewed hook changed unexpectedly."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def patch(name,old,new):
 p=ROOT/name;s=p.read_text()
 if new in s:return
 if old not in s:raise ValueError('Integration hook changed: '+name+' / '+old[:100])
 p.write_text(s.replace(old,new,1))
def append(name,text):
 p=ROOT/name;s=p.read_text()
 if text not in s:p.write_text(s+'\n'+text+'\n')
def main():
 patch('src/index.html','<link rel="stylesheet" href="study.css">','<link rel="stylesheet" href="study.css"><link rel="stylesheet" href="workspace.css">')
 patch('src/index.html','<script src="app.js"></script>','<script src="workspace.js"></script><script src="app.js"></script>')
 patch('src/index.html','<a href="#/home">学习总览</a>','<a href="#/home">学习总览</a><a href="#/discover">检索与导入论文</a><a href="#/my-library">我的文献库</a><a href="#/glossary">术语词典</a>')
 patch('scripts/build_reader.py',"'study.css','translation-worker.js']","'study.css','translation-worker.js','workspace.js','workspace.css']")
 patch('scripts/build_reader.py',"'src/translation-worker.js']","'src/translation-worker.js','src/workspace.js','src/workspace.css']")
 patch('scripts/build_reader.py',"for css in ['reader.css','study.css']:","for css in ['reader.css','study.css','workspace.css']:")
 patch('scripts/build_reader.py',"'study.js','reader.js']:single=","'study.js','reader.js','workspace.js']:single=")
 patch('scripts/build_reader.py',"release.update(version=version,externalPDFsCached=True,reader='reflow-study-v3',","release.update(version=version,workspace='local-research-v4',glossaryExamples=sum(bool(t.get('example')) for t in study['terms']),externalPDFsCached=True,reader='reflow-study-v3',")
 patch('scripts/build_tutorials.py',"aliases={'home','library','methods','notes','offline','search','lab'}","aliases={'home','library','methods','notes','offline','search','lab','discover','my-library','workbook','glossary'}")
 patch('src/app.js',"const [id,section]=route.split('/');if(['original'", "const [id,section]=route.split('/');window.PaperWorkspace?.leave();if(['discover','my-library','workbook','glossary'].includes(id)){window.PaperReader?.leave();window.PaperStudy?.leave();$('#sidebar').classList.remove('open');$('#menu').setAttribute('aria-expanded','false');document.title='个人论文工作区 · Paper Lab';$('#breadcrumb').textContent='检索 · 导入 · 阅读';window.PaperWorkspace.route(id,route.split('/'));scrollTo(0,0);return;}if(['original'")
 patch('src/app.js','<a class="btn secondary" href="#/offline">保存到手机</a>','<a class="btn secondary" href="#/offline">保存到手机</a><a class="btn secondary" href="#/discover">检索／导入自己的论文</a>')
 patch('src/reader.js',"window.PaperReader={layoutChanged:","window.PaperReader={navigate:hash=>api.go(hash),notify:tell,importFile,layoutChanged:")
 patch('src/reader.js',"window.PaperStudy?.mountLesson(api.route().split('/')[0]);paint().catch", "window.PaperStudy?.mountLesson(api.route().split('/')[0]);window.PaperWorkspace?.enhanceLesson(api.route().split('/')[0]);paint().catch")
 patch('src/reader.js',"await window.PaperStudy?.mountOriginal(b);await paint();", "await window.PaperStudy?.mountOriginal(b);await window.PaperWorkspace?.enhanceOriginal(b);await paint();")
 patch('src/reader.js',"if(!b){const r=rec(id);$('#view').innerHTML=", "if(!b){const r=rec(id);if(window.PaperWorkspace&&r){$('#view').innerHTML=head(r.title,'本站原件状态与网络获取途径分别列出。')+'<div id=\"source-access-v4\"></div>';await window.PaperWorkspace.sourcePanel(r,$('#source-access-v4'));return;}$('#view').innerHTML=")
 patch('src/reader.js',"const local=await get('books',id);if(local)return local;const r=rec(id);", "const local=await get('books',id);if(local)return local;const attached=(await all('books')).filter(b=>b.lessonId===id);if(attached.length===1)return attached[0];const r=rec(id);")
 patch('src/reader.js','<div class="actions"><button class="primary" id="import-original">','<div class="actions"><a href="#/discover">通过DOI／题名检索与导入</a><a href="#/my-library">我的文献库</a><button class="primary" id="import-original">')
 # Rebuild alias matcher without changing any original characters or annotation offsets.
 p=ROOT/'src/study.js';s=p.read_text()
 start=s.index('const aliases=[];') if 'const aliases=[];' in s else s.index('let termRE=');end=s.index('function decorate(root)',start)
 replacement=r'''let termRE=null;const aliases=[],byAlias=new Map();
const escRE=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const canonical=s=>s.normalize('NFKC').toLowerCase().replace(/[\s\u00ad\-‐‑‒–—]/g,'');
function rebuildTerms(){aliases.length=0;byAlias.clear();for(const t of termsById.values())for(const a of t.aliases||[]){if(typeof a!=='string'||!a.trim()||a.length>180)continue;aliases.push([a,t.id]);if(!byAlias.has(canonical(a)))byAlias.set(canonical(a),t.id);}aliases.sort((a,b)=>b[0].length-a[0].length);const seen=new Set(),patterns=[];for(const [a] of aliases){const key=canonical(a);if(seen.has(key))continue;seen.add(key);const pattern=a.split(/([\s\-‐‑‒–—]+)/).filter(Boolean).map(part=>/^[\s\-‐‑‒–—]+$/.test(part)?'[\\s\\u00ad\\-‐‑‒–—]*':[...part].map(escRE).join('(?:\\u00ad\\s*)?')).join('');patterns.push(pattern);}termRE=patterns.length?new RegExp(patterns.join('|'),'giu'):null;}
function addTerms(rows){if(!Array.isArray(rows)||rows.length>1000)return;for(const t of rows){if(!t||!/^custom-[\w-]+$/.test(t.id)||typeof t.definition!=='string'||t.definition.length>10000||!Array.isArray(t.aliases)||t.aliases.length>20||typeof t.en!=='string'||typeof t.zh!=='string')continue;termsById.set(t.id,{...t,custom:true,sources:[]});}rebuildTerms();decorate(document.querySelector('#original-text')||document.querySelector('#view .reader'));}
function matchTerms(text){if(!termRE)return [];termRE.lastIndex=0;const found=[];let m;while((m=termRE.exec(text))){const a=m[0],i=m.index;if(/[A-Za-z]/.test(a[0])&&i>0&&/[A-Za-z0-9_]/.test(text[i-1]))continue;if(/[A-Za-z]/.test(a.at(-1))&&/[A-Za-z0-9_]/.test(text[i+a.length]||''))continue;const id=byAlias.get(canonical(a));if(id)found.push({start:i,end:i+a.length,id,text:a});}return found;}
rebuildTerms();
'''
 if 'function rebuildTerms()' not in s:s=s[:start]+replacement+s[end:];p.write_text(s)
 patch('src/study.js',"byAlias.get(a.textContent.trim().toLowerCase())","byAlias.get(canonical(a.textContent.trim()))")
 patch('src/study.js','<p>${E(t.definition)}</p>${t.boundary?', '<p>${E(t.definition)}</p>${t.explanation&&t.explanation!==t.definition?`<h4>一步一步理解</h4><p>${E(t.explanation)}</p>`:\'\'}${t.example?`<div class="term-example"><h4>${t.custom?\'我的例子（未核验）\':\'教学示例（自编，非论文数据）\'}</h4><p>${E(t.example)}</p></div>`:\'\'}${t.boundary?')
 patch('src/study.js',"addEventListener('wheel',hideTerm,{passive:true});addEventListener('touchmove',hideTerm,{passive:true});", "addEventListener('wheel',e=>{if(!e.target.closest('.term-popover'))hideTerm();},{passive:true});addEventListener('touchmove',e=>{if(!e.target.closest('.term-popover'))hideTerm();},{passive:true});")
 # Restore validates source identities and never silently replaces existing personal text.
 backup=r'''async function restoreTranslationBackup(entries){if(!Array.isArray(entries)||entries.length>50000)throw Error('译文备份格式错误');const books=new Map();for(const e of entries){if(!e||typeof e.docId!=='string'||typeof e.block!=='string'||typeof e.original!=='string'||typeof e.text!=='string'||e.text.length>120000||! /^[a-f0-9]{64}$/.test(e.sourceHash))throw Error('译文条目无效');if(!books.has(e.docId))books.set(e.docId,await window.PaperReader.loadBook(e.docId).catch(()=>null));const b=books.get(e.docId),block=b?.pages.flatMap(p=>p.blocks).find(x=>x.id===e.block);if(!b||b.sourceHash!==e.sourceHash||!block||block.text!==e.original)continue;const id=key(b,block);if(!await io('get',id))await io('put',{...e,id});}}
'''
 patch('src/study.js','window.PaperStudy={mountLesson',backup+'window.PaperStudy={addTerms,restoreTranslationBackup,mountLesson')
 # Personal edits made while an inference was running must win over machine output.
 patch('src/study.js',"await io('put',entry);if(slot.isConnected&&ticket===run){const a=anchor();fillSlot(slot,entry);", "const existing=await io('get',entry.id);const winner=existing?.original===entry.original?existing:entry;if(winner===entry)await io('put',entry);if(slot.isConnected&&ticket===run){const a=anchor();fillSlot(slot,winner);")
 # Avoid eager decoding all original-page images and disable inappropriate reflow paging.
 patch('src/workspace.js',"if(files.length>10){notice('每批最多10份文件，请分批导入。');return;}","if(ref&&files.length>1){notice('附加到指定文献时请一次选择一份原件；独立批量导入请使用文件入口。');return;}if(files.length>10){notice('每批最多10份文件，请分批导入。');return;}")
 patch('src/workspace.js',"root.classList.toggle('source-image-mode',on);", "if(on&&$('#original-viewport')?.classList.contains('paged'))$('#reader-mode').click();const anchorPage=$$('.source-page',root).find(p=>p.getBoundingClientRect().bottom>140)?.id;root.classList.toggle('source-image-mode',on);$('#reader-mode').disabled=on;")
 patch('src/workspace.js',"d.querySelector('img')?.setAttribute('loading','eager');", "d.querySelector('img')?.setAttribute('loading','lazy');")
 patch('src/workspace.js',"else d.open=d.dataset.priorOpen==='1';});window.PaperReader.layoutChanged();", "else d.open=d.dataset.priorOpen==='1';});window.PaperReader.layoutChanged();if(anchorPage)requestAnimationFrame(()=>document.getElementById(anchorPage)?.scrollIntoView({block:'start'}));")
 # Safely reject a known DOI mismatch rather than attach the wrong full text to a citation.
 patch('src/workspace.js',"if(!book.sourceDOI)book.sourceDOI=doi(first);", "const detected=doi(first);book.detectedDOI=detected;if(ref?.doi&&detected&&detected!==ref.doi)throw Error('原文件首部DOI与所选文献不同，请核对后作为独立文件导入。');if(!book.sourceDOI)book.sourceDOI=detected;")
 append('src/workspace.css','body.dark{--surface:var(--panel,#1c2b26);--ink:var(--text,#e4eee7);--line:var(--border,#385447);--soft:#223e31;}')
 p=ROOT/'content/navigation.json';docs=json.loads(p.read_text())
 if not any(d['id']=='reader-guide' for d in docs):docs.append({'id':'reader-guide','type':'guide','title':'把论文放进可复用的阅读流程','stage':'系统使用','minutes':12,'summary':'检索、身份核对、个人全文、原图保真、术语与框架、证据笔记及备份。','sections':[
 ['检索与身份核对','使用说明','在[[discover|检索与导入]]输入DOI、DOI链接、题名或关键词。DOI用于精确定位；题名返回候选，需核对作者、年份、期刊。Crossref与DataCite主要返回元数据，OpenAlex可提供开放全文位置线索。将元数据加入[[my-library|我的文献库]]，不等于已经取得全文。检索只在你点击后联网，不上传私人原文或笔记。','官方接口说明：https://www.crossref.org/documentation/retrieve-metadata/rest-api/；https://help.openalex.org/api/'],
 ['全文获取不是只有一种状态','使用说明','先检查出版商、作者仓储和已知原件入口。网址可在浏览器打开但不能直接导入，可能是跨域限制；返回登录页并不等于返回PDF。机构阅读权限与公开再分发分别判断。学校账号只在官方认证页输入，本站不收集。合法取得PDF后可拖入个人阅读库，本站不会把私人文件自动公开。','https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS；机构入口：https://lib.cau.edu.cn/'],
 ['复杂公式与表格优先看原图','使用说明','导入PDF后保留全部原页图像。原文工具栏可切换“原页图文”，公式、表格和图注均随原页保留，点击图片可以放大。重排层便于选择、检索和批注，但机器段落与双栏顺序可能需要核对。扫描PDF没有文字层时，不假装已可全文文字检索；无需为了可选择文字而猜写公式。','本系统实现边界：PDF.js机器解析，未自动OCR；原件图像作为复杂排版核对依据。'],
 ['先框架再方法，边读边留证据','使用说明','对已有带读的论文，先读整篇研究问题、论证链，再看各阶段接收什么、输出什么。任意导入论文均可打开六步[[workbook|阅读工作表]]，整理问题、证据、方法、结果、限制与迁移。自动识别的章节导航只是导航，不是自动精读结论；没有全文时只提供问题模板。可导出私人AI精读材料包，自行决定是否交给外部工具。','已有框架以对应论文核读范围为准；用户工作表与自编例子不冒充作者结论。'],
 ['术语与可持续积累','使用说明','点击正文已标记词语就地阅读定义、分步理解和例子，点击外部关闭。[[glossary|术语词典]]可搜索中英文名称。词典尚未穷尽全部学科；遗漏词可添加自己的本机释义，并标注为未核验。数学区域、程序代码及原页图片中的词语不强行覆盖点击层，以保护公式和选字。','教学示例均自编；论文特定定义优先于通用解释。'],
 ['备份、迁移与离线','使用说明','元数据备份适合轻量同步；完整个人备份包含本机原件、页面图片、划线、译文与工作表，请勿公开上传。当前完整备份限制约300MB本机原件与图片，浏览器配额由设备决定。恢复保留现有内容，同ID不同原件停止以保护批注。完整网站缓存包含公开资料与本机翻译引擎，不会替代个人数据备份；更新时不要清除网站数据。','本机数据不是跨设备自动云同步；浏览器存储仍可能被用户或系统清理。']],'quiz':[['为什么加入DOI后还可能不能立即阅读全文？','DOI先定位元数据；全文需有可用来源，且浏览器直读受网络、跨域和访问权限影响。'],['自动生成章节目录是否代表已完成论文带读？','不是。目录只反映结构，结论必须逐条回到原文证据。']],'related':['research-framework','offline-help']})
 p.write_text(json.dumps(docs,ensure_ascii=False,indent=2)+'\n')
 p=ROOT/'content/session-log.json';log=json.loads(p.read_text())
 if not any(d['id']=='reader-workspace-20260928' for d in log):log.append({'id':'reader-workspace-20260928','type':'guide','title':'2026-09-28 · 从固定文库到个人论文工作区','stage':'更新记录','summary':'加入DOI与题名检索、本机文献管理、原页图文、术语例子及六步阅读工作表。','sections':[['本次新增','更新记录','保留原文与旧批注数据结构；新增明确触发的公共元数据查询，PDF本机导入与去重、文献列表、证据工作表、RIS/BibTeX与备份。复杂版面允许以完整原图阅读。术语补充步骤解释和自编示例。','不会把元数据、摘要或自动目录标为全文精读。']],'related':['reader-guide']})
 p.write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
 # Existing declared sources remain; access != public redistribution.
 p=ROOT/'resources/catalog.json';cat=json.loads(p.read_text());paper={d['id']:d for d in json.loads((ROOT/'content/papers.json').read_text())}
 for r in cat['records']:
  if not r.get('bookPath'):
   candidate=r.get('downloadURL') or r.get('candidateURL') or paper.get(r['id'],{}).get('pdf')
   if candidate:r['candidateURL']=candidate
  if r['id']=='farmsteps-2026':
   r['downloadURL']='https://edepot.wur.nl/713946';r['accessStatus']='repository-available';r['accessNote']='WUR官方记录列出可访问原件（Taverne）。出版商页面另有机构订阅入口；本站尚未公开镜像不代表全文不存在。请打开仓储原件或导入本机。';r['accessEvidence']='https://research.wur.nl/en/publications/farmsteps-a-model-for-spatial-temporal-exploration-of-diversified/'
 p.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n')
 print('Workspace integrated; source strings and existing annotation keys retained.')
if __name__=='__main__':main()
