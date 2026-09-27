#!/usr/bin/env python3
"""Build a fully local static learning site. No network dependencies."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,hashlib,html,json,re,shutil,struct,subprocess,zipfile,zlib
ROOT=Path(__file__).resolve().parents[1]

def png_icon(size):
    rows=[]
    for y in range(size):
        row=bytearray([0])
        for x in range(size):
            stem=size*.28<x<size*.4 and size*.23<y<size*.78
            top=size*.35<x<size*.69 and (size*.23<y<size*.33 or size*.46<y<size*.56)
            side=size*.59<x<size*.69 and size*.3<y<size*.49
            row.extend((245,249,241,255) if stem or top or side else (23,92,80,255))
        rows.append(bytes(row))
    def chunk(t,b):return struct.pack('!I',len(b))+t+b+struct.pack('!I',zlib.crc32(t+b)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows),9))+chunk(b'IEND',b'')

def source_date(commit):
    try:
        date=subprocess.check_output(['git','show','-s','--format=%cI',commit],cwd=ROOT,stderr=subprocess.DEVNULL,text=True).strip()
        return datetime.fromisoformat(date).astimezone(timezone(timedelta(hours=8))).date().isoformat()
    except (ValueError,OSError,subprocess.CalledProcessError):
        return datetime.now(timezone(timedelta(hours=8))).date().isoformat()

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='dist/site');p.add_argument('--source-commit',default='local');p.add_argument('--date');a=p.parse_args()
    date=a.date or source_date(a.source_commit);out=Path(a.out).resolve()
    if out==ROOT or (ROOT in out.parents and out.name in {'src','content','examples','scripts'}):raise ValueError('Unsafe output directory')
    if out.exists():shutil.rmtree(out)
    for d in ('read','downloads','examples'):(out/d).mkdir(parents=True,exist_ok=True)
    documents=[]
    for name in ('papers','methods','navigation','session-log'):
        file=ROOT/'content'/f'{name}.json'
        if file.exists():documents+=json.loads(file.read_text(encoding='utf-8'))
    byid={d['id']:d for d in documents}
    if len(byid)!=len(documents):raise ValueError('Duplicate content ID')
    # Citation locator correction only: original definitions are preserved.
    d=byid['liang-2022'];d['sections'][2][3]='§2.5.1–2.5.2；§3.1–3.2';d['sections'][3][3]='§2.5.2，公式9–12；零范围处理为实现补充'
    aliases={'home','library','methods','notes','offline','search','lab'}|set(byid)
    for d in documents:
        if not re.fullmatch('[a-z0-9-]+',d['id']) or not d.get('sections'):raise ValueError('Invalid document')
        refs=re.findall(r'\[\[([a-z0-9-]+)\|',json.dumps(d,ensure_ascii=False))+(d.get('related') or [])+(d.get('sources') or [])
        if set(refs)-aliases:raise ValueError('Broken links: '+str(set(refs)-aliases))
    files={f.name:f.read_text(encoding='utf-8') for f in sorted((ROOT/'examples').iterdir()) if f.is_file() and f.suffix in {'.py','.R','.csv','.md'}}
    for name,text in files.items():(out/'examples'/name).write_text(text,encoding='utf-8')
    inputs=sorted([*(ROOT/'content').glob('*.json'),*(ROOT/'src').glob('*'),*(ROOT/'examples').glob('*'),Path(__file__)])
    digest=hashlib.sha256(b''.join(f.read_bytes() for f in inputs if f.is_file())).hexdigest()[:12]
    data={'version':digest,'sourceCommit':a.source_commit,'updated':date,'documents':documents,'files':files}
    datajs='window.PAPER_DATA='+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+';\n'
    for name in ('index.html','style.css','app.js'):shutil.copyfile(ROOT/'src'/name,out/name)
    # Mobile controls must use the same custom property as desktop, not a fixed size.
    css=(out/'style.css').read_text(encoding='utf-8')+'\n@media(max-width:800px){.reader .prose{font-size:var(--body-size)!important}}\n'
    (out/'style.css').write_text(css,encoding='utf-8');(out/'data.js').write_text(datajs,encoding='utf-8')
    (out/'icon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192"><rect width="192" height="192" rx="36" fill="#175c50"/><path d="M55 145V46H115V99H66M66 58H104V87H66" fill="none" stroke="#f5f9f1" stroke-width="13"/></svg>')
    for n in (192,512):(out/f'icon-{n}.png').write_bytes(png_icon(n))
    manifest={'name':'Paper Lab · 农业系统论文带读','short_name':'Paper Lab','id':'./','start_url':'./#/home','scope':'./','display':'standalone','background_color':'#f4f5f0','theme_color':'#175c50','lang':'zh-CN','icons':[{'src':f'icon-{n}.png','sizes':f'{n}x{n}','type':'image/png','purpose':'any maskable'} for n in (192,512)]}
    (out/'manifest.webmanifest').write_text(json.dumps(manifest,ensure_ascii=False),encoding='utf-8');(out/'.nojekyll').touch()
    def rich(s):
        text=html.escape(str(s));text=re.sub(r'\[\[([a-z0-9-]+)\|([^\]]+)\]\]',lambda m:f'<a href="../index.html#/{m[1]}">{m[2]}</a>',text)
        return '<p>'+text.replace('\n\n','</p><p>').replace('\n','<br>')+'</p>'
    def shell(title,body):return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+' · Paper Lab</title><link rel="stylesheet" href="../style.css"></head><body><main style="max-width:850px;margin:auto;padding:28px"><p><a href="../index.html">Paper Lab</a> / <a href="index.html">静态目录</a></p>'+body+'</main></body></html>'
    index=[]
    for d in documents:
        title=html.escape(d['title']);body='<header class="articlehead"><span class="eyebrow">'+html.escape(d.get('stage',''))+'</span><h1>'+title+'</h1><p>'+html.escape(d.get('en',''))+'</p><p>'+html.escape(d.get('citation',''))+'</p>'+rich(d.get('summary',''))+'</header>'
        if d.get('evidence'):body+='<div class="notice">核读范围：'+html.escape(d['evidence'])+'</div>'
        if d.get('url'):body+='<p><a target="_blank" rel="noopener noreferrer" href="'+html.escape(d['url'],quote=True)+'">原始文献来源 ↗</a></p>'
        body+='<p><a href="../index.html#/'+d['id']+'">交互阅读、保存位置与笔记 →</a></p>'
        for i,s in enumerate(d['sections']):body+=f'<section class="reader" id="s{i}"><span class="kind">{html.escape(s[1])}</span><h2>{i+1}. {html.escape(s[0])}</h2><div class="prose">{rich(s[2])}</div>'+('<p class="source-note">'+html.escape(s[3])+'</p>' if len(s)>3 else '')+'</section>'
        for q,ans in d.get('quiz',[]):body+='<details><summary>'+html.escape(q)+'</summary>'+rich(ans)+'</details>'
        if d.get('sources'):body+='<h2>来源与应用</h2>'+''.join('<p><a href="'+i+'.html">'+html.escape(byid[i]['title'])+'</a></p>' for i in d['sources'])
        (out/'read'/f'{d["id"]}.html').write_text(shell(d['title'],body),encoding='utf-8');index.append(f'<p><a href="{d["id"]}.html">{title}</a></p>')
    (out/'read/index.html').write_text(shell('静态目录','<h1>论文与方法全文目录</h1>'+''.join(index)),encoding='utf-8')
    app=(out/'app.js').read_text(encoding='utf-8');base=(out/'index.html').read_text(encoding='utf-8')
    single=base.replace('<link rel="stylesheet" href="style.css">','<style>'+css+'body.single a[href^="read/"],body.single a[href^="downloads/"]{display:none}</style>')
    single=re.sub(r'<link rel="(?:icon|manifest)"[^>]+>','',single).replace('<body>','<body class="single">')
    single=single.replace('<script src="data.js"></script>','<script>'+datajs+'</script>').replace('<script src="app.js"></script>','<script>'+app.replace('</script','<\\/script')+'</script>')
    (out/'downloads/Paper-Lab-offline.html').write_text(single,encoding='utf-8')
    (out/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    release={'version':digest,'sourceCommit':a.source_commit,'updated':date,'documents':len(documents),'paperEntries':sum(d['type'] in ('paper','thesis') for d in documents),'methodEntries':sum(d['type']=='method' for d in documents),'externalPDFsCached':False}
    (out/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2),encoding='utf-8')
    asset_paths=sorted('./'+str(f.relative_to(out)).replace('\\','/') for f in out.rglob('*') if f.is_file() and f.name not in {'.nojekyll','data.json'})
    (out/'sw.js').write_text("""'use strict';
const VERSION=__VERSION__, ASSETS=__ASSETS__;
const PREFIX='paper-lab:'+new URL(self.registration.scope).pathname+':', CACHE=PREFIX+VERSION;
const URLS=ASSETS.map(p=>new URL(p,self.registration.scope).href);
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(URLS.map(u=>new Request(u,{cache:'reload'}))))));
self.addEventListener('activate',e=>e.waitUntil((async()=>{for(const k of await caches.keys())if(k.startsWith(PREFIX)&&k!==CACHE)await caches.delete(k);await self.clients.claim();})()));
self.addEventListener('message',e=>{if(e.data?.type==='SKIP_WAITING')self.skipWaiting();if(e.data?.type==='STATUS')e.waitUntil((async()=>{const c=await caches.open(CACHE);let n=0;for(const u of URLS)if(await c.match(u))n++;e.ports[0]?.postMessage({complete:n===URLS.length,count:n,expected:URLS.length,version:VERSION});})());});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url),scope=new URL(self.registration.scope);if(e.request.method!=='GET'||u.origin!==scope.origin||!u.pathname.startsWith(scope.pathname))return;e.respondWith((async()=>{const c=await caches.open(CACHE);const normalized=u.pathname===scope.pathname?new URL('index.html',scope).href:e.request;const hit=await c.match(normalized);if(hit)return hit;try{return await fetch(e.request);}catch{return new Response('该资源未在离线包中。请返回已缓存的论文正文。',{status:503,headers:{'Content-Type':'text/plain;charset=utf-8'}});}})());});
""".replace('__VERSION__',json.dumps(digest)).replace('__ASSETS__',json.dumps(asset_paths)),encoding='utf-8')
    with zipfile.ZipFile(out/'downloads/Paper-Lab-offline.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for f in sorted(out.rglob('*')):
            if f.is_file() and f.suffix!='.zip':
                info=zipfile.ZipInfo(str(f.relative_to(out)).replace('\\','/'),date_time=(2026,9,28,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,f.read_bytes())
    print(json.dumps(release,ensure_ascii=False));print('Built',out)
if __name__=='__main__':main()
