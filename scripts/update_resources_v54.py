"""Integrate a verified author-deposited resource; never substitute metadata for a run."""
from pathlib import Path
import json,subprocess,sys
R=Path(__file__).resolve().parents[1]
p=R/'resources/method-contracts-v54.json';data=json.loads(p.read_text());c=data['contracts']['ditzler-2019']
resources=[{'label':'作者模型与案例数据：Mendeley Data v1','url':'https://data.mendeley.com/datasets/n3sk27ggwf/1','doi':'10.17632/n3sk27ggwf.1','status':'作者官方归档说明已核实；CC BY 4.0；完整下载、文件内容检查与实际运行状态另计。'},{'label':'WUR论文及关联数据的官方记录','url':'https://research.wur.nl/en/publications/a-model-to-examine-farm-household-trade-offs-and-synergies-with-a/','status':'论文与上述数据记录的关联已核实。'}]
c['authorResources']=resources
note=' 2026-09-29补查：作者已在Mendeley Data发布FarmDESIGN模型与案例农场数据，DOI 10.17632/n3sk27ggwf.1，2019-02-15 v1，标注CC BY 4.0；这改变了原先仅笼统标为缺数据的状态，但找到归档不等于完成下载、软件启动或结果复现。'
if note not in c['evidence']:c['evidence']+=note
c['gaps']=['已找到作者模型与案例数据归档；仍须核对实际文件、版本、依赖和完整性，再复现案例。','家庭案例原始变量与正文公式/参数的对应关系。','非农工作可得性、季节约束和家庭分工在何种范围被表达。','模型可运行与结果一致需要独立验收；不能把程序包可下载等同科学结果已复现。']
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
p=R/'content/papers.json';papers=json.loads(p.read_text());d=next(x for x in papers if x['id']=='ditzler-2019');d['dataUrl']=resources[0]['url']
heading='新增原始资源：作者的模型与案例数据'
if not any(s[0]==heading for s in d['sections']):
 d['sections'].append([heading,'原始资源核验','Mendeley Data于2019-02-15发布v1，DOI 10.17632/n3sk27ggwf.1；说明明确包含本篇FarmDESIGN模型与案例农场数据，许可证CC BY 4.0。WUR研究门户也将这份数据列为本篇关联资料。\n\n这不是本站的教学模拟数据。下一步应从文件清单、模型版本、依赖、案例输入和运行参数开始验收；在实际下载与运行前，不宣称已经复现两户的优化结果。页面的方法账本原文依据区提供可点击的作者归档入口。','Mendeley Data DOI 10.17632/n3sk27ggwf.1；WUR论文页面Datasets与Access to Document，核对日期2026-09-29'])
p.write_text(json.dumps(papers,ensure_ascii=False,indent=2)+'\n')
p=R/'src/contracts.js';t=p.read_text()
anchor="ev.append(link('original/'+id,'进入站内完整原文 →'));"
extra="""for(const r of c.authorResources||[]){const u=new URL(r.url);if(u.protocol!=='https:')continue;const a=el('a',r.label);a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';const row=el('p');row.append(a,el('small',' '+r.status));ev.append(row);}"""
if extra not in t:
 assert anchor in t;t=t.replace(anchor,anchor+extra,1);p.write_text(t)
# Regenerate searchable static ledgers from the now-updated source contracts.
subprocess.run([sys.executable,str(R/'scripts/install_v54.py')],check=True)
print('Verified author-resource links recorded; no source executable run and no original-data reproduction claimed.')
