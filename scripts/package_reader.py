from pathlib import Path
import json,zipfile

def pack(out):
 out=Path(out);download=out/'downloads';download.mkdir(exist_ok=True)
 for p in download.glob('Paper-*.zip'):p.unlink()
 def zip_files(name,files):
  with zipfile.ZipFile(download/name,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   for p in sorted(files):
    info=zipfile.ZipInfo(p.relative_to(out).as_posix(),date_time=(2026,9,28,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
  assert (download/name).stat().st_size<95000000,'Archive exceeds bounded GitHub file limit'
 def groups_under(root):
  groups=[];group=[];size=0
  for p in sorted(root.rglob('*')):
   if not p.is_file():continue
   if group and size+p.stat().st_size>65000000:groups.append(group);group=[];size=0
   group.append(p);size+=p.stat().st_size
  if group:groups.append(group)
  return groups
 names=[]
 for prefix,root,label in [('Paper-Originals',out/'library','原文与公式'),('Paper-Translation',out/'vendor/translation','本机离线翻译引擎')]:
  for i,files in enumerate(groups_under(root)):
   name=f'{prefix}-{i+1:02d}.zip';zip_files(name,files);names.append({'name':name,'bytes':(download/name).stat().st_size,'kind':label})
 page='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>完整离线包 · Paper Lab</title><link rel="stylesheet" href="../style.css"></head><body><main style="max-width:780px;padding:28px;margin:auto"><h1>完整离线阅读与中文对照</h1><p>下载基础包和下方所需分卷，全部解压到同一个目录，保留library、vendor等路径。在该目录运行 python -m http.server 8000，然后访问 localhost:8000。手机更推荐在主站点击完整缓存。</p><p><a href="Paper-Lab-offline.zip" download>基础网站与教学包</a></p>'+''.join(f'<p><a href="{r["name"]}" download>{r["name"]}</a> · {r["kind"]} · {r["bytes"]/1e6:.1f} MB</p>' for r in names)+'<p>每卷可独立解压，不是传统分割ZIP。所有原文卷构成完整归档，所有翻译卷构成无需联网API的本机翻译引擎。译文在本设备生成、可校订和备份，不预称人工精校。单文件HTML不含原文和模型。</p><a href="../index.html#/offline">返回离线中心</a></main></body></html>'
 (download/'index.html').write_text(page);(out/'offline-packs.json').write_text(json.dumps({'base':'downloads/Paper-Lab-offline.zip','parts':names},ensure_ascii=False,indent=2))
 m=json.loads((out/'offline-manifest.json').read_text());m['core']=sorted(set(m['core']+['./downloads/index.html','./offline-packs.json']));m['library']=[x for x in m['library'] if not x.endswith('.zip') and x!='./downloads/index.html'];(out/'offline-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
 root=Path(__file__).resolve().parents[1];v=json.loads((out/'release.json').read_text())['version'];sw=(root/'src/sw-template.js').read_text().replace('__VERSION__',json.dumps(v)).replace('__CORE__',json.dumps(m['core'])).replace('__LIBRARY__',json.dumps(m['library'])).replace('__BOOKS__',json.dumps(m['books']));(out/'sw.js').write_text(sw)
 zip_files('Paper-Lab-offline.zip',[p for p in out.rglob('*') if p.is_file() and not p.relative_to(out).as_posix().startswith(('library/','vendor/translation/')) and p.suffix!='.zip'])
 print('Offline resource packs:',names)
