'use strict';
// Executes the exact source function bodies against a small scheduling / DOM model.
// This model proves allowed stale continuations, not a real-browser reproduction.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
// Optional explicit source path is for isolated audit workspaces; CI uses src/reader.js.
const candidatePath=process.argv[2]?path.resolve(process.argv[2]):path.resolve(__dirname,'../src/reader.js');
const candidate=fs.readFileSync(candidatePath,'utf8');
const baselineHash='7ed6c65d96f0e766cf3e3f78a03cb95f32483f5eb05f9f52746d1a6dbd9f2783';
const guards=[
 ["async function notes(target){const ticket=epoch,ns=await all('annotations');if(ticket!==epoch)return;", "async function notes(target){const ns=await all('annotations');"],
 ["async function shelf(){const ticket=epoch,locals=await all('books');if(ticket!==epoch)return;", "async function shelf(){const locals=await all('books');"],
 ["async function paint(){const ticket=epoch,root=", "async function paint(){const root="],
 ["if(ticket!==epoch||!root.isConnected||root!==(docid?$('#original-text'):$('#view .reader')))return;", ""],
 ["let b=document.getElementById(s.block);if(b&&!root.contains(b))b=null;let a=b?resolve(s,b):null;", "let b=document.getElementById(s.block),a=b?resolve(s,b):null;"]
];
let source=candidate;
for(const [inserted,original] of guards){assert.equal(source.split(inserted).length-1,1,'each production guard must occur exactly once');source=source.replace(inserted,original);}
assert.equal(crypto.createHash('sha256').update(source).digest('hex'),baselineHash,'only the five reviewed guard edits may differ from original reader');
function body(start,end,text){const i=text.indexOf(start),j=text.indexOf(end,i);assert(i>=0&&j>i,'function extraction boundaries exist');return text.slice(i,j);}
const notes=body('async function notes(target)','function importNotes()',source),candidateNotes=body('async function notes(target)','function importNotes()',candidate);
const shelf=body('async function shelf()','function importFile(',source),candidateShelf=body('async function shelf()','function importFile(',candidate);
const paint=body('async function paint()','const href=',source),candidatePaint=body('async function paint()','const href=',candidate);
const resolve=body('function resolve(s,b)','async function paint()',source);
class Node{
 constructor(tag='',text=''){this.tagName=tag.toUpperCase();this.data=text;this.children=[];this.parentNode=null;this.dataset={};this.id='';this._connected=false;this.className='';}
 get nodeType(){return this.tagName?1:3;}
 get childNodes(){return this.children;}
 get length(){return this.data.length;}
 get isConnected(){return this._connected||!!this.parentNode?.isConnected;}
 get textContent(){return this.nodeType===3?this.data:this.children.map(x=>x.textContent).join('');}
 set textContent(s){this.children=[];this.append(new Node('',String(s)));}
 append(...nodes){for(const n of nodes){if(n.parentNode){const i=n.parentNode.children.indexOf(n);n.parentNode.children.splice(i,1);}n.parentNode=this;this.children.push(n);}}
 contains(n){return n===this||this.children.some(x=>x.contains(n));}
 replaceWith(...nodes){const parent=this.parentNode,i=parent.children.indexOf(this);parent.children.splice(i,1,...nodes);for(const n of nodes)n.parentNode=parent;this.parentNode=null;this.children=[];}
 normalize(){for(const n of [...this.children])n.normalize();for(let i=this.children.length-1;i>0;i--)if(this.children[i].nodeType===3&&this.children[i-1].nodeType===3){this.children[i-1].data+=this.children[i].data;this.children.splice(i,1);}}
 querySelectorAll(q){let values=[];for(const n of this.children){if(q==='mark[data-annotation]'&&n.tagName==='MARK'&&n.dataset.annotation)values.push(n);if(q==='[data-block]'&&n.dataset.block)values.push(n);values.push(...n.querySelectorAll(q));}return values;}
}
function rootFixture(id='method-block-1',text=['Alpha ','beta',' gamma']){const root=new Node('article'),p=new Node('p'),span=new Node('span');root._connected=true;p.id=id;p.dataset.block=id;root.append(p);p.append(new Node('',text[0]));span.append(new Node('',text[1]));p.append(span,new Node('',text[2]));return {root,p};}
function harness(patched=false){
 let current=null,route='farmdesign-2012/method-block-1',outside=null,html='';const pending=[],controls=new Map(),writes=[],terms=[];
 const view={get innerHTML(){return html;},set innerHTML(value){html=value;writes.push(value);if(current){current.root._connected=false;current=null;}controls.clear();for(const match of value.matchAll(/id="([^"]+)"/g))controls.set(match[1],{value:'',innerHTML:'',dataset:{}});}};
 const document={
  getElementById(id){if(current?.p.id===id)return current.p;if(outside?.id===id)return outside;return controls.get(id)||null;},
  createTreeWalker(root){const text=[];function walk(n){if(n.nodeType===3)text.push(n);else n.children.forEach(walk);}walk(root);let i=-1;return {currentNode:null,nextNode(){this.currentNode=text[++i];return !!this.currentNode;}};},
  createElement(tag){return new Node(tag);},
  createRange(){let a,z,lo,hi;return {setStart(n,i){a=n;lo=i;},setEnd(n,i){z=n;hi=i;},surroundContents(mark){assert.equal(a,z);const parent=a.parentNode,i=parent.children.indexOf(a),nodes=[];if(lo)nodes.push(new Node('',a.data.slice(0,lo)));mark.append(new Node('',a.data.slice(lo,hi)));nodes.push(mark);if(hi<a.data.length)nodes.push(new Node('',a.data.slice(hi)));parent.children.splice(i,1,...nodes);nodes.forEach(n=>n.parentNode=parent);a.parentNode=null;}};}
 };
 const $=q=>q==='#view'?view:q==='#view .reader'?(context.docid?null:current?.root||null):q==='#original-text'?(context.docid?current?.root||null:null):q.startsWith('#')?controls.get(q.slice(1))||null:null;
 const context=vm.createContext({epoch:10,docid:null,api:{route:()=>route,byId:new Map()},document,NodeFilter:{SHOW_TEXT:4},window:{PaperStudy:{terms:r=>terms.push(r)}},$: $,$$:(q,r)=>r?r.querySelectorAll(q):[],all:store=>new Promise(resolve=>pending.push({store,resolve})),head:(t,s)=>'<header>'+t+'</header>',E:s=>String(s??''),href:()=>'',edit(){},download(){},importNotes(){},requestAnimationFrame(){},sources:{records:[]},importFile(){},cacheBook(){},confirm(){return false;},del(){},location:{href:'https://test.invalid/#/'+route}});
 vm.runInContext(["'use strict';",resolve,patched?candidatePaint:paint,patched?candidateNotes:notes,patched?candidateShelf:shelf].join('\n'),context);
 return {context,pending,view,writes,terms,install(f=rootFixture(),bump=true){if(current)current.root._connected=false;if(bump)context.epoch++;current=f;html='FORWARD_METHOD_DOM';return f;},route(s){route=s;},outside(n){outside=n;},resolve(index,rows){pending[index].resolve(Object.freeze([...rows]));},get current(){return current;}};
}
function deepFreeze(x){Object.freeze(x);for(const value of Object.values(x))if(value&&typeof value==='object'&&!Object.isFrozen(value))deepFreeze(value);return x;}
const note=deepFreeze({id:'synthetic-note-1',docId:'lesson:farmdesign-2012',docTitle:'Synthetic only',quote:'Alpha beta gamma',type:'highlight',color:'yellow',segments:[{block:'method-block-1',start:0,end:16,quote:'Alpha beta gamma'}],comment:'',links:[],tags:[]});
const noteBefore=JSON.stringify(note);
const checks=[];
async function test(name,fn){checks.push({name,...await fn()});}
(async()=>{
 await test('notes pending across Back then Forward overwrites the newer method DOM',async()=>{
  const before=harness();before.route('annotations');const stale=before.context.notes();before.install();before.route('farmdesign-2012/method-block-1');assert(before.current?.root.isConnected);before.resolve(0,[note]);await stale;assert.match(before.view.innerHTML,/批注与便签/);assert.equal(before.current,null);
  const after=harness(true);after.route('annotations');const guarded=after.context.notes();const target=after.install();after.route('farmdesign-2012/method-block-1');after.resolve(0,[note]);await guarded;assert.equal(after.current,target);assert.equal(after.view.innerHTML,'FORWARD_METHOD_DOM');
  return {baseline:'stale notes replaced method DOM',candidate:'method DOM retained',proves:'An unfolded-target check before late notes completion cannot rule this race out'};
 });
 await test('active notes remains functional with ticket check',async()=>{
  const x=harness(true);x.route('annotations');const p=x.context.notes();x.resolve(0,[note]);await p;assert.match(x.view.innerHTML,/批注与便签/);return {candidate:'active notes rendered'};
 });
 await test('resources shelf has the same stale route overwrite class',async()=>{
  const before=harness();before.route('resources');const stale=before.context.shelf();before.install();before.route('farmdesign-2012');before.resolve(0,[]);await stale;assert.match(before.view.innerHTML,/原文书架与离线资源/);assert.equal(before.current,null);
  const after=harness(true);after.route('resources');const guarded=after.context.shelf();const target=after.install();after.route('farmdesign-2012');after.resolve(0,[]);await guarded;assert.equal(after.current,target);return {baseline:'stale shelf replaced method DOM',candidate:'method DOM retained'};
 });
 await test('old paint resolves after latest paint and duplicates marks inside the new root',async()=>{
  const result={};for(const patched of [false,true]){const x=harness(patched);x.install();const old=x.context.paint();const target=x.install();const latest=x.context.paint();x.resolve(1,[note]);await latest;const first=target.root.querySelectorAll('mark[data-annotation]');assert.equal(first.map(x=>x.textContent).join(''),note.quote);x.resolve(0,[note]);await old;const marks=target.root.querySelectorAll('mark[data-annotation]'),combined=marks.map(x=>x.textContent).join('');assert.equal(target.p.textContent,note.quote);if(patched){assert.equal(combined,note.quote);assert.equal(marks.length,3);}else{assert.equal(marks.length,6);assert.notEqual(combined,note.quote);}result[patched?'candidate':'baseline']={markCount:marks.length,combinedQuote:combined,blockText:target.p.textContent};}return result;
 });
 await test('old paint completing first also cannot mutate the replacement root',async()=>{
  const x=harness(true);const oldRoot=x.install();const old=x.context.paint();const target=x.install();const fresh=x.context.paint();x.resolve(0,[note]);await old;assert.equal(target.root.querySelectorAll('mark[data-annotation]').length,0);assert.equal(oldRoot.root.querySelectorAll('mark[data-annotation]').length,0);x.resolve(1,[note]);await fresh;assert.equal(target.root.querySelectorAll('mark[data-annotation]').map(x=>x.textContent).join(''),note.quote);return {candidate:'stale discarded before latest completion'};
 });
 await test('paint protects root replacement even without epoch increment',async()=>{
  const x=harness(true);x.install();const old=x.context.paint();const target=x.install(rootFixture(),false);x.resolve(0,[note]);await old;assert.equal(target.root.querySelectorAll('mark[data-annotation]').length,0);return {candidate:'detached root rejected'};
 });
 await test('paint rejects a different current root even when the old root is still connected',async()=>{
  const x=harness(true),oldRoot=x.install();const old=x.context.paint();const target=x.install(rootFixture(),false);oldRoot.root._connected=true;x.resolve(0,[note]);await old;assert.equal(target.root.querySelectorAll('mark[data-annotation]').length,0);assert.equal(oldRoot.root.querySelectorAll('mark[data-annotation]').length,0);return {candidate:'root identity check rejected connected old root'};
 });
 await test('paint rejects a newer navigation epoch even if the same root remains connected',async()=>{
  const x=harness(true),target=x.install();const p=x.context.paint();x.context.epoch++;x.resolve(0,[note]);await p;assert.equal(target.root.querySelectorAll('mark[data-annotation]').length,0);return {candidate:'epoch check rejected stale paint'};
 });
 await test('active original-reader paint remains functional and preserves its record',async()=>{
  const x=harness(true),target=x.install(),record=deepFreeze({...note,docId:'synthetic-original'});x.context.docid=record.docId;const before=JSON.stringify(record),p=x.context.paint();x.resolve(0,[record]);await p;assert.equal(target.root.querySelectorAll('mark[data-annotation]').map(x=>x.textContent).join(''),record.quote);assert.equal(JSON.stringify(record),before);return {candidate:'original reader painted exact quote and retained record'};
 });
 await test('active resources shelf remains functional',async()=>{
  const x=harness(true);x.route('resources');const p=x.context.shelf();x.resolve(0,[]);await p;assert.match(x.view.innerHTML,/原文书架与离线资源/);return {candidate:'active shelf rendered'};
 });
 await test('paint resolves block only inside its owned root',async()=>{
  const result={};for(const patched of [false,true]){const x=harness(patched),target=x.install(rootFixture('other-id')),foreign=rootFixture('method-block-1');x.outside(foreign.p);const p=x.context.paint();x.resolve(0,[note]);await p;const own=target.root.querySelectorAll('mark[data-annotation]'),other=foreign.root.querySelectorAll('mark[data-annotation]');assert.equal(patched?own.length:other.length,3);assert.equal(patched?other.length:own.length,0);result[patched?'candidate':'baseline']={ownedMarks:own.length,foreignMarks:other.length};}return result;
 });
 await test('current repeated paint stays idempotent with multi-node glossary markup',async()=>{
  const x=harness(true),target=x.install();for(let i=0;i<3;i++){const p=x.context.paint();x.resolve(i,[note]);await p;const marks=target.root.querySelectorAll('mark[data-annotation]');assert.equal(marks.length,3);assert.equal(marks.map(x=>x.textContent).join(''),note.quote);assert.equal(target.p.textContent,note.quote);}return {candidate:'three repaints each yield exactly three marks and original text'};
 });
 await test('all scenarios preserve the entire immutable synthetic annotation record',async()=>{assert.equal(JSON.stringify(note),noteBefore);return {candidate:'full record byte-for-byte JSON unchanged; nested record frozen'};});
 console.log(JSON.stringify({passed:true,scope:'No socket, no browser: exact source-function / deferred IndexedDB result / minimal DOM model. Does not establish actual CI interleaving.',source:{name:'original reader baseline',sha256:baselineHash},candidate:{name:'src/reader.js',sha256:crypto.createHash('sha256').update(candidate).digest('hex')},checks},null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
