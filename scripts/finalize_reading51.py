from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def replace(name,old,new):
 p=ROOT/name;s=p.read_text()
 if new in s:return
 assert s.count(old)==1,(name,s.count(old),old[:80])
 p.write_text(s.replace(old,new))
replace('scripts/build_tutorials.py',"('papers','methods','navigation','session-log','reading-proof-workflow')","('papers','methods','navigation','session-log','reading-proof-workflow','xu-thesis-chapter4')")
replace('src/app.js',"fresh[name]={};store=fresh;}catch", "fresh[name]={};store=fresh;persistedBaseline=JSON.parse(JSON.stringify(fresh));}catch")
p=ROOT/'resources/catalog.json';c=json.loads(p.read_text())
for r in c['records']:
 if r['id']=='farmsteps-2026' and 'Taverne' not in r['accessNote']:
  r['accessNote']+=' 此来源无需登录可读取完整PDF（20页），WUR官方记录标注Taverne；可读不等于已确认允许在本公开仓库再分发。'
p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'content/papers.json';rows=json.loads(p.read_text());x=next(r for r in rows if r['id']=='xu-thesis')
x['evidence']='完整322页PDF已在私有库校验；本轮核读目录、第4章方法及相关结果/讨论文字，未逐图核对所有附录或运行作者数据。'
x['summary']='已从官方摘要导航推进至第4章正文方法带读：类型→同类优秀实践→FarmDESIGN配置与管理情景；完整原件保留私有。'
if not any('2026-09-29正文核读更新' in s[0] for s in x['sections']):
 # Keep old quoted text for annotation relocation, but clearly mark its former evidence date.
 x['sections'][2][0]='上版路线记录（现已有正文补充）'
 x['sections'][2][2]='以下保留此前仅有摘要时的阅读路线，证据状态已更新，请接着看后面的正文核读入口。\n\n'+x['sections'][2][2]
 x['sections'].append(['2026-09-29正文核读更新','原文依据','目录现已核对：第2章印刷页35、第3章101、第4章163、第5章267。第4章题页在该博士版本中注明拟投稿，不把它虚构成已核实有独立DOI的论文。\n\n进入[[xu-chapter4|第4章完整方法链带读]]：分清SC1/SC2现实参照与SC3/SC4模型情景；注意共评价8个指标，但实际优化器包含7个目标，作物多样性在生成后评价。这一差别见§4.2.3.4，不能仅依摘要概括。','Xu 2025博士论文目录（PDF第9页）、第4章印刷页163、175–176；完整PDF有322页'])
 x.setdefault('related',[]).append('xu-chapter4')
p.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'resources/study-v3.json';data=json.loads(p.read_text());frame=data['frameworks'].get('xu-thesis')
if frame and not any(3 in phase.get('sections',[]) for phase in frame['phases']):
 frame['phases'][-1]['sections'].append(3)
 frame['next']='完整原件现已核验，继续进入第4章正文方法带读；旧版摘要路线保留为阅读历史，不代表当前仍未取得全文。'
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'content/reading-proof-workflow.json';data=json.loads(p.read_text());r=data[0]
if 'xu-chapter4' not in r['related']:r['related'].append('xu-chapter4')
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'content/session-log.json';rows=json.loads(p.read_text());r=next(x for x in rows if x['id']=='release-510')
if not any('徐展' in s[0] for s in r['sections']):
 r['sections'].append(['徐展博士论文补读','原文核对','完整PDF已在私有库校验。新增[[xu-chapter4|第4章方法链]]与章节定位，明确8项评价与7项优化目标的区别；不把正文核读说成全部附录、图表和作者代码已经复现。','依据原件目录及§4.2.3.4'])
 r['related'].append('xu-chapter4')
p.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print('Reading connections and original access evidence preserved. No private document was published.')
