from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def edit(path,old,new):
 p=ROOT/path;t=p.read_text()
 if new in t:return
 if old not in t:raise ValueError('Missing exact integration anchor: '+path+' '+old[:80])
 p.write_text(t.replace(old,new,1))
def main():
 c=json.loads((ROOT/'resources/method-contracts-v54.json').read_text());assert c['schema']=='paper.method.contracts.v1' and len(c['contracts'])==21
 papers=json.loads((ROOT/'content/papers.json').read_text());ids={p['id'] for p in papers};assert set(c['contracts'])==ids
 for id,x in c['contracts'].items():
  for key in ['object','question','evidence','inputs','process','outputs','limits','transfer','practice','gaps']:assert x.get(key),id+' missing '+key
  assert all(len(row)==4 for row in x['inputs'])
 edit('src/index.html','<link rel="stylesheet" href="research.css">','<link rel="stylesheet" href="research.css"><link rel="stylesheet" href="contracts.css">')
 edit('src/index.html','<script src="app.js"></script>','<script src="contracts-data.js"></script><script src="contracts.js"></script><script src="personal.js"></script><script src="app.js"></script>')
 edit('src/index.html','<a href="#/research-studio">','<a href="#/method-ledgers">逐篇方法账本与掌握证据</a><a href="#/research-studio">')
 edit('src/index.html','<meta charset="utf-8">','<meta charset="utf-8"><meta name="referrer" content="no-referrer">')
 edit('src/app.js','window.PaperResearch?.enhance();requestAnimationFrame(','window.PaperResearch?.enhance();window.PaperContracts?.mount();requestAnimationFrame(')
 edit('src/release.js',"if(s?.connected)return {ready:false,reason:","if(s?.connected&&!window.PaperPersonal?.safeToReload?.())return {ready:false,reason:")
 # The decrypted GitHub token remains in the existing sync engine's page memory.
 # A separate explicit personal-entry capability stores authenticated ciphertext.
 p=ROOT/'src/personal.js';t=p.read_text();t=t.replace("function cleanURL(){history.replaceState(history.state,'',location.pathname+location.search+'#/research-studio');}","function cleanURL(){history.replaceState(history.state,'',location.pathname+location.search+'#/research-studio');dispatchEvent(new HashChangeEvent('hashchange'));}")
 p.write_text(t)
 p=ROOT/'scripts/build_reader.py';t=p.read_text()
 if 'PAPER_CONTRACTS' not in t:
  t=t.replace(" research=json.loads((ROOT/'resources/research-v53.json').read_text())"," contracts=json.loads((ROOT/'resources/method-contracts-v54.json').read_text())\n assert len(contracts['contracts'])==21\n research=json.loads((ROOT/'resources/research-v53.json').read_text())",1)
  t=t.replace("'research.js','research.css','research-review.js']:shutil.copyfile", "'research.js','research.css','research-review.js','contracts.js','contracts.css','personal.js']:shutil.copyfile",1)
  t=t.replace(" (out/'research-data.js').write_text", " (out/'contracts-data.js').write_text(js('PAPER_CONTRACTS',contracts))\n shutil.copyfile(ROOT/'examples/paper_minilab.py',out/'examples/paper_minilab.py')\n (out/'research-data.js').write_text",1)
  t=t.replace("'src/research-review.js']:","'src/research-review.js','src/personal.js','src/contracts.js','src/contracts.css','resources/method-contracts-v54.json','examples/paper_minilab.py']:",1)
  t=t.replace("'release.css','research.css']:single", "'release.css','research.css','contracts.css']:single",1)
  t=t.replace("'research-data.js','research.js']:single", "'research-data.js','research.js','contracts-data.js','contracts.js','personal.js']:single",1)
  t=t.replace(" (out/'release.json').write_text", " release['methodContracts']={'count':len(contracts['contracts']),'syntheticExercises':21,'masteryInferredFromVisit':False}\n release['personalEntry']={'schema':'paper.personal.entry.v1','requiresManualTokenInput':False,'requiresPrivateEntryOnNewDevice':True,'anonymousPublicAccess':False,'deviceStorage':'authenticated ciphertext plus non-extractable CryptoKey; excluded from backups','realUserTokenStatus':'selected and permission-tested automatically on private entry; not independently verified during public build'}\n release['sync']['automaticConnection']='after-user-held-private-entry'\n release['researchStudio']['automaticSignIn']='private-capability-entry'\n (out/'release.json').write_text",1)
  p.write_text(t)
 # Add static searchable copies of the method ledgers, not just runtime-only cards.
 overview={'id':'method-ledgers','type':'guide','title':'逐篇方法账本：网站完成不等于方法掌握','stage':'证据与实践','summary':'21个文献条目逐个追踪研究对象、输入结构、转换、输出、限制和最小练习。自动保存的是你的学习证据，不自动替你判断已掌握。','sections':[['四个不同的完成状态','使用说明','资料已取得、带读已建立、教学练习已运行、原文结果已复现，是四件不同的事情。本系统逐项报告缺口，不因为有网页、读过或勾选完成，就宣布你掌握了模型。'],['从任何一篇开始','阅读入口','\n\n'.join('[['+id+'|'+p['title']+']]' for p in papers for id in [p['id']])],['自己的输入不会被改成助手结论','使用说明','每个方法账本保留数据结构、推导、运行差异、反例和研究迁移的小框。它们采用原有本地优先与私有同步；原话保留，后续辅导另给建议。尚无云端确认的设备输入不能假称助手已读。'],['复现需要实际材料','证据边界','paper_minilab.py包含21条目对应的可运行机制练习或编码/接口检查。质性研究、框架和未取得全文的博士论文，不能靠生成一组数就算复现。完整结果复现仍需作者原始数据、代码、清洗、版本、参数与实验条件。']],'related':['reading-proof-workflow','research-feedback','research-decisions','research-studio']}
 (ROOT/'content/method-ledgers-v54.json').write_text(json.dumps([overview],ensure_ascii=False,indent=2)+'\n')
 docs=[]
 for p in papers:
  id=p['id'];x=c['contracts'][id]
  rows=['；'.join(row) for row in x['inputs']]
  docs.append({'id':'ledger-'+id,'type':'guide','title':'方法账本｜'+p['title'],'stage':'逐篇方法证据','summary':x['question'],'sections':[['研究对象','原文方法整理',x['object']],['原文依据与证据边界','核验范围',x['evidence']],['输入数据结构','按原文方法整理，非作者数据文件','字段/数据组；层级；形式/单位；用途\n\n'+'\n\n'.join(rows)],['转换与输出','方法链','\n\n'.join(str(i+1)+'. '+s for i,s in enumerate(x['process']))+'\n\n输出：'+x['outputs']],['最小练习','自编教学机制',x['practice']['do']+'\n\n运行：python paper_minilab.py --case '+id+'\n\n应能说明：'+x['practice']['expect']+'\n\n未复现：'+x['practice']['notReproduced']],['限制与未解决问题','不能补造',x['limits']+'\n\n'+'\n\n'.join(x['gaps'])],['对我的研究的启发','迁移建议',x['transfer']+'\n\n[['+id+'|返回带读和可填写的方法账本]]']],'related':[id,*x['links']]})
 (ROOT/'content/paper-ledgers-v54.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2)+'\n')
 release={'schema':'paper.application.release.v1','version':'5.4.0','date':'2026-09-29','title':'专属入口自动连接与逐篇方法账本','changes':['新增私有入口：不在网页手填令牌；加密保存在本设备，刷新后自动连接。','新设备使用同一专属入口自动恢复，不向匿名公共访客开放私人数据。','已连接且加密入口可恢复时，自动更新不再因会话授权而无限延迟。','21个文献条目逐一建立对象、输入表、转换、输出、限制、原文依据与未解决问题。','21个标准库教学机制练习及独立学习证据小框；不把网页完成当作方法掌握。','继续核查官方原文入口；下载失败、许可与精读/复现状态分别报告。'],'automaticUpdate':'idle-and-all-tabs-safe','managedSignIn':'private-entry-client-encrypted-no-hosted-server','credentialPolicy':'No plaintext or decryptable shared GitHub credentials in repository/public website; the user-held entry capsule remains private'}
 (ROOT/'resources/application-release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
 p=ROOT/'AGENTS.md';t=p.read_text()
 if '## Personal entry v5.4' not in t:
  t+='''\n## Personal entry v5.4 and mastery evidence\nThe user explicitly requested no frontend token typing and automatic recovery on new devices. The implementation uses a USER-HELD PRIVATE capability entry, not anonymous public access or an embedded shared PAT. Only authenticated ciphertext and a non-extractable WebCrypto key may be stored in the separate paper-personal-device-v1 database; decrypted PATs remain in memory. That database and any entry URL/capsule are strictly excluded from backups, sync checkpoints, public source, logs, screenshots and test reports. A private entry can grant broad access matching its PAT, so never publish it. New devices must open that private entry; ordinary public URLs cannot identify them. This explicit user-approved encrypted device mode supersedes the prior requirement to discard all authorization capability on reload; legacy manually connected sessions remain memory-only.\nActual write/readback must pass before confirming access; do not infer full token scopes from repository roles or connector permissions. Code builds never claim that user PATs were independently tested. Test with ephemeral private-repo CI authorization, synthetic records and isolated test branches only. Never weaken CAS, tombstones, source identity or private boundaries.\n21 per-paper method ledgers link source evidence, input schema, transformations, outputs, limitations, transfer and minimal exercises. Teaching fixtures are not author data or original result reproduction. Keep mastery notes distinct from webpage completion; preserve the user's explanations and failures. Inspect all successfully synchronized user inputs using the private review protocol each relevant turn.\n'''
  p.write_text(t)
 print('Integrated v5.4; no plaintext credentials or user notes accessed.')
if __name__=='__main__':main()
