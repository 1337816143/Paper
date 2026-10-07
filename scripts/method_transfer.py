"""Reviewed additive method-transfer explanations; no source or note rewriting."""
from pathlib import Path
import html,json,re

def load_method_transfers(root,document_ids):
    path=Path(root)/'resources/method-transfer.json'
    if not path.exists():return {}
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema')!='paper.method-transfer.v1':raise ValueError('Invalid method-transfer schema')
    result={}
    def p(text,identity):
        if not isinstance(text,str) or not text.strip():raise ValueError('Empty method-transfer text')
        return '<p id="'+identity+'" data-block="'+identity+'">'+html.escape(text)+'</p>'
    for pid,row in data['papers'].items():
        if not re.fullmatch('[a-z0-9-]+',pid) or pid not in document_ids:raise ValueError('Unknown method-transfer paper')
        if not row['url'].startswith('https://doi.org/'):raise ValueError('Method transfer requires a canonical DOI')
        base='method-transfer-'+pid
        block='<section class="method-transfer" id="'+base+'" data-method-transfer="'+pid+'" data-no-terms style="overflow-wrap:anywhere;font-size:var(--body-size,17px)"><h2>'+html.escape(data['title'])+'</h2>'
        block+=p(row['intro'],base+'-intro')
        block+='<p class="source-note">2026-10-07 · 原文方法、合成版本与拟议接口分别标明 · <a href="'+html.escape(row['url'],quote=True)+'" target="_blank" rel="noopener noreferrer">原论文来源</a> · <a href="#/original/'+pid+'">站内原文与旧批注</a></p>'
        block+='<details><summary>先分清研究A、研究B和四种不同的量</summary>'
        for i,text in enumerate(data['scope'],1):block+=p(text,base+'-scope-'+str(i))
        block+='</details><h3>'+html.escape(row['title'])+'</h3>'+p(row['chain'],base+'-chain')
        ids=set()
        for n,step in enumerate(row['steps'],1):
            sid=step['id']
            if not re.fullmatch('[a-z0-9-]+',sid) or sid in ids:raise ValueError('Invalid method-transfer step ID')
            ids.add(sid);identity=base+'-'+sid
            block+='<details id="'+identity+'"><summary>'+str(n)+'. '+html.escape(step['title'])+'</summary>'
            for i,field in enumerate(step['fields'],1):block+=p(field['label']+'：'+field['text'],identity+'-p'+str(i))
            block+='</details>'
        block+='<h3>接入前的口径与待核事项</h3>'
        for i,note in enumerate(row['notes'],1):
            identity=base+'-note-'+str(i)
            block+='<details id="'+identity+'"><summary>'+html.escape(note['title'])+'</summary>'+p(note['text'],identity+'-p1')+'</details>'
        block+='</section>'
        result[pid]={'html':block,'steps':len(row['steps'])}
    return result

def static_transfer_html(transfer,pid):
    return transfer.get('html','').replace('href="#/original/'+pid+'"','href="../index.html#/original/'+pid+'"')
