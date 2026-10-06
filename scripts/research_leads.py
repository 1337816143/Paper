"""Optional reviewed text introductions. No image, network or private-data access."""
from pathlib import Path
import hashlib,html,json,re
SCHEMA='paper.research-leads.v1'
def load_research_leads(root,document_ids):
    folder=Path(root)/'resources/research-leads';manifest=folder/'accepted.json'
    if not manifest.exists():return {}
    data=json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('schema')!=SCHEMA:raise ValueError('Unsupported research-lead schema')
    leads={}
    for pid,row in data['papers'].items():
        if not re.fullmatch(r'[a-z0-9-]+',pid) or pid not in document_ids:raise ValueError('Unknown research-lead target: '+pid)
        paragraphs={};hashes={}
        for version in ['full','brief']:
            spec=row[version]
            if not spec.get('accepted'):raise ValueError('Unreviewed research lead: '+pid+'/'+version)
            path=folder/pid/(version+'.txt');raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
            if digest!=spec['sha256']:raise ValueError('Research lead changed after review: '+pid+'/'+version)
            text=raw.decode('utf-8').rstrip('\r\n');parts=re.split(r'\r?\n\s*\r?\n',text)
            if not text or any(not part.strip() for part in parts):raise ValueError('Empty research-lead paragraph')
            paragraphs[version]=parts;hashes[version]=digest
        # Never use the legacy .prose class: attachLesson numbers those paragraphs.
        # These explicit IDs allow new annotations while preserving all legacy indices.
        block='<section class="research-lead-overlay" data-research-lead="'+pid+'" data-no-terms>'
        block+='<nav aria-label="研究串讲版本"><a href="#/'+pid+'/research-lead-'+pid+'-full">读完整版串讲</a> · <a href="#/'+pid+'/research-lead-'+pid+'-brief">读简略串讲</a></nav>'
        for version,title in [('full','完整研究串讲'),('brief','简略研究串讲')]:
            block+='<div id="research-lead-'+pid+'-'+version+'" class="research-lead-copy" data-lead-version="'+version+'" data-lead-sha256="'+hashes[version]+'" style="font-size:var(--body-size,17px);overflow-wrap:anywhere"><h2>'+title+'</h2>'
            for index,paragraph in enumerate(paragraphs[version],1):
                block_id='research-lead-'+pid+'-'+version+'-p'+str(index)
                block+='<p id="'+block_id+'" data-block="'+block_id+'">'+html.escape(paragraph,quote=True)+'</p>'
            block+='</div>'
        block+='</section>'
        leads[pid]={'html':block,'hashes':hashes,'paragraphs':{k:len(v) for k,v in paragraphs.items()}}
    return leads

def static_lead_html(lead,pid):
    """Use native in-page anchors for the script-free static page."""
    return lead.get('html','').replace('href="#/'+pid+'/','href="#')
