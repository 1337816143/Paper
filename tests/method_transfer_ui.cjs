'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const ui=require('../src/method-transfer-ui.js');
const paper='liang-2022',block='method-transfer-liang-2022-exp-liang22-step1-p1';
assert.equal(ui.parseTarget('#/liang-2022/'+block,paper),block);
assert.equal(ui.parseTarget('#/liang-2022/method-transfer-liang-2022',paper),'method-transfer-liang-2022');
for(const value of ['#/liang-2022/s0','#/liang-2023/'+block,'#/original/liang-2022/'+block,'#/liang-2022/method-transfer-liang-2023-note-1','#/liang-2022/'+block+'/extra'])assert.equal(ui.parseTarget(value,paper),null,value);
assert.equal(ui.parseTarget('#/liang-2022/'+block,'bad"id'),null);
assert.equal(ui.sourceAccess({bookPath:'library/example/book.json'}).kind,'public-archive');
assert.match(ui.sourceAccess({bookPath:'library/example/book.json'},true).text,/单HTML不包含原件/);
for(const value of [null,{}, {accessStatus:'private-copy-verified'}]){
 const access=ui.sourceAccess(value);assert.equal(access.kind,'source-status');assert.match(access.text,/未公开托管/);assert.match(access.text,/本机/);
}
const root={tagName:'SECTION',parentElement:null},outer={tagName:'DETAILS',open:false,parentElement:root},inner={tagName:'DETAILS',open:false,parentElement:outer},target={tagName:'P',parentElement:inner},other={tagName:'DETAILS',open:false,parentElement:root};
root.contains=node=>[root,outer,inner,target,other].includes(node);
assert.equal(ui.openParents(target,root),true);assert.equal(outer.open,true);assert.equal(inner.open,true);assert.equal(other.open,false);
assert.equal(ui.openParents({parentElement:null},root),false);assert.equal(ui.openParents(null,root),false);
const source=fs.readFileSync(path.join(__dirname,'../src/method-transfer-ui.js'),'utf8');
for(const forbidden of ['localStorage','sessionStorage','indexedDB','fetch(','XMLHttpRequest','history.pushState','history.replaceState','PaperReader.put'])assert(!source.includes(forbidden),forbidden);
assert(source.includes('root.removeAttribute(\'data-no-terms\')'));
assert(source.includes("root.querySelectorAll('summary,h2,h3')"));
assert(source.includes('win.location.hash!==requestedHash'));
assert(source.includes("node.tagName==='DETAILS'"));
const index=fs.readFileSync(path.join(__dirname,'../src/index.html'),'utf8');assert(index.indexOf('src="method-transfer-ui.js"')>index.indexOf('src="app.js"'));
console.log(JSON.stringify({passed:true,scope:'Pure helper and source-boundary checks; not browser interaction',namespaceLimited:true,ancestorDetailsOnly:true,sourceKindsSeparated:true,noStorageOrNetworkMutation:true,staleNavigationGuarded:true}));
