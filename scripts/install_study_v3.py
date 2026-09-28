#!/usr/bin/env python3
from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parents[1]
def edit(name,transform):
 p=ROOT/name;s=p.read_text();t=transform(s);p.write_text(t)
def main():
 def index(s):
  if 'study.css' not in s:s=s.replace('<link rel="stylesheet" href="reader.css">','<link rel="stylesheet" href="reader.css"><link rel="stylesheet" href="study.css">')
  if 'study-data.js' not in s:s=s.replace('<script src="reader.js"></script>','<script src="study-data.js"></script><script src="study-layouts.js"></script><script src="study.js"></script><script src="reader.js"></script>')
  s=s.replace('<a href="#/course">七个学习单元</a>','<a href="#/research-framework">完整研究框架</a><a href="#/course">七单元实践计划</a>')
  return s
 edit('src/index.html',index)
 def app(s):
  s=s.replace('href="#/liang-2022">开始第一课 →','href="#/research-framework">先看完整研究框架 →')
  s=s.replace('先联网保存，再测试飞行模式。包括已归档的完整原文、图表、原始文件和阅读器。','先联网保存，再测试飞行模式。包括已归档的原文、图表、阅读器、术语释义和本机翻译引擎。')
  return s
 edit('src/app.js',app)
 def reader(s):
  if 'PaperStudy?.mountOriginal' in s:return s
  s=s.replace('function reset(){selection=null;', 'function reset(){window.PaperStudy?.leave();selection=null;')
  old='await paint();if(ticket!==epoch)return;const saved='
  assert old in s,'Reader lifecycle changed; review integration'
  s=s.replace(old,'await window.PaperStudy?.mountOriginal(b);await paint();if(ticket!==epoch)return;const saved=',1)
  s=s.replace("paint().catch(()=>{});}\nwindow.PaperReader", "window.PaperStudy?.mountLesson(api.route().split('/')[0]);paint().catch(()=>{});}\nwindow.PaperReader",1)
  s=s.replace('window.PaperReader={records:', 'window.PaperReader={layoutChanged:pageInfo,jumpTo:jump,records:',1)
  start=s.index('async function paint()');end=s.index('\nconst href=',start);chunk=s[start:end];assert chunk.endswith('}')
  s=s[:start]+chunk[:-1]+';window.PaperStudy?.terms(root);}'+s[end:]
  s=s.replace('只做格式重排，未翻译、摘要或编辑。复杂公式、表格及双栏顺序可能需查看每页末“原排版核对”；机器转换不等于逐字符人工校对。','英文原文不做摘要或改写；中文对照为独立的本机阅读层，机器译文会注明。识别出的公式以结构化数学或原式保真排版显示，原始提取文字仍可核对；复杂表格及剩余版面问题可查看每页末原排版核对。')
  assert 'PaperStudy?.mountLesson' in s
  return s
 edit('src/reader.js',reader)
 # Inline superscript/subscript restoration never changes textContent or source anchors.
 def study(s):
  if 'function mountInline' in s:return s
  helper="""function mountInline(b){const entry=layouts[b.id];if(!entry||entry.sourceHash!==b.sourceHash)return;for(const [id,ranges] of Object.entries(entry.inline||{})){const el=document.getElementById(id);if(!el||!el.closest('#original-text')||el.dataset.inlineRestored)continue;el.dataset.inlineRestored='v3';for(const r of [...ranges].sort((a,b)=>b.start-a.start)){if(el.textContent.slice(r.start,r.end)!==r.text||!['sup','sub'].includes(r.tag))continue;const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);let n=0,nodes=[];while(walker.nextNode()){const t=walker.currentNode;nodes.push([t,n,n+t.length]);n+=t.length;}for(const [t,a,z] of nodes.reverse()){const start=Math.max(a,r.start)-a,end=Math.min(z,r.end)-a;if(end<=start)continue;const range=document.createRange();range.setStart(t,start);range.setEnd(t,end);const tag=document.createElement(r.tag);tag.className='source-inline-script';range.surroundContents(tag);}}}}\n"""
  s=s.replace('function mountEquations(b){',helper+'function mountEquations(b){mountInline(b);',1)
  s=s.replace("${g.number?'('+E(g.number)+')':''}","${g.number&&g.mathml?'('+E(g.number)+')':''}")
  return s
 edit('src/study.js',study)
 study=json.loads((ROOT/'resources/study-v3.json').read_text());papers=json.loads((ROOT/'content/papers.json').read_text());titles={x['id']:x['title'] for x in papers}
 j=study['journey'];sections=[["先理解整条研究链","教学框架",j['question']+'\n\n'+'\n\n'.join(j['narrative'])]]
 for stage in j['stages']:
  text=stage['question']+'\n\n这一阶段以'+stage['input']+'为依据，形成'+stage['output']+'。'+stage['next']+'\n\n'+' → '.join('[['+p+'|'+titles.get(p,p)+']]' for p in stage['papers'])
  sections.append([stage['title'],'研究流程',text])
 entry={'id':'research-framework','type':'guide','title':j['title'],'stage':'从全局进入论文','minutes':20,'summary':'先掌握问题、系统边界、证据和方法之间的关系，再进入每篇论文的连续论证与细节。','sections':sections,'quiz':[["为什么不先学习所有软件？","软件只解决研究链中的特定环节。先明确对象、可调整决策、约束和证据，再选择工具，才能避免方法和问题脱节。"],["感知、偏好和优化为什么不能混为一项结果？","它们分别描述认识、相对优先级和模型中的可行选择。连接时需要明确接口，并保留各自证据边界。"]],'related':['course','liang-2022','liang-2023','cheng-2023','cheng-2025','farmdesign-2012','hainan-map']}
 p=ROOT/'content/navigation.json';nav=json.loads(p.read_text());nav=[x for x in nav if x['id']!='research-framework'];nav.insert(0,entry);p.write_text(json.dumps(nav,ensure_ascii=False,indent=2)+'\n')
 p=ROOT/'content/session-log.json';log=json.loads(p.read_text());id='study-bilingual-framework-2026-09-28'
 if not any(x['id']==id for x in log):log.append({'id':id,'type':'guide','title':'带读框架、逐段中文与点按术语','stage':'学习站更新','minutes':3,'summary':'保留英文、旧笔记和锚点，增加整体研究框架、逐段本机译文、公式版面与点按释义。','sections':[['带读结构','更新记录','先阅读完整研究框架，再进入每篇论文的研究问题、阶段衔接和方法细节。旧章节与笔记位置保留。'],['中文对照','更新记录','右侧开关控制逐段中文。机器译文在本机生成与缓存，可校订、导出与导入；不把机器译文说成人工精校。完整缓存包含离线引擎，不依赖在线翻译API。'],['公式与术语','更新记录','公式按原件恢复版面；确定的表达使用MathML，其余用原式保真图并保留提取文字。点击术语显示带来源的释义，点击别处或Escape关闭。']],'related':['research-framework','offline-help']});p.write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
 shutil.copyfile(ROOT/'scripts/build_study.py',ROOT/'scripts/build_reader.py');shutil.copyfile(ROOT/'scripts/package_study.py',ROOT/'scripts/package_reader.py')
 p=ROOT/'AGENTS.md';s=p.read_text()
 if '## Study layer v3' not in s:s+='\n## Study layer v3\nPreserve English source strings, block IDs and existing local annotations. Framework narratives and glossary definitions must cite actual lessons/sources. Translation is a separate on-device layer, labelled as unreviewed machine output; do not publish translations of NoDerivatives sources. All browser inference assets are local, pinned and license/hash checked. No note or private source goes to an inference API. Math changes are technical presentation only; retain source crops and raw blocks. Run scripts/test_study.py in addition to existing browser/reader tests. Update math overlays on original-source refresh; never silently reinterpret ambiguous symbols.\n';p.write_text(s)
 print('Study v3 integrated; existing English strings and annotation stores preserved.')
if __name__=='__main__':main()
