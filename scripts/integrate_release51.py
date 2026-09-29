"""One-time exact source migration for application version and safe automatic updates."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def replace(name,old,new):
 p=ROOT/name;s=p.read_text()
 if new in s:return
 assert s.count(old)==1,(name,'expected unique source anchor',old[:80],s.count(old))
 p.write_text(s.replace(old,new))
p=ROOT/'src/app.js';s=p.read_text();start=s.find("if('serviceWorker' in navigator&&location.protocol!=='file:'){")
if start>=0:
 end=s.index('\n})();',start)
 s=s[:start]+"window.PaperRelease.init({savePosition});"+s[end:];p.write_text(s)
else:assert 'window.PaperRelease.init({savePosition});' in s
replace('src/index.html','<link rel="stylesheet" href="comfort.css">','<link rel="stylesheet" href="comfort.css"><link rel="stylesheet" href="release.css">')
replace('src/index.html','<script src="app.js"></script>','<script src="release.js"></script><script src="app.js"></script>')
replace('src/workspace.js','window.PaperWorkspace={route,','window.PaperWorkspace={isBusy:()=>state.importing||requests.size>0,route,')
replace('src/study.js','window.PaperStudy={','window.PaperStudy={isBusy:()=>busy||pending.size>0,')
replace('scripts/build_reader.py',"'sync.js','comfort.js','comfort.css']:shutil", "'sync.js','comfort.js','comfort.css','release.js','release.css']:shutil")
replace('scripts/build_reader.py',"'src/sync.js','src/comfort.js','src/comfort.css']:","'src/sync.js','src/comfort.js','src/comfort.css','src/release.js','src/release.css','src/sw-template.js','resources/application-release.json']:")
replace('scripts/build_reader.py',"version=digest.hexdigest()[:12];data['version']=version", "version=digest.hexdigest()[:12];data['version']=version;application=json.loads((ROOT/'resources/application-release.json').read_text());data['application']=application")
replace('scripts/build_reader.py',"['reader.css','study.css','workspace.css','comfort.css']:","['reader.css','study.css','workspace.css','comfort.css','release.css']:")
replace('scripts/build_reader.py',"'workspace.js','sync.js','comfort.js']:single=", "'workspace.js','sync.js','comfort.js','release.js']:single=")
replace('scripts/build_reader.py',"release.update(version=version,workspace=", "release.update(version=version,appVersion=application['version'],application=application,automaticUpdate='all-tabs-idle-safe',workspace=")
# Mutable downloads belong to the versioned core, never the shared immutable source cache.
replace('scripts/build_reader.py',"large=('library/','downloads/','vendor/translation/')", "large=('library/','vendor/translation/')")
p=ROOT/'src/sw-template.js';s=p.read_text()
addition="""
/* Negotiate with every same-scope page before switching code beneath it. */
async function safeActivate(event){
 const sender=event.source;try{const u=new URL(sender?.url||'');if(u.origin!==SCOPE.origin||!u.pathname.startsWith(SCOPE.pathname))return;}catch{return;}
 const windows=(await self.clients.matchAll({type:'window',includeUncontrolled:true})).filter(c=>{try{const u=new URL(c.url);return u.origin===SCOPE.origin&&u.pathname.startsWith(SCOPE.pathname);}catch{return false;}});
 const answers=await Promise.all(windows.map(c=>new Promise(resolve=>{const channel=new MessageChannel();const timer=setTimeout(()=>{channel.port1.close();resolve({ready:false,reason:'另一个标签页尚未支持安全更新，请关闭不用的旧标签页'});},2500);channel.port1.onmessage=e=>{clearTimeout(timer);channel.port1.close();resolve(e.data?.ready===true?{ready:true}:{ready:false,reason:e.data?.reason||'其他标签页正在使用'});};c.postMessage({type:'PAPER_CAN_UPDATE',version:VERSION},[channel.port2]);})));
 const blocked=answers.find(a=>!a.ready);event.ports[0]?.postMessage(blocked?{accepted:false,reason:blocked.reason}:{accepted:true,version:VERSION});if(!blocked)await self.skipWaiting();
}
self.addEventListener('message',e=>{if(e.data?.type==='PAPER_SAFE_ACTIVATE')e.waitUntil(safeActivate(e));});
"""
if 'async function safeActivate' not in s:p.write_text(s+addition)
# If an already-authorized switch races with renewed interaction, reload later, not mid-edit.
replace('src/release.js','cacheBusy=false;', 'cacheBusy=false,needsReload=false;')
replace('src/release.js','function reloadSafely(){if(reloading)return;', 'function reloadSafely(){needsReload=true;if(reloading)return;')
replace('src/release.js','if(!document.hidden){check();maybeApply();}},15000)', 'if(!document.hidden){check();if(needsReload)reloadSafely();else maybeApply();}},15000)')
replace('src/release.js',"dialog[open],.context-popover,.term-popover,#translation-editor", "dialog[open],.context-popover,.term-popover,#translation-editor,#release-panel")
# Mark source-level preferences without storing any credential values.
p=ROOT/'AGENTS.md';s=p.read_text()
if '## User defaults: no configuration chores' not in s:
 s+='''\n## User defaults: no configuration chores\nShow a human-readable release number in the visible UI and retain the exact content/source identifiers for diagnosis. Automatically test, publish and mirror confirmed changes; do not routinely hand repository or deployment settings back to the user. Prefer managed server-side authorization and minimal first-use identity verification. Never implement “automatic” by embedding shared tokens, exposing private vault routes anonymously, or persisting secrets in public assets. If the connected services cannot safely receive a secret or provision the backend, name that exact remaining dependency rather than claim completion. No user-provided secrets or full chat messages belong in maintenance records.\nAutomatic updates must wait for all active reading tabs, preserve input/selection/import/sync work and existing on-device data, and distinguish new code from a confirmed private-data checkpoint. The v5 page-memory GitHub session must not be silently discarded. Keep old caches if fetching or installing new files fails.\n''';p.write_text(s)
p=ROOT/'content/session-log.json';rows=json.loads(p.read_text())
if not any(x['id']=='release-510' for x in rows):
 rows.append({'id':'release-510','type':'guide','title':'v5.1.0：版本号与保护笔记的自动更新','stage':'更新记录','minutes':4,'summary':'程序更新不等于私人数据已同步；默认自动检查，正在编辑或连接同步时延后刷新。','sections':[['看懂三个状态','使用说明','页头v5.1.0是程序版本；内容校验值用于辨认准确构建；顶部云端状态表示私人数据是否已获GitHub确认，三者不能互相替代。'],['自动更新如何保护阅读','使用说明','新版本先下载核心资源，再询问同一站点的所有标签页是否可以切换。输入、选字、导入、翻译或当前GitHub会话未结束时，不强制刷新。已经做过完整离线缓存的设备，更新后自动补齐新增资源；失败时保留旧数据。'],['授权处理边界','使用说明','免填令牌的长期登录需要受保护的服务端。目前仍等待安全托管连接，不能宣称已配置或把共享密钥放进网页。已有手动会话同步保留可用。'],['继续完善的带读','学习建议','进入[[reading-proof-workflow|完整论文带读验收]]，先完成从问题到证据的整篇论证，再进入术语和方法细节。']], 'related':['research-framework','reading-proof-workflow']});p.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'CHANGELOG.md';s=p.read_text();marker='## 5.1.0'
if marker not in s:
 s=s.replace('# 更新记录','# 更新记录\n\n## 5.1.0 · 2026-09-29\n\n- 页头、侧栏与版本面板展示易读版本、日期和内容校验值。\n- 默认自动检查，所有标签页安全后切换；保留编辑、选字、导入、翻译、私有同步会话。\n- 已完整缓存设备自动补齐新版资源；可变化的下载文件移入版本化缓存，避免旧离线包残留。\n- 新增完整论文带读验收方法，记录无需用户反复配置的维护偏好。\n- 免填令牌长期登录仍待安全托管连接；没有在本轮存储或公开用户提供的凭据。\n')
 p.write_text(s)
# Permanent CI acceptance, with existing checks unchanged.
p=ROOT/'.github/workflows/pages.yml';s=p.read_text()
if 'Test safe automatic releases' not in s:
 s=s.replace('      - name: Save public acceptance reports','      - name: Test safe automatic releases\n        run: |\n          node --check src/release.js\n          python scripts/test_release51.py\n      - name: Save public acceptance reports')
 s=s.replace('          cp test-results/v5-report.json dist/site/v5-validation.json','          cp test-results/v5-report.json dist/site/v5-validation.json\n          cp test-results/release51-report.json dist/site/release51-validation.json')
 p.write_text(s)
print('Exact integration complete. Existing reader strings and storage schemas were not rewritten.')
