from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=R/'scripts/build_tutorials.py';t=p.read_text();old="'sampling-v53','indicator-audit-v53')";new="'sampling-v53','indicator-audit-v53','method-ledgers-v54','paper-ledgers-v54')"
if new not in t:assert old in t;t=t.replace(old,new,1);p.write_text(t)
p=R/'src/personal.js';t=p.read_text();old='async function boot(fragment=initialFragment){if(booting)return;';new='async function boot(fragment=initialFragment){if(booting){if(fragment)setTimeout(()=>boot(fragment),80);return;}'
if new not in t:assert old in t;t=t.replace(old,new,1);p.write_text(t)
p=R/'src/contracts.js';t=p.read_text();old='const block=cache.get(route)||make(route,C[route]);cache.set(route,block);';new="const block=cache.get(route)||make(route,C[route]);for(const box of block.querySelectorAll('.research-note-box')){const f=box.querySelector('textarea');if(f&&document.activeElement!==f){try{const value=JSON.parse(localStorage.getItem('paper-lab-learning-v1')||'{}').notes?.[box.dataset.noteKey]||'';f.value=value;f._researchBase=value;}catch{}}}cache.set(route,block);"
if new not in t:assert old in t;t=t.replace(old,new,1);p.write_text(t)
p=R/'scripts/test_personal_v54.py';t=p.read_text();old='def confirmed(page):page.wait_for_function("window.PaperPersonal?.status().state===\'connected\' && PaperSync.status().state===\'synced\'",timeout=90000)';new='''def confirmed(page):
 try:page.wait_for_function("window.PaperPersonal?.status().state==='connected' && PaperSync.status().state==='synced'",timeout=90000)
 except Exception:
  safe=page.evaluate("()=>({personal:PaperPersonal.status(),sync:{state:PaperSync.status().state,message:PaperSync.status().message,busy:PaperSync.status().busy,dirty:PaperSync.status().dirty}})")
  (OUT/'personal-v54-failure.json').write_text(json.dumps({'completed':checks,'safeStatus':safe,'data':'synthetic-only; no entry URLs or secrets'},ensure_ascii=False,indent=2))
  raise
'''
if 'personal-v54-failure.json' not in t:assert old in t;t=t.replace(old,new,1);p.write_text(t)
print('Registered complete static method ledgers and preserved private entry initialization without exposing secrets.')
