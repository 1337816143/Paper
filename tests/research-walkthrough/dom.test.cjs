/* Minimal DOM simulation, NOT browser/layout/accessibility conformance proof. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'../..');
const decode=s=>s.replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&#39;/g,"'");
class Node {
 constructor(tag,attrs={},doc){this.tagName=tag.toUpperCase();this.attrs=attrs;this.ownerDocument=doc;this.children=[];this.parentNode=null;this.listeners={};this._text='';this.value=attrs.value||'';this.disabled=false;this.hidden='hidden'in attrs;this.dataset={};for(const[k,v]of Object.entries(attrs))if(k.startsWith('data-'))this.dataset[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=v;
 this.classList={toggle:(c,on)=>{const a=new Set((this.attrs.class||'').split(/\s+/));on?a.add(c):a.delete(c);this.attrs.class=[...a].join(' ')},contains:c=>(this.attrs.class||'').split(/\s+/).includes(c)};}
 get id(){return this.attrs.id||''}set id(v){this.attrs.id=v}get className(){return this.attrs.class||''}set className(v){this.attrs.class=v}
 get isConnected(){return this===this.ownerDocument?.documentElement||!!this.parentNode?.isConnected}
 append(...nodes){for(const n of nodes){n.parentNode=this;this.children.push(n)}}
 set innerHTML(html){this.children=[];this._text='';const stack=[this];const token=/<\/?[^>]+>|[^<]+/g;let m;while((m=token.exec(html))){const t=m[0];if(t.startsWith('</')){if(stack.length>1)stack.pop();continue}if(t.startsWith('<')){const match=t.match(/^<([\w-]+)([\s\S]*?)\/?\s*>$/);if(!match)continue;const attrs={};for(const a of match[2].matchAll(/([\w:-]+)(?:="([^"]*)"|='([^']*)'|=([^\s>]+))?/g))attrs[a[1]]=decode(a[2]??a[3]??a[4]??'');const n=new Node(match[1],attrs,this.ownerDocument);stack.at(-1).append(n);if(!['input','br','hr','meta','link','img','source'].includes(match[1])&&!t.endsWith('/>'))stack.push(n)}else{const n=new Node('#text',{},this.ownerDocument);n._text=decode(t);stack.at(-1).append(n)}}}
 get innerHTML(){return this.textContent}get textContent(){return this._text+this.children.map(n=>n.textContent).join('')}set textContent(v){this.children=[];this._text=String(v)}
 matches(selector){if(selector==='[contenteditable="true"]')return this.attrs.contenteditable==='true';if(selector.startsWith('#'))return this.id===selector.slice(1);if(selector.startsWith('.'))return this.classList.contains(selector.slice(1));const attr=selector.match(/^\[([^=\]]+)(?:="([^"]*)")?\]$/);if(attr)return attr[1] in this.attrs&&(attr[2]===undefined||this.attrs[attr[1]]===attr[2]);return this.tagName.toLowerCase()===selector.toLowerCase()}
 querySelectorAll(sel){const found=[];const selectors=sel.split(',');function walk(n){for(const c of n.children){if(selectors.some(s=>c.matches(s.trim())))found.push(c);walk(c)}}walk(this);return found}
 querySelector(s){return this.querySelectorAll(s)[0]||null}closest(s){return s.split(',').some(v=>this.matches(v.trim()))?this:this.parentNode?.closest(s)||null}
 contains(n){return n===this||this.children.some(c=>c.contains(n))}setAttribute(k,v){this.attrs[k]=String(v)}getAttribute(k){return this.attrs[k]??null}
 addEventListener(k,f){this.listeners[k]=f}removeEventListener(k,f){if(this.listeners[k]===f)delete this.listeners[k]}
 focus(){this.ownerDocument.activeElement=this}remove(){if(this.parentNode){this.parentNode.children=this.parentNode.children.filter(c=>c!==this);this.parentNode=null}}
}
function env(reduced=false){
 const timers=new Map(),observers=[];let tid=0;const doc={hidden:false,listeners:{},activeElement:null,createElement:tag=>new Node(tag,{},doc),addEventListener(k,f){this.listeners[k]=f},removeEventListener(k){delete this.listeners[k]}};
 doc.documentElement=new Node('html',{},doc);const container=new Node('section',{id:'host'},doc);doc.documentElement.append(container);
 const media={matches:reduced,addEventListener(k,f){this.listener=f},removeEventListener(){}};
 const win={matchMedia:()=>media,listeners:{},setTimeout:f=>{timers.set(++tid,f);return tid},clearTimeout:id=>timers.delete(id),addEventListener(k,f){this.listeners[k]=f},removeEventListener(k){delete this.listeners[k]},MutationObserver:class{constructor(f){this.f=f;observers.push(this)}observe(){}disconnect(){this.off=true}}};doc.defaultView=win;
 vm.runInNewContext(fs.readFileSync(path.join(root,'src/research-walkthrough.js'),'utf8'),{window:win,Set,WeakMap,Map,Number,Object,Array,String,Math,TypeError,RangeError,Error});
 const api=win.PaperWalkthrough,ctl=api.mount(container),panel=container.children[0];const q=s=>panel.querySelector(s);
 const click=s=>{const target=q(s);assert.ok(target,s);panel.listeners.click({target})};const input=(key,value)=>{const target=q(`[data-field="${key}"]`);assert.ok(target,key);target.value=String(value);panel.listeners.input({target})};
 return{api,ctl,panel,q,click,input,doc,win,media,container,timers,observers,tick(){const f=timers.values().next().value;assert.ok(f);timers.delete(timers.keys().next().value);f()}};
}
let passed=0;function test(name,fn){fn();passed++;console.log('PASS DOM-simulated',name)}
test('all six main render branches execute, propagate cost and show live values',()=>{
 const e=env();assert.equal(e.timers.size,0);assert.equal(e.api.isBusy(),false);e.input('costAW',600);assert.equal(e.api.isBusy(),true);
 for(let i=0;i<6;i++){e.click(`[data-step="${i}"]`);assert.equal(e.ctl.getState().step,i);assert.ok(e.q('.rw-result').textContent.length>100)}
 assert.ok(e.q('.rw-stage').textContent.includes('2,300'));e.click('[data-action="reset"]');assert.equal(e.api.isBusy(),false);
});
test('focused table and chart scrollers retain their native arrow keys',()=>{
 const e=env();for(const [stage,selector] of [[0,'.rw-table-wrap'],[4,'.rw-chart-scroll']]){
  e.click(`[data-step="${stage}"]`);const target=e.q(selector);assert.ok(target,selector);let prevented=false;
  e.panel.listeners.keydown({target,key:'ArrowRight',preventDefault(){prevented=true}});
  assert.equal(e.ctl.getState().step,stage);assert.equal(prevented,false);
 }
});
test('main default distance and all selectable farms render safely',()=>{
 const e=env();e.click('[data-step="2"]');for(const id of['A','B','C','D']){e.click(`[data-select="${id}"]`);assert.ok(e.q('.rw-stage').textContent.includes(id))}
 e.click('[data-step="5"]');e.click('[data-select="A"]');assert.ok(e.q('.rw-stage').textContent.includes('0.424264'));e.click('[data-select="C"]');assert.ok(e.q('.rw-stage').textContent.includes('0.707107'));
});
test('all seven independent metric renders and join toggles',()=>{
 const e=env();for(const name of['gm','dey','labor','gwd','nl','ghg','pu']){e.click(`[data-metric="${name}"]`);assert.ok(e.q('.rw-side-metric-result').textContent.length>300)}
 e.input('area',3);assert.ok(e.q('.rw-side-metric-result').textContent.includes('仍为6次'));e.click('[data-join="wrong"]');assert.ok(e.q('.rw-side-join-result').textContent.includes('收获 120 Mg · 粪肥 36 Mg'));e.click('[data-join="correct"]');assert.ok(e.q('.rw-side-join-result').textContent.includes('收获 60 Mg · 粪肥 12 Mg'));
});
test('invalid input feedback and recovery retain valid state',()=>{
 const e=env();e.input('costAW','');assert.equal(e.ctl.getState().values.costAW,1000);assert.equal(e.q('[data-field="costAW"]').getAttribute('aria-invalid'),'true');assert.equal(e.q('[data-action="play"]').disabled,true);e.input('costAW',1010);assert.equal(e.ctl.getState().values.costAW,1010);assert.equal(e.q('[data-action="play"]').disabled,false);e.input('costAW','');e.click('[data-action="reset"]');assert.equal(e.api.isBusy(),false);assert.equal(e.q('[data-action="play"]').disabled,false);
});
test('empty and constant-column states render without NaN',()=>{
 const e=env();e.click('[data-step="3"]');e.input('laborCap',0);e.click('[data-step="5"]');assert.ok(e.q('.rw-stage').textContent.includes('没有可行方案'));e.click('[data-step="3"]');e.input('laborCap',74);e.click('[data-step="5"]');assert.ok(e.q('.rw-stage').textContent.includes('所有值相同'));assert.ok(!/NaN|Infinity/.test(e.q('.rw-stage').textContent));
});
test('play, pause, final stop, hidden state and route cleanup',()=>{
 const e=env();e.click('[data-action="play"]');assert.equal(e.timers.size,1);e.tick();assert.equal(e.ctl.getState().step,1);e.click('[data-action="play"]');assert.equal(e.timers.size,0);e.click('[data-step="4"]');e.click('[data-action="play"]');e.tick();assert.equal(e.ctl.getState().step,5);assert.equal(e.timers.size,0);e.click('[data-action="play"]');e.doc.hidden=true;e.doc.listeners.visibilitychange();assert.equal(e.timers.size,0);e.doc.hidden=false;e.click('[data-step="0"]');e.input('costAW',1100);e.win.listeners.hashchange();assert.equal(e.api.isBusy(),false);
});
test('reduced motion, duplicate mount, detach and explicit destroy',()=>{
 const e=env(true);assert.equal(e.q('[data-action="play"]').disabled,true);assert.equal(e.api.mount(e.container),e.ctl);assert.equal(e.container.children.length,1);e.click('[data-step="5"]');assert.equal(e.ctl.getState().step,5);e.container.remove();for(const o of e.observers)if(!o.off)o.f();assert.equal(e.ctl.getState().mounted,false);assert.equal(e.api.isBusy(),false);assert.equal(e.timers.size,0);
});
test('semantic IDs, input labels and graphics descriptions present in generated DOM',()=>{
 const e=env();e.click('[data-step="5"]');const ids=e.panel.querySelectorAll('[id]').map(n=>n.id);assert.equal(new Set(ids).size,ids.length);for(const input of e.panel.querySelectorAll('input,select'))assert.ok(e.panel.querySelectorAll('label').some(l=>l.getAttribute('for')===input.id));for(const svg of e.panel.querySelectorAll('svg')){assert.ok(svg.querySelector('title'));assert.ok(svg.querySelector('desc'))}assert.equal(e.panel.querySelectorAll('.prose').length,0);
});
console.log(JSON.stringify({passed,scope:'DOM simulation only; not actual browser rendering, screen reader, mobile or pixel verification'}));
