"""Reviewed additive method-transfer explanations; no source or note rewriting."""
from pathlib import Path
import html,json,re

def load_method_transfers(root,document_ids,filename='method-transfer.json'):
    if filename not in {'method-transfer.json','method-transfer-expanded.json','method-transfer-ditzler.json'}:raise ValueError('Invalid method-transfer file')
    path=Path(root)/'resources'/filename
    if not path.exists():return {}
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema')!='paper.method-transfer.v1':raise ValueError('Invalid method-transfer schema')
    result={}
    def p(text,identity):
        if not isinstance(text,str) or not text.strip():raise ValueError('Empty method-transfer text')
        multiline=' style="white-space:pre-line"' if '\n' in text else ''
        return '<p id="'+identity+'" data-block="'+identity+'"'+multiline+'>'+html.escape(text)+'</p>'
    for pid,row in data['papers'].items():
        if not re.fullmatch('[a-z0-9-]+',pid) or pid not in document_ids:raise ValueError('Unknown method-transfer paper')
        if not row['url'].startswith('https://doi.org/'):
            catalog_path=Path(root)/'resources/catalog.json'
            catalog=json.loads(catalog_path.read_text(encoding='utf-8')) if catalog_path.exists() else {'records':[]}
            approved={record.get('sourceURL') for record in catalog['records'] if record.get('id')==pid}
            if not row['url'].startswith('https://') or row['url'] not in approved:raise ValueError("Method transfer requires this paper's canonical source URL")
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
        previous_title=None
        for i,note in enumerate(row['notes'],1):
            identity=base+'-note-'+str(i)
            if note['title']!=previous_title:
                if previous_title is not None:block+='</details>'
                block+='<details id="'+identity+'"><summary>'+html.escape(note['title'])+'</summary>'
            block+=p(note['text'],identity+'-p1')
            previous_title=note['title']
        if previous_title is not None:block+='</details>'
        block+='</section>'
        result[pid]={'html':block,'steps':len(row['steps'])}
    return result

def static_transfer_html(transfer,pid):
    return transfer.get('html','').replace('href="#/original/'+pid+'"','href="../index.html#/original/'+pid+'"')

def static_source_notice(root,pid):
    """Add a source-availability note without rewriting the original method fragment."""
    records=json.loads((Path(root)/'resources/catalog.json').read_text(encoding='utf-8'))['records']
    record=next((row for row in records if row.get('id')==pid),None)
    archived=bool(record and record.get('bookPath'))
    kind='public-archive' if archived else 'source-status'
    label='站内归档原文（篇级）' if archived else '来源状态 / 本机原文（篇级）'
    text=('本站已有许可归档正文，此链接打开论文入口。各步骤的页码与公式编号是定位文字，不是逐页直达链接。' if archived else '本站未公开托管本篇全文。此链接按本机已有原件打开，或显示来源状态与合法导入入口；不表示已公开全文。页码与公式编号仅作定位说明。')
    return '<p id="method-transfer-source-status-'+pid+'" class="source-note method-transfer-access" data-method-source-status="'+kind+'" data-no-terms>'+html.escape(text)+' <a href="../index.html#/original/'+pid+'">'+html.escape(label)+'</a></p>'
