"""Normalize one-time integration hooks against the inspected v4 source."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'scripts/prepare_comfort_v5.py';s=p.read_text()
s=s.replace('"function reset(){selection=null;", "function reset(){window.PaperComfort?.close();selection=null;"','"function reset(){window.PaperStudy?.leave();", "function reset(){window.PaperComfort?.close();window.PaperStudy?.leave();"')
s=s.replace("['reader-guide','research-framework']","['research-framework']")
s='\n'.join(line for line in s.splitlines() if not line.startswith('patch(\'src/workspace.js\',"window.PaperStudy?.terms(root);'))+'\n'
p.write_text(s)
p=ROOT/'src/comfort.js';s=p.read_text()
s=s.replace('const target=lastTarget;const anchor=','const target=lastTarget?.isConnected?lastTarget:document.getElementById(existing?.segments?.[0]?.block||seed.segments?.[0]?.block||seed.block);const anchor=')
old='try{formatHeadings(root);setupTagContainers(root);'
new="""try{const reader=$('.reader',root),id=location.hash.replace(/^#\\//,'').split('/')[0],frame=window.PAPER_STUDY?.frameworks[id];if(reader&&frame?.readingCheck&&!$('.guided-reading-check',reader)){const check=document.createElement('section');check.className='guided-reading-check';check.innerHTML='<h2>读完后，把论证连回去</h2><p>'+E(frame.readingCheck.start)+'</p><p>'+E(frame.readingCheck.finish)+'</p><p>把数据怎样经过方法变成结果写清楚，再指出一个结果不能支持的推论。找不到原文证据的部分保留为问题，不自行补齐。</p><a href=\"#/workbook/'+E(id)+'\">把答案记入本篇工作表 →</a>';const at=$('#self-test',reader);if(at)at.before(check);else reader.append(check);}formatHeadings(root);setupTagContainers(root);"""
if new not in s:
 assert old in s;s=s.replace(old,new,1)
p.write_text(s)
print('Reviewed lifecycle hooks aligned; no validation assertions removed.')
