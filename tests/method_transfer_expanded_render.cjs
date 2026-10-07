'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),crypto=require('crypto'),assert=require('assert');
const root=path.resolve(__dirname,'..'),site=path.resolve(process.argv[2]||path.join(root,'dist/site'));
const D=JSON.parse(fs.readFileSync(path.join(site,'data.json'),'utf8'));
const source=fs.readFileSync(path.join(root,'src/app.js'),'utf8'),contract=JSON.parse(fs.readFileSync(path.join(root,'tests/method-transfer-expanded-baseline.json'),'utf8'));
assert.equal(crypto.createHash('sha256').update(source).digest('hex'),contract.app_sha256,'The app renderer must be unchanged');
const presentation=JSON.parse(fs.readFileSync(path.join(root,'resources/research-presentation.json'),'utf8')),rules=Object.entries(presentation).sort((a,b)=>b[0].length-a[0].length);
function evaluate(data){
 const window={PAPER_DATA:data,PAPER_SOURCES:JSON.parse(fs.readFileSync(path.join(root,'resources/catalog.json'),'utf8')),PaperLibrary:{explain(s){s=String(s??'');for(const [a,b]of rules)s=s.split(a).join(b);return s;}}};
 const lines=source.split('\n');let code=lines.filter(s=>s.startsWith('const D=')||s.startsWith('const explain=')||s.startsWith('const esc=')||s.startsWith('const safeUrl=')).join('\n')+'\nlet store={notes:{}},blocked=false;\n';
 for(const name of ['localRef','rich','link','dongSourceCorrection','qSourceCorrection','article']){const line=lines.find(s=>s.startsWith('function '+name+'('));assert(line);code+=line+'\n';}
 code+='docs.forEach(d=>store.notes[d.id]="SYNTHETIC retained note <>&");\nglobalThis.rendered=Object.fromEntries(docs.map(d=>[d.id,article(d)]));';
 const context={window,URL};Object.defineProperty(context,'localStorage',{get(){throw Error('No storage mutation allowed')}});Object.defineProperty(context,'indexedDB',{get(){throw Error('No storage mutation allowed')}});vm.runInNewContext(code,context);return context.rendered;
}
const previous={...D,methodTransfers:Object.fromEntries(Object.entries(D.methodTransfers).filter(([id])=>contract.legacy_method_ids.includes(id)||id==='ditzler-2019'))};
const before=evaluate(previous),after=evaluate(D);let additions=0;
for(const doc of D.documents){
 const isNew=Object.hasOwn(contract.new_method_step_counts,doc.id),fragment=isNew?D.methodTransfers[doc.id].html:'';
 if(fragment){assert.equal(after[doc.id].split(fragment).length,2);assert.equal(after[doc.id].replace(fragment,''),before[doc.id]);assert(!fragment.includes('class="prose"'));assert(after[doc.id].indexOf(fragment)>after[doc.id].indexOf(D.researchLeads[doc.id].html));assert(after[doc.id].indexOf(fragment)<after[doc.id].indexOf('<section id="s0">'));additions++;}
 else assert.equal(after[doc.id],before[doc.id]);
}
assert.equal(additions,15);
if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify({before,after}));
console.log(JSON.stringify({passed:true,scope:'Actual unchanged article renderer in Node VM, not browser',old_method_fragments_unchanged:4,old_documents:128,total_documents:D.documents.length,new_method_pages:additions,all_method_pages:Object.keys(D.methodTransfers).length,storage_untouched:true}));
