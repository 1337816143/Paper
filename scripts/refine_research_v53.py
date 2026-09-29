from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'src/app.js';t=p.read_text();old="window.PaperReader?.attachLesson();requestAnimationFrame(";new="window.PaperReader?.attachLesson();window.PaperResearch?.enhance();requestAnimationFrame("
if new not in t:
 assert old in t;t=t.replace(old,new,1);p.write_text(t)
p=root/'src/research.js';t=p.read_text()
if 'const mountedResearch=new Map();' not in t:
 t=t.replace("function enhance(){scheduled=false;", "const mountedResearch=new Map();\nfunction enhance(){scheduled=false;",1)
 old="root.dataset.researchV53='true';const d=docs.get(id),p=R.papers?.[id];"
 new="""root.dataset.researchV53='true';root.dataset.researchDoc=id;const cached=mountedResearch.get(id);if(cached&&id!=='research-feedback'){
 root.querySelector('.articlehead')?.after(...cached.top);
 for(const [anchor,node] of cached.sections)root.querySelector('#'+anchor)?.append(node);
 for(const box of $$('.research-note-box',root)){const f=$('textarea',box);try{const value=state().notes[box.dataset.noteKey]||'';if(document.activeElement!==f){f.value=value;f._researchBase=value;}}catch{}}
 cloudStatus(root);
}else{const d=docs.get(id),p=R.papers?.[id];"""
 assert old in t;t=t.replace(old,new,1)
 old="if(id==='research-feedback')dashboard(root).catch(e=>{root.append(document.createTextNode('读取个人输入失败：'+e.message));});}"
 new="""if(id==='research-feedback')dashboard(root).catch(e=>{root.append(document.createTextNode('读取个人输入失败：'+e.message));});
 if(id!=='research-feedback'){mountedResearch.set(id,{top:$$(':scope > .research-bridge,:scope > .research-indicator-table,:scope > .sampling-grid-section',root),sections:$$(':scope > section > .research-section-tools',root).map(n=>[n.parentElement.id,n])});if(mountedResearch.size>10)mountedResearch.delete(mountedResearch.keys().next().value);}
 }}"""
 assert old in t;t=t.replace(old,new,1)
 p.write_text(t)
# Test the additional detail-state preservation, not merely route restoration.
p=root/'scripts/test_research_v53.py';t=p.read_text()
t=t.replace("document.querySelector(\"#view .reader\")?.dataset.researchV53',arg=id)","document.querySelector(\"#view .reader\")?.dataset.researchDoc===id',arg=id)")
old="check('Original-evidence navigation returns to guided reading',page.url.endswith('#/liang-2022'))"
new=old+";check('Expanded original evidence and its exact text remain available after returning',page.locator('.research-bridge > .research-evidence').first.evaluate('(e)=>e.open') and page.locator('.research-bridge .research-excerpt').count()>0)"
if new not in t:
 assert old in t;t=t.replace(old,new,1)
p.write_text(t)
print('Mounted research additions before scroll restoration; cached open evidence survives back-navigation.')
