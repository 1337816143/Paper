'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),crypto=require('crypto'),assert=require('assert');
const root=path.resolve(__dirname,'..'),site=path.resolve(process.argv[2]||path.join(root,'dist/site'));
const D=JSON.parse(fs.readFileSync(path.join(site,'data.json'),'utf8'));
const current=fs.readFileSync(path.join(root,'src/app.js'),'utf8'),contract=JSON.parse(fs.readFileSync(path.join(root,'tests/research-leads-baseline.json'),'utf8'));
const marker="${D.researchLeads?.[d.id]?.html||''}";assert.equal(current.split(marker).length,2);
const original=current.replace(marker,'');assert.equal(crypto.createHash('sha256').update(original).digest('hex'),contract.app_sha256);
const presentation=JSON.parse(fs.readFileSync(path.join(root,'resources/research-presentation.json'),'utf8'));
const rules=Object.entries(presentation).sort((a,b)=>b[0].length-a[0].length);
function evaluate(source){
 const window={PAPER_DATA:D,PAPER_SOURCES:JSON.parse(fs.readFileSync(path.join(root,'resources/catalog.json'),'utf8')),PaperLibrary:{explain(s){s=String(s??'');for(const [a,b]of rules)s=s.split(a).join(b);return s;}}};
 const lines=source.split('\n');let code=lines.filter(s=>s.startsWith('const D=')||s.startsWith('const explain=')||s.startsWith('const esc=')||s.startsWith('const safeUrl=')).join('\n')+'\nlet store={notes:{}},blocked=false;\n';
 for(const name of ['localRef','rich','link','dongSourceCorrection','qSourceCorrection','article']){
  const line=lines.find(s=>s.startsWith('function '+name+'('));assert(line,'Actual renderer missing '+name);code+=line+'\n';
 }
 code+='docs.forEach(d=>store.notes[d.id]="SYNTHETIC retained note <>&");\nglobalThis.rendered=Object.fromEntries(docs.map(d=>[d.id,article(d)]));';
 const context={window,URL};Object.defineProperty(context,'localStorage',{get(){throw Error('No legacy storage access allowed')}});Object.defineProperty(context,'indexedDB',{get(){throw Error('No legacy DB access allowed')}});
 vm.runInNewContext(code,context);return context.rendered;
}
const old=evaluate(original),next=evaluate(current);let changed=0;
for(const d of D.documents){const fragment=D.researchLeads?.[d.id]?.html||'';if(fragment){assert.equal(next[d.id].split(fragment).length,2);assert.equal(next[d.id].replace(fragment,''),old[d.id]);assert(!fragment.includes('class="prose"'));assert(fragment.includes('data-block="research-lead-'+d.id+'-full-p1"'));changed++;}else assert.equal(next[d.id],old[d.id]);}
assert.equal(changed,Object.keys(D.researchLeads||{}).length);
if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify({before:old,after:next}));
console.log(JSON.stringify({passed:true,scope:'Actual article function in Node VM, not browser',legacy_articles_byte_equal_after_removing_addition:contract.legacy_document_ids.length,total_documents:D.documents.length,appended_papers:changed,synthetic_notes_preserved:true,storage_untouched:true}));
