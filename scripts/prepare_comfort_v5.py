#!/usr/bin/env python3
"""Narrow, idempotent v5 integration; preserves previous scientific content and tests."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def patch(path,old,new,count=1):
 p=ROOT/path;s=p.read_text()
 if new in s:return
 if old not in s:raise RuntimeError('Expected integration hook changed: '+path+' / '+old[:80])
 p.write_text(s.replace(old,new,count))
def write(path,data):
 (ROOT/path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
# Static shell and complete offline packaging.
patch('src/index.html','<link rel="stylesheet" href="workspace.css">','<link rel="stylesheet" href="workspace.css"><link rel="stylesheet" href="comfort.css">')
patch('src/index.html','<button id="theme"','<button id="sync-status" class="sync-status" type="button" data-state="local-only" aria-label="GitHub 同步：尚未连接">仅本地</button><button id="theme"')
patch('src/index.html','<a href="#/my-library">我的文献库</a>','<a href="#/my-library">我的文献库</a><a href="#/sync">GitHub 私有同步</a>')
patch('src/index.html','笔记仅存本设备。','本地优先保存；跨设备恢复请连接 GitHub 私有同步。')
patch('src/index.html','<script src="workspace.js"></script>','<script src="workspace.js"></script><script src="sync.js"></script><script src="comfort.js"></script>')
patch('scripts/build_reader.py',"'workspace.js','workspace.css']:shutil.copyfile", "'workspace.js','workspace.css','sync.js','comfort.js','comfort.css']:shutil.copyfile")
patch('scripts/build_reader.py',"'src/workspace.js','src/workspace.css']:","'src/workspace.js','src/workspace.css','src/sync.js','src/comfort.js','src/comfort.css']:")
patch('scripts/build_reader.py',"['reader.css','study.css','workspace.css']:","['reader.css','study.css','workspace.css','comfort.css']:")
patch('scripts/build_reader.py',"'study.js','reader.js','workspace.js']:single", "'study.js','reader.js','workspace.js','sync.js','comfort.js']:single")
patch('scripts/build_reader.py',"workspace='local-research-v4',", "workspace='private-sync-v5',comfort='liquid-glass-contextual-v5',sync={'backend':'private GitHub Contents API','requiresUserAuthorization':True,'authorizationStorage':'page memory only','configurationRequired':True,'privateDataBranch':'paper-user-data','privateDataPrefix':'private/paper-sync/v5/'},")
# Route and in-memory legacy notebook must reload after applying a remote checkpoint.
patch('src/app.js',"function render(restore=false){window.PaperReader?.beforeNavigate();", "function render(restore=false){window.PaperComfort?.close();window.PaperReader?.beforeNavigate();")
patch('src/app.js',"window.PaperWorkspace?.leave();if(['discover'", "window.PaperWorkspace?.leave();if(id==='sync'){window.PaperReader?.leave();window.PaperStudy?.leave();$('#sidebar').classList.remove('open');$('#menu').setAttribute('aria-expanded','false');$('#breadcrumb').textContent='GitHub 私有同步';document.title='私有同步 · Paper Lab';window.PaperSync.render().catch(e=>toast(e.message));scrollTo(0,0);return;}if(['discover'")
patch('src/app.js',"localStorage.setItem(KEY,JSON.stringify(store));return true;", "localStorage.setItem(KEY,JSON.stringify(store));window.PaperSync?.changed('learning');return true;")
patch('src/app.js',"window.addEventListener('popstate',()=>render(true));", "window.addEventListener('paper-sync-applied',()=>{try{const fresh=JSON.parse(localStorage.getItem(KEY)||'{}');for(const name of ['notes','done','positions'])if(!fresh[name]||typeof fresh[name]!=='object')fresh[name]={};store=fresh;}catch{toast('云端检查点已保存，但当前学习笔记未能重新载入；请保留备份。');}});\nwindow.addEventListener('popstate',()=>render(true));")
# Only successful local writes schedule synchronization, never read operations.
patch('src/reader.js',"t.oncomplete=()=>ok(r);", "t.oncomplete=()=>{if(!['get','getAll'].includes(m))window.PaperSync?.changed(s);ok(r);};")
patch('src/workspace.js',"tx.oncomplete=()=>ok(v);", "tx.oncomplete=()=>{if(!['get','getAll'].includes(method))window.PaperSync?.changed(name);ok(v);};")
patch('src/workspace.js',"tx.oncomplete=ok;tx.onabort=tx.onerror", "tx.oncomplete=()=>{window.PaperSync?.changed('files');ok();};tx.onabort=tx.onerror")
patch('src/study.js',"t.oncomplete=()=>ok(result);", "t.oncomplete=()=>{if(!['get','getAll'].includes(method))window.PaperSync?.changed('translations');ok(result);};")
# Preserve the original editor as a fallback for old single-file integrations.
patch('src/reader.js',"async function edit(existing,seed={}){const allNotes=await all('annotations')", "async function edit(existing,seed={}){if(window.PaperComfort)return window.PaperComfort.editNote(existing,seed,{all,put,del,paint,notes,route:api.route,tell});const allNotes=await all('annotations')")
# On navigation a compact draft is flushed; no modal overlay or lost editing state.
patch('src/reader.js',"function reset(){selection=null;", "function reset(){window.PaperComfort?.close();selection=null;")
# Personal backups include the newly introduced records but never authentication.
patch('src/workspace.js',"learning:localStorage.getItem('paper-lab-learning-v1'),at:now()", "learning:localStorage.getItem('paper-lab-learning-v1'),comfort:await window.PaperComfort?.exportMetadata(),at:now()")
patch('src/workspace.js',"sessionStorage.setItem('paper-restored-v4','完整个人备份已恢复", "await window.PaperComfort?.restoreMetadata(x.comfort);window.PaperSync?.changed('files');sessionStorage.setItem('paper-restored-v4','完整个人备份已恢复")
# Clarify local-first vs confirmed-cloud saving; remove contradictory permanent-local claims.
p=ROOT/'src/workspace.js';s=p.read_text()
for a,b in {
 '文档和笔记仅保存在本机':'文档和笔记本地优先保存，GitHub 状态见同步中心',
 '本机保存，不上传。':'本地优先保存；连接 GitHub 后同步到私有数据分支。',
 '只在本机</p>':'本地原件 · 可同步至私有 GitHub</p>',
 '自定义释义只保存在本机。':'自定义释义本地保存，可通过私有 GitHub 同步。',
 '导入${files.length}个文件，仅保存在本机。PDF将保留全部原页图片，批注不上传。继续？':'导入${files.length}个文件到个人阅读库。PDF保留原页图片；连接 GitHub 时将同步至私有数据分支，绝不公开发布。继续？',
 '文件不会上传。':'文件先保存本机；私有同步连接后按同步设置保存到 GitHub。'
}.items():s=s.replace(a,b)
p.write_text(s)
p=ROOT/'src/reader.js';s=p.read_text().replace('只存本设备；清理前请下载原件和导出批注。','本地优先；连接 GitHub 后可跨设备恢复。清理前先核对云端确认状态并保留独立备份。');p.write_text(s)
# Advanced note controls are now intentionally collapsed. Tests open that actual UI.
p=ROOT/'scripts/test_reader.py';s=p.read_text();old="first=page.locator('[name=\"links\"] option').first.get_attribute('value');"
if old in s and 'note-extra' not in s:s=s.replace(old,"page.locator('#note-editor .note-extra').evaluate('e=>e.open=true');"+old)
p.write_text(s)
# Sync hardening discovered during review: reconnect and content-addressed attachment retention.
patch('src/sync.js',"const device=(()=>", "const confirmedObjects=new Set();\nconst device=(()=>")
patch('src/sync.js',"if(await receipt('get',id))return;", "if(confirmedObjects.has(id))return;")
patch('src/sync.js',"await receipt('put',{id,confirmed:true});", "confirmedObjects.add(id);")
patch('src/sync.js',"async function connect(c,token){const next=checkConfig(c);", "async function connect(c,token){if(busy)throw Error('上一次同步仍在结束，请稍候再连接。');const next=checkConfig(c);")
patch('src/sync.js',"connection++;authorization=token.trim();", "connection++;confirmedObjects.clear();authorization=token.trim();")
patch('src/sync.js',"await uploadFiles(merged.entries,snapshot.blobs,ticket);", "await uploadFiles(snapshot.entries,snapshot.blobs,ticket);await uploadFiles(merged.entries,snapshot.blobs,ticket);")
# Exactly known display headings only. No source characters or original IDs are replaced.
# A false embargo/access claim is never inferred from an HTTP failure.
cat=json.loads((ROOT/'resources/catalog.json').read_text())
for r in cat['records']:
 if r['id']=='liang-thesis':
  r['accessStatus']='embargoed';r['accessNote']='2026-09-29通过WUR官方记录的Download PDF正常浏览器入口核验：仓储显示“This object is not available from our repository until: 2026-12-31”。这是该学位论文的仓储暂不开放提示，不代表其已发表章节论文不可获取。尚未取得完整学位论文。';r['embargoNoticeDate']='2026-12-31';r['accessCheckedAt']='2026-09-29';r['candidateURL']='https://edepot.wur.nl/677384'
write('resources/catalog.json',cat)
# Additional original teaching explanations: examples are not claimed as research observations.
study=json.loads((ROOT/'resources/study-v3.json').read_text());terms=study['terms'];papers=json.loads((ROOT/'content/papers.json').read_text());methods=json.loads((ROOT/'content/methods.json').read_text());known_ids={d['id'] for d in papers+methods}
updates=[
 ('pareto-dominance','Pareto dominance','帕累托支配',['Pareto dominance','dominance','支配关系'],'比较两个方案时，若A在所有目标上都不比B差，并且至少一项目标严格更好，就说A支配B。必须先规定每个指标是越大越好还是越小越好。','先逐列比较，不要先把指标相加。例如利润最大化、氮损失最小化，A的利润不少于B且氮损失不高于B，再检查是否至少有一项严格改善。只有全部条件成立，才能淘汰B。','教学例：A利润10、氮损失5；B利润9、氮损失6，因此A支配B。C利润12、氮损失8则与A各有长处，二者不能据这两列直接排出唯一优劣。','不被支配不等于每项都是最好，也不等于已经选出了一个最优方案。',['liang-2022']),
 ('ideal-point','Ideal point','理想点',['ideal point','理想点'],'把每个指标在规定比较范围内的最佳值放在一起，构成一个用于比较的参照点。这个组合未必是任何真实农场。','利润列取最大值，污染列取最小值；不同列的最佳值可以来自不同农场。它说明“各列都达到最好”在哪里，不保证这个组合可同时实现。','教学例：农场A利润100、用水80，B利润80、用水50。利润最大化、用水最小化时，理想点是利润100、用水50；样本里并没有这样的农场。','一定注明理想值来自全样本、子样本还是外部目标，换比较范围可能改变距离。',['liang-2022']),
 ('cluster-centroid','Cluster centroid','聚类中心',['cluster centroid','centroid','聚类中心','群组中心'],'用一组样本的各列平均值代表该组的中心位置。它是概括群组表现的点，不一定对应其中某一个真实样本。','把同组所有农场的利润求平均，再把用水求平均，依次得到一个完整指标组合。比较群组中心可以看总体特征，但还必须检查组内差异。','教学例：两农场的利润是80和120，用水是40和60，中心为利润100、用水50；不能据此说两个农场都恰好是100和50。','平均中心与实际代表样本不同；偏斜分布或离群点会影响平均值。',['liang-2022']),
 ('range-scaling','Range scaling','极差标准化',['range-scaled','range scaling','极差标准化'],'用一列指标的最大值减最小值得到极差，再用它缩放差异，使不同单位的指标能够放在可比较的尺度上。','原来利润差10元和用水差10立方米没有相同意义。分别除以各自的范围后，表达的是在当前比较范围中相差了多大比例。','教学例：利润最小50、最大150，某群组中心130，离最佳值150的差距为20，标准化距离为20/100=0.2。','极差为零时不能直接除；极端值、比较范围改变都会影响结果，标准化也不自动代表没有价值判断。',['liang-2022']),
 ('standard-deviation','Standard deviation','标准差',['standard deviation','标准差'],'用来描述一组数围绕平均值分散得有多开的量，单位与原变量相同。数越集中，标准差通常越小。','先求平均值，再看每个数与平均值的差，平方后合计，按相应分母平均，再开平方。样本标准差通常使用n−1，不能在复现时把论文指定的分母擅自改成n。','教学例：2、2、2完全相同，标准差为0；0、2、4平均值仍为2，但更分散。HDIP中比较的是各指标到理想点的距离，而不是利润原始值。','标准差小只说明数值接近，不说明表现好；各项同样差也可能很均衡。',['liang-2022']),
 ('trade-off','Trade-off','权衡',['trade-off','trade-offs','tradeoff','权衡'],'改善一个目标可能使另一个目标变差，需要在不能同时尽善尽美的结果之间作选择。','先指出哪些目标发生了冲突，再说明这种关系在哪些数据、约束和比较范围内成立。看到散点趋势不等于已经证明因果机制。','教学例：某方案利润更高，但需要更多灌溉；另一个方案节水，但收入稍低。是否接受取舍取决于决策者、用水上限与风险。','相关关系、模型可行边界和利益相关者偏好不是同一种证据，应分开解释。',['breure-2024','liang-2022']),
 ('decision-variable','Decision variable','决策变量',['decision variable','decision variables','决策变量'],'模型中允许设计者调整的量，例如各作物分配多少面积。它不同于已经给定的价格或资源上限。','先问“我实际能改变什么”，再确定取值范围、单位和相互关系。只有把可调整的量写清楚，优化问题才有明确的方案空间。','教学例：一个10公顷农场可以决定小麦和豆类的种植面积。两种面积是决策变量；总土地不超过10公顷是约束。','某个输入是否是决策变量取决于建模设定，不能看到一个数就默认模型可以调整它。',['farmdesign-2012']),
 ('constraint','Constraint','约束',['constraint','constraints','约束'],'方案必须满足的条件，用来划定哪些方案可实施或允许被考虑。违反约束的方案即使得分很好也不可行。','资源约束可以是土地、劳动或资金上限；逻辑约束可以是作物先后次序或不能同时占地。约束需与相应时间和空间范围一致。','教学例：全年总劳动100小时看似够用，但若某一周要80小时、该周只有40小时可用，方案仍不可行。','不能把希望尽量提高的目标与绝对不能超过的上限混为一谈。',['farmsteps-2026','farmdesign-2012']),
 ('scenario','Scenario','情景',['scenario','scenarios','情景'],'对未来或条件变化的一组明确假设，用来问在这种条件下会出现什么结果。情景不是已知未来，也不自动带有发生概率。','写明改变了价格、气候、技术或政策中的哪些量，哪些量保持不变，再比较方案是否仍然可行、结论是否稳定。','教学例：分别考察正常水价、水价上涨20%两个假设。第二种是假设条件下的计算，不是预测水价一定上涨20%。','概率预测、压力测试和情景比较应区别表述。',['breure-2024']),
 ('confounding','Confounding','混杂',['confounding','confounder','混杂','混杂变量'],'比较两个因素的关系时，另一个与二者相关的因素可能影响观察到的关系，使人误把关联解释成直接作用。','观察到某类管理更好的农场产量更高，还要问这些农场是否也有更好的土壤、资金或劳动力条件。不能仅凭分组平均差异断言某措施造成增产。','教学例：受培训的农户产量高，但他们原本可能设备更好。产量差异不能全部归因于培训，除非研究设计和分析能支持这种解释。','识别了潜在混杂并不等于已经消除了它；统计调整也依赖假设和数据。',['liang-2022']),
 ('system-boundary','System boundary','系统边界',['system boundary','system boundaries','系统边界'],'明确一次评价把哪些活动、投入产出、空间范围和时间范围算进去，以及哪些不算。','比较农场排放前，应先确认是否都包括化肥生产、运输、田间排放和土壤变化；如果边界不一致，相同名称的指标也未必可比。','教学例：只算田间燃油与把化肥制造排放也计入，得到的温室气体总量通常不同；这首先是统计边界不同，不是计算器出了错。','边界要按原文说明，未报告的环节不能由读者自行补成已经包含。',['liang-2022','farmdesign-2012']),
 ('sensitivity-analysis','Sensitivity analysis','敏感性分析',['sensitivity analysis','敏感性分析'],'有计划地改变模型输入或假设，观察结果对这些改变有多敏感，用来识别重要因素和不稳健的结论。','先规定改变哪些参数、改变多少、独立改变还是一起改变，再观察指标数值、方案排序或可行性是否变化。','教学例：把作物价格分别下调和上调10%，比较同一农场方案是否仍被选中；排序改变说明结论依赖价格假设。','敏感性高不等于参数本身最不确定，也不等于存在已证实的因果关系。',['breure-2024'])
]
for slug,en,zh,aliases,definition,explanation,example,boundary,sources in updates:
 target=next((t for t in terms if t.get('zh')==zh or any(a.lower()==en.lower() for a in t.get('aliases',[]))),None)
 sources=[x for x in sources if x in known_ids]
 if target:
  target['aliases']=list(dict.fromkeys(target.get('aliases',[])+aliases))
  existing=target.get('explanation','')
  if explanation not in existing:target['explanation']=(existing+'\n\n'+explanation).strip()
  if not target.get('example'):target['example']=example
  elif example not in target['example']:target['example']+='\n\n'+example
  if not target.get('boundary'):target['boundary']=boundary
 else:terms.append({'id':slug,'en':en,'zh':zh,'aliases':aliases,'definition':definition,'explanation':explanation,'example':example,'boundary':boundary,'sources':sources,'scope':'original beginner teaching; synthetic examples are not article data'})
# A coherent reading checkpoint belongs to each existing stage, not a detached list of jargon.
for docid,frame in study['frameworks'].items():
 frame['readingCheck']={'start':'先用自己的话回答：'+frame['question'],'finish':'回到原文证据：'+frame.get('result',frame['phases'][-1]['output']),'scope':'阅读练习，不替代论文结果或作者论证。'}
study['version']='2026-09-29.5';write('resources/study-v3.json',study)
patch('src/workspace.js',"window.PaperStudy?.terms(root);}\nasync function route", "if(frame.readingCheck){const check=document.createElement('section');check.className='guided-reading-check';check.innerHTML='<h2>读完后，把论证连回去</h2><p>'+E(frame.readingCheck.start)+'</p><p>'+E(frame.readingCheck.finish)+'</p><p>写出数据怎样经过方法变成结果；再指出一个结果不能支持的推论。找不到原文证据的部分保留为问题，不自行补齐。</p><a href=\"#/workbook/'+E(id)+'\">把答案记入本篇工作表 →</a>';root.querySelector('.connected-walkthrough')?.after(check)||root.querySelector('.paper-framework')?.append(check);}window.PaperStudy?.terms(root);}\nasync function route")
# Persist a scope-accurate learning change record.
p=ROOT/'content/session-log.json';logs=json.loads(p.read_text()) if p.exists() else []
if not any(x['id']=='update-20260929-reader-v5' for x in logs):
 logs.append({'id':'update-20260929-reader-v5','type':'guide','title':'阅读系统更新：私有同步、轻便便签与可编辑标签','stage':'系统使用','minutes':8,'summary':'本地与GitHub确认状态分离；初次连接才能上传旧笔记，不能把程序发布当成私人数据已同步。','evidence':'软件使用说明；教学例子为自编。机构登录未完成，不声明取得受限全文。','sections':[['跨设备数据如何保存','使用说明','在同步中心连接私有仓库的数据分支。授权只在页面内存中，刷新后需重新连接。等待云端确认再换设备；离线编辑和未上传的附件仍需保留本机。不要把校园密码、GitHub授权或私人全文放进公开网站。','软件行为以实际同步状态为准'],['便签与标签','使用说明','便签使用非模态小窗，点击别处关闭时保存草稿。标签可修改名称、解释、例子和链接，也可移除。私人标签、草稿与冲突记录纳入私有同步及完整备份。','新增交互层，不改原文字符串与段落ID'],['从框架走到证据','教学解释','先把问题、数据、方法和结果串起来，再检查结论边界。术语补充直观解释和自编例子；保留论文自己的定义，不能用通用知识替换原文。','论文条目与方法专题'],['全文状态不是一回事','来源核验','公开可读、机构订阅、仓储禁运、可否公开转载分别记录。梁政渊学位论文的WUR官方入口显示截至2026-12-31的暂不开放提示；不据此推断已发表章节论文无法获取。','WUR官方Download PDF正常浏览器入口，2026-09-29']], 'quiz':[['顶部显示“仅本地”时，换手机是否已经有刚写的笔记？','没有。必须先连接私有同步并等待GitHub确认，程序已经发布不代表浏览器里的旧笔记已经上传。']], 'related':['reader-guide','research-framework']})
write('content/session-log.json',logs)
# The user explicitly requested private cloud persistence; update the previous local-only contract.
p=ROOT/'AGENTS.md';s=p.read_text();s=s.replace('No browser tokens, analytics, CDN or write APIs.','No embedded or persisted authorization secrets, analytics or CDN. Explicitly authorized private-vault API access is allowed under the v5 rules below.')
if '## Private synchronization v5' not in s:s+='\n## Private synchronization v5\nThe user requested local plus private GitHub persistence. Runtime authorization may exist only in page memory after explicit user entry; never in source, storage, logs, URLs or backup. Verify that the destination repository is private before every synchronization; write only the dedicated paper-user-data branch under private/paper-sync/v5/. Preserve concurrent versions and deletion tombstones. An offline/local save is not a cloud confirmation. Existing browser data is not migrated until the user connects and a checkpoint is acknowledged. Do not claim an OAuth service has been deployed. Public website builds must not contain any vault data. Test actual two-device private GitHub writes using synthetic records and an ephemeral CI token; never include real user notes or credentials in test artifacts.\n'
p.write_text(s)
# Standard release tests include the new suite.
p=ROOT/'.github/workflows/pages.yml';s=p.read_text()
if 'python scripts/test_v5.py' not in s:
 anchor='      - name: Save public acceptance report'
 assert anchor in s
 s=s.replace(anchor,'      - name: Test compact notes, custom tags and private-sync semantics\n        run: python scripts/test_v5.py\n'+anchor)
 p.write_text(s)
print(json.dumps({'glossaryTerms':len(terms),'glossaryWithExamples':sum(bool(t.get('example')) for t in terms),'frameworks':len(study['frameworks']),'sourceAnchorPolicy':'unchanged','sync':'requires explicit private-repository connection; no embedded authorization'},ensure_ascii=False))
