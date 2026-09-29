"""Add one genuinely obtained licensed article, without replacing existing sources."""
from pathlib import Path
import json,hashlib,re,requests
from datetime import datetime,timezone
from compile_sources import convert
ROOT=Path(__file__).resolve().parents[1]
url='https://cgspace.cgiar.org/bitstreams/0b457171-47c4-48c1-9d6b-13118d7b8e35/download'
expected='c865f2df627aa360e93e07ffd6860d29672e7f25ab0c950a85b890fb2c3e7a62'
r=requests.get(url,timeout=70);r.raise_for_status();raw=r.content
assert raw.startswith(b'%PDF-') and len(raw)<10_000_000
assert hashlib.sha256(raw).hexdigest()==expected,'Source changed: review before updating archive'
import fitz
d=fitz.open(stream=raw,filetype='pdf');assert len(d)==15
text='\n'.join(p.get_text() for p in d);norm=re.sub(r'\s+',' ',text)
assert '10.1016/j.agsy.2019.02.008' in norm and 'Ditzler' in norm
assert re.search(r'creativecommons\.org/licenses/by/4\.0',text,re.I),'Explicit CC BY4.0 evidence required'
license_match=re.search(r'.{0,150}creativecommons\.org/licenses/by/4\.0.{0,100}',norm,re.I)
cp=ROOT/'resources/catalog.json';catalog=json.loads(cp.read_text());entry=next(x for x in catalog['records'] if x['id']=='ditzler-2019')
record={**entry,'status':'licensed','accessStatus':'public-copy-verified','checkedAt':datetime.now(timezone.utc).isoformat(),'accessCheckedAt':datetime.now(timezone.utc).isoformat(),'downloadURL':url,'sourceURL':'https://doi.org/10.1016/j.agsy.2019.02.008','metadataURL':'https://cgspace.cgiar.org/items/a7cb2ba4-2b63-4102-a6b1-d04c63f18934','sha256':expected,'bytes':len(raw),'pages':len(d),'textCharacters':len(text),'license':{'name':'CC BY 4.0','url':'https://creativecommons.org/licenses/by/4.0/','evidence':license_match.group(0),'pageScope':'copyright notice in acquired original'},'accessNote':'已从CGIAR官方仓储取得15页完整主文PDF，并核对原件CC BY4.0声明、DOI、作者与SHA-256。原文正文、原图、原始PDF和EPUB纳入完整离线缓存；不自动代表补充文件和作者模型包已齐全。','scope':'All pages of acquired main article; supplementary data and software are separate resources','noncommercial':True,'technicalChanges':'Technical format conversion only; original bytes and source text retained'}
record.pop('reason',None)
record['aliases']=list(dict.fromkeys(entry.get('aliases',[])+[record['sourceURL'],url,record['metadataURL']]))
base=Path('library')/'ditzler-2019'/expected[:12];out=ROOT/'resources'/base
out.mkdir(parents=True,exist_ok=True);source=out/'source.pdf';source.write_bytes(raw)
book=convert(source,record,out,base.as_posix());assert book['audit']['normalizedCharacterCoverage']==1.0 and len(book['pages'])==15
record.update(bookPath=(base/'book.json').as_posix(),originalPath=(base/'source.pdf').as_posix(),epubPath=(base/'article.epub').as_posix())
catalog['records']=[record if x['id']=='ditzler-2019' else x for x in catalog['records']]
cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
log=ROOT/'content/session-log.json';docs=json.loads(log.read_text())
item={'id':'resource-ditzler-20260929','type':'guide','title':'原文补齐：Ditzler2019已取得完整主文','stage':'资源核验记录','minutes':5,'summary':'新取得的全文与旧带读结论分开记录。主文完整入库不等于作者数据、软件与复现实验全部完成。','sections':[['取得什么','原件核验','从CGIAR官方仓储取得15页主文，校验DOI、作者、原件哈希和CC BY4.0声明。站内原文入口不再停留在未获取提示；原文件和原图随完整缓存保存。'],['对带读有什么用','阅读导航','先读[[ditzler-2019|家庭预算、劳动与营养模块带读]]，再展开完整原文。原文主张和教学例子仍分别标识，新增全文不会自动把之前未核读的全部公式与结果标成已复现。'],['模型数据另有真实入口','资源边界','作者另公开了配套模型与案例数据：DOI 10.17632/n3sk27ggwf.1。当前只核实数据页面与许可，尚未把其中全部软件和输入文件纳入本站，不能用主文替代它们。']],'related':['ditzler-2019','farmdesign-2012','whole-farm']}
docs=[x for x in docs if x['id']!=item['id']]+[item];log.write_text(json.dumps(docs,ensure_ascii=False,indent=2)+'\n')
summary={'id':'ditzler-2019','status':'licensed-full-original','bytes':len(raw),'pages':15,'sha256':expected,'license':'CC BY 4.0','textCoverage':1.0,'sourceURL':url,'supplementsIncluded':False}
(ROOT/'resources/ditzler-2019-recovery.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary))
