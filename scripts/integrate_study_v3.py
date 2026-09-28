#!/usr/bin/env python3
"""One-time, idempotent integration. Original PDFs/books and user storage stay intact."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
def edit(path,old,new,marker=None):
 p=ROOT/path;s=p.read_text()
 if marker and marker in s:return
 if new in s:return
 assert old in s,(path,'expected source fragment absent',old[:100]);p.write_text(s.replace(old,new,1))
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
 edit('src/index.html','<link rel="stylesheet" href="reader.css">','<link rel="stylesheet" href="reader.css"><link rel="stylesheet" href="study.css">')
 edit('src/index.html','<script src="reader.js"></script>','<script src="study-data.js"></script><script src="study.js"></script><script src="reader.js"></script>')
 edit('src/index.html','<a href="#/course">七个学习单元</a>','<a href="#/study-map">研究框架 · 从全局到一篇</a><a href="#/course">七个学习单元</a>')
 edit('src/reader.js','function reset(){selection=null;','function reset(){window.PaperStudy?.leave();selection=null;')
 edit('src/reader.js',"function blockHTML(b){if(b.kind==='image')", "function blockHTML(b){const enhanced=window.PaperStudy?.blockHTML(b,book);if(enhanced!==null&&enhanced!==undefined)return enhanced;if(b.kind==='image')")
 edit('src/reader.js','book=b;docid=id;','book=b;docid=id;await window.PaperStudy?.loadOriginal(b);if(ticket!==epoch)return;')
 edit('src/reader.js',"settings();$('#reader-mode').onclick", "window.PaperStudy?.enhanceOriginal(b);settings();$('#reader-mode').onclick")
 edit('src/reader.js','只做格式重排，未翻译、摘要或编辑。复杂公式、表格及双栏顺序可能需查看每页末“原排版核对”；机器转换不等于逐字符人工校对。','英文原文及原文件保持不变；中文对照是单独的阅读辅助层，逐段标注机器初译或已核译，不能替代原文。公式采用原件完整裁图，已核对的表达式另有数学排版。复杂表格及双栏顺序仍可查看每页末“原排版核对”；未声称完成逐字符人工校对。')
 edit('src/reader.js',"x.dataset.block=x.id;});paint().catch", "x.dataset.block=x.id;});window.PaperStudy?.enhanceLesson();paint().catch")
 edit('src/reader.js',"m.onclick=e=>{e.stopPropagation();edit(n);};", "m.onclick=e=>{if(e.target.closest('.term-token'))return;e.stopPropagation();edit(n);};")
 # Open collapsed method details on old deep links; preserve browser back exact scroll restoration.
 edit('src/app.js',"else if(section&&document.getElementById(section))document.getElementById(section).scrollIntoView();", "else if(section&&document.getElementById(section)){window.PaperStudy?.reveal(section);document.getElementById(section).scrollIntoView();}")
 edit('src/app.js','<a class="btn secondary" href="#/course">查看完整学习路线</a>','<a class="btn secondary" href="#/study-map">先建立完整研究框架</a>')
 # Adapt native-selection test to semantic nested text, not an assumption that firstChild is a text node.
 edit('scripts/test_reader.py',"const el=[...document.querySelectorAll('[data-block]')].find(e=>e.textContent.length>200);el.scrollIntoView();const t=el.firstChild,r=document.createRange();r.setStart(t,0);r.setEnd(t,Math.min(80,t.length));", "const el=[...document.querySelectorAll('[data-block]')].find(e=>e.textContent.length>200&&e.getBoundingClientRect().height>0);el.scrollIntoView();const w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);let t;while(w.nextNode()){if(w.currentNode.length>20){t=w.currentNode;break;}}if(!t)throw Error('No selectable text');const r=document.createRange();r.setStart(t,0);r.setEnd(t,Math.min(80,t.length));")
 # Source-faithful references: Liang 2022 methods actually places distances in section 2.5.2.
 gp=ROOT/'study/glossary.json';g=json.loads(gp.read_text())
 for t in g['terms']:
  if t['id'] in ['ideal-point','midip','hdip','hca','ward','standardization']:
   t['sources']=[[pid,where.replace('§2.6–2.7','§2.5.2').replace('§2.6','§2.5.2')] if pid=='liang-2022' else [pid,where] for pid,where in t['sources']]
 dump(gp,g)
 fp=ROOT/'study/frameworks.json';f=json.loads(fp.read_text());global_=f['global'];sections=[['整套论文要共同回答什么','学习框架',global_['question']+'\n\n'+global_['framing']]]
 for i,x in enumerate(global_['stages']):sections.append([f'{i+1}. '+x['title'],'研究链条',x['text']+'\n\n输入：'+x['input']+'\n输出：'+x['output']+'\n\n对应阅读：'+' → '.join('[['+id+'|'+id+']]' for id in x['links'])])
 for x in global_['lanes']:sections.append([x['title'],'论文之间的接口',x['text']+'\n\n'+' → '.join('[['+id+'|'+id+']]' for id in x['papers'])])
 sections.append(['怎样从框架读到细节','阅读方式','每篇先读研究问题、四步论证链和每一步的连贯解释，再按需展开该步原有的方法、公式、读图和复现细节。原文出处与旧链接保留，不靠罗列术语替代研究论证。\n\n先能讲清为什么要做下一步，再学习下一步的工具。术语可以就地点读；理解后点旁边关闭，不必离开当前论证。'])
 entry={'id':'study-map','type':'guide','title':global_['title'],'stage':'完整研究框架','minutes':25,'summary':'问题与边界 → 现实数据 → 系统表达 → 方案探索 → 人的需求 → 可信度检验。先连成论证，再进入每篇。','sections':sections,'quiz':[['能否直接把农户的Q排序当成景观优化权重？','不能。需要另行定义偏好到目标、约束或方案筛选的接口。'],['为什么一项单地块可行的轮作未必构成全农场可行方案？','同时期多个地块可能共同超出水、劳动或其他共享资源约束。']],'related':['liang-2022','cheng-2023','xu-data-2024','hainan-map','course']}
 p=ROOT/'content/session-log.json';log=json.loads(p.read_text());log=[x for x in log if x['id'] not in ['study-map','study-v3-update']];log.extend([entry,{'id':'study-v3-update','type':'guide','title':'逐段中文、公式与系统化带读更新','stage':'版本说明','minutes':5,'summary':'保留英文、原件和已有笔记；增加独立译文层、可核对公式与完整论证框架。','sections':[['研究框架先行','内容更新','全部21个文献条目重新组织为问题—步骤—输入输出—结论边界—下一篇。旧精读内容移入对应步骤的展开区，未删减；原s编号和笔记锚点保留。'],['译文范围与质量','证据边界','公开允许改编的8份原文配备逐段中文初译；带禁止演绎条款的4份原文译文仅通过本机私人包导入，不公开发布。中文不是作者认可的译本，数值、单位与方法细节仍须对照英文。'],['公式与术语','格式修复','原式优先依据PDF坐标恢复完整显示，避免将分子、分母、根号等分别当作正文段落。梁2022式9—12另提供已对照原式的MathML与式义。其距离方法的准确章节为§2.5.2；部分旧带读引用曾写§2.6，本轮作显式更正。'],['本机资料不公开','隐私边界','选字标记、便签、导入原件和私人译文只保存在浏览器。定期导出备份；网站更新不能替代个人备份。']],'quiz':[],'related':['study-map','corrections','offline-help']}]);dump(p,log)
 # Strengthen MathML insertion guard: exact paper revision, page and equation label must agree.
 p=ROOT/'scripts/prepare_study_layout.py';s=p.read_text();old="and label in ['9','10','11','12']:";new="and label in ['9','10','11','12'] and p['number']==(6 if label=='12' else 5):";s=s.replace(old,new);p.write_text(s)
 print('Integrated study v3: original IDs/storage preserved; coherent frameworks installed.')
if __name__=='__main__':main()
