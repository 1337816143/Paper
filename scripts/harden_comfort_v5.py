"""Source fixes found in pre-release integrity review, with idempotent hooks."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def patch(path,old,new):
 p=ROOT/path;s=p.read_text()
 if new in s:return
 assert old in s,(path,old[:60]);p.write_text(s.replace(old,new,1))
patch('src/sync.js','let value=row;if(store===\'files\')','let value=clone(row);if(store===\'files\')')
p=ROOT/'src/sync.js';s=p.read_text().replace("document.dispatchEvent(new CustomEvent('paper-sync-applied'","window.dispatchEvent(new CustomEvent('paper-sync-applied'").replace("document.dispatchEvent(new Event('paper-sync-applied'","window.dispatchEvent(new Event('paper-sync-applied'");p.write_text(s)
patch('src/sync.js',"if(store==='files'||store==='books')fileMemo.clear();", "if(store==='files'||store==='books'){fileMemo.clear();try{localStorage.setItem('paper-sync-file-revision-v5',Date.now()+'-'+device);}catch{}}")
patch('src/sync.js',"window.PaperSync={connect,", "addEventListener('storage',e=>{if(e.key==='paper-sync-file-revision-v5'){fileMemo.clear();changed('other-tab-files');}});\nwindow.PaperSync={connect,")
# Strong validation after all per-record hashes have been checked.
patch('src/sync.js',"async function readRemote(){", """function validateReferences(entries){for(const [k,e] of Object.entries(entries)){if(e.deleted)continue;const [db,store,id]=validKey(k),v=e.value;
 if(db==='paper-lab-reader-v2'&&store==='books'){const file=entries[key(db,'files',id+'/original')];if(!file||file.deleted||file.value.sha256!==v.sourceHash)throw Error('导入论文的原件缺失或与书目哈希不匹配；未声明完整同步');for(const page of v.pages){if(page.snapshot){const image=entries[key(db,'files',page.snapshot)];if(!page.local||!image||image.deleted||!page.snapshot.startsWith(id+'/'))throw Error('导入论文的原页图片缺失或关联错误');}}}
 if(db==='paper-comfort-v5'&&store==='tags'){if(typeof v.label!=='string'||v.label.length>100||typeof v.text!=='string'||v.text.length>15000||v.href&&!window.PaperComfort.safeLink(v.href))throw Error('云端标签内容或链接不安全');}
 if(db==='settings'&&(typeof v!=='string'||v.length>10000))throw Error('阅读设置字段无效');
 if(db==='paper-workspace-v4'&&store==='references'&&v.landing&&!window.PaperWorkspace.safeURL(v.landing))throw Error('书目链接不安全');
}}\nasync function readRemote(){""")
patch('src/sync.js',"await validate(payload.entries);return", "await validate(payload.entries);validateReferences(payload.entries);return")
patch('src/sync.js',"await validate(merged.entries);await uploadFiles", "await validate(merged.entries);validateReferences(merged.entries);await uploadFiles")
# Applying or removing a private custom term refreshes existing decorations too.
patch('src/study.js','function clearSourceTerms(){', """function replaceCustomTerms(rows){for(const [id,t] of termsById)if(t.custom)termsById.delete(id);for(const e of document.querySelectorAll('.term-word[data-study-term^=\"custom-\"]'))e.replaceWith(...e.childNodes);for(const e of document.querySelectorAll('a[data-study-term^=\"custom-\"]')){delete e.dataset.studyTerm;e.classList.remove('term-link');}addTerms(rows);}\nfunction clearSourceTerms(){""")
patch('src/study.js','window.PaperStudy={','window.PaperStudy={replaceCustomTerms,')
p=ROOT/'src/comfort.js';s=p.read_text().replace('window.PaperStudy?.addTerms(rows)','window.PaperStudy?.replaceCustomTerms(rows)');p.write_text(s)
# Cloud confirmation timestamps cannot be silently invalidated by spurious position writes.
p=ROOT/'src/reader.js';s=p.read_text();s=s.replace("put('positions',{id:docid,block:x?.id,y:scrollY,offset:x?.getBoundingClientRect().top||0,at:Date.now()}).catch(()=>{});", "const next={id:docid,block:x?.id,y:scrollY,offset:x?.getBoundingClientRect().top||0,at:Date.now()};get('positions',docid).then(old=>{if(!old||old.block!==next.block||Math.abs((old.y||0)-next.y)>1||Math.abs((old.offset||0)-next.offset)>1)return put('positions',next);}).catch(()=>{});")
p.write_text(s)
print('Private checkpoint hashes, live-store events, source attachments and per-tab caches hardened.')
