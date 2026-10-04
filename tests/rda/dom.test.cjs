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
 contains(n){return n===this||this.children.some(c=>c.contains(n))}setAttribute(k,v){this.attrs[k]=String(v)}getAttribute(k){return this.attrs[k]??null}removeAttribute(k){delete this.attrs[k]}
 addEventListener(k,f){this.listeners[k]=f}removeEventListener(k,f){if(this.listeners[k]===f)delete this.listeners[k]}
 focus(){this.ownerDocument.activeElement=this}remove(){if(this.parentNode){this.parentNode.children=this.parentNode.children.filter(c=>c!==this);this.parentNode=null}}
}
const csv=fs.readFileSync(path.join(root,'examples/rda_synthetic_villages.csv'),'utf8').trim().split(/\r?\n/),columns=csv.shift().split(','),records=csv.map(line=>Object.fromEntries(line.split(',').map((v,i)=>[columns[i],i?Number(v):v])));
const config=JSON.parse(fs.readFileSync(path.join(root,'resources/rda-walkthrough-v555.json'),'utf8'));
function env(options={}) {
 const observers=[];const doc={activeElement:null,createElement:tag=>new Node(tag,{},doc)};doc.documentElement=new Node('html',{},doc);
 const container=new Node('div',{id:'isolated-rda'},doc);doc.documentElement.append(container);
 const win={PAPER_RDA:{...config,records:options.records || records},location:{protocol:options.protocol || 'https:'},listeners:{},addEventListener(k,f){this.listeners[k]=f},removeEventListener(k,f){if(this.listeners[k]===f)delete this.listeners[k]},MutationObserver:class{constructor(f){this.f=f;observers.push(this)}observe(){}disconnect(){this.off=true}}};doc.defaultView=win;
 for(const name of ['rda-model.js','rda-walkthrough.js'])vm.runInNewContext(fs.readFileSync(path.join(root,'src',name),'utf8'),{window:win,Set,WeakMap,Map,Number,Object,Array,String,Math,TypeError,Error});
 const api=win.PaperRDA,ctl=api.mount(container),panel=container.children[0],q=s=>panel.querySelector(s);
 const click=s=>{const target=q(s);assert.ok(target,s);panel.listeners.click({target})};
 const input=(key,value)=>{const target=q(`[data-field="${key}"]`);assert.ok(target,key);target.value=String(value);panel.listeners.input({target})};
 return{api,ctl,panel,q,click,input,doc,win,container,observers};
}
let passed=0;function test(name,fn){fn();passed++;console.log('PASS DOM-simulated',name)}
test('all six manual stages render with defaults and model-derived numbers',()=>{
 const e=env();assert.equal(e.api.isBusy(),false);assert.equal(e.ctl.getState().pendingTimer,false);
 for(let i=0;i<6;i++){e.click(`[data-step="${i}"]`);assert.equal(e.ctl.getState().step,i);assert.ok(e.q('.rda-stage').textContent.length>350)}
 e.click('[data-step="3"]');for(const value of ['1.388889','0.611111','0.833333','0.555556','41.667%','27.778%','60.000%','40.000%','30.556%'])assert.ok(e.q('.rda-stage').textContent.includes(value),value);
 assert.equal(e.api.isBusy(),true);e.click('[data-action="reset"]');assert.equal(e.api.isBusy(),false);
});
test('V4 B edit recomputes rotated eigenvectors and does not replace focused controls',()=>{
 const e=env();e.click('[data-step="3"]');const input=e.q('[data-field="v4B"]');input.focus();e.input('v4B',4.25);
 assert.equal(e.doc.activeElement,input);assert.equal(e.q('[data-field="v4B"]'),input);assert.equal(e.ctl.getState().v4B,4.25);
 for(const value of ['0.907322','0.435815'])assert.ok(e.q('.rda-stage').textContent.includes(value),value);
 assert.equal(e.api.isBusy(),true);
});
test('empty, off-step and out-of-range values visibly retain last valid model',()=>{
 const e=env();e.input('v4B',4.25);
 for(const invalid of ['',-1,5.25,3.76,'abc','Infinity']){e.input('v4B',invalid);assert.equal(e.ctl.getState().v4B,4.25);assert.equal(e.q('[data-field="v4B"]').getAttribute('aria-invalid'),'true');assert.ok(e.q('.rda-status').textContent.includes('上次有效结果'));assert.ok(e.q('.rda-status').textContent.includes('4.25'));}
 e.input('v4B',0);assert.equal(e.ctl.getState().v4B,0);assert.equal(e.ctl.getState().invalid,false);e.input('v4B',5);assert.equal(e.ctl.getState().v4B,5);
 e.input('v4B','');e.click('[data-action="reset"]');assert.equal(e.ctl.getState().invalid,false);assert.equal(e.ctl.getState().v4B,3.75);assert.equal(e.api.isBusy(),false);
});
test('author standardization fact stays distinct from missing reproduction inputs',()=>{const e=env();e.click('[data-step="1"]');assert.ok(e.q('.rda-stage').textContent.includes('Cheng 原文明确报告将 X 和 Y 标准化至均值0、方差1'));assert.ok(e.q('.rda-stage').textContent.includes('作者原始矩阵、各字段重编码细节与绘图 scaling'));});
test('each selected village updates numeric substitution and original-score reconstruction',()=>{
 const e=env();for(const id of ['V1','V2','V3','V4']){e.input('village',id);e.click('[data-step="1"]');assert.ok(e.q('.rda-stage').textContent.includes(id+' 的 A'));e.click('[data-step="2"]');assert.ok(e.q('.rda-stage').textContent.includes(id+'：把原始分数重建回来'));e.click('[data-step="4"]');e.input('view','observations');assert.ok(e.q('.rda-stage').textContent.includes(id+'（已选）'));}
});
test('denominator changes labels and fractions, never variable coordinates',()=>{
 const e=env();e.click('[data-step="4"]');const before=e.q('[data-variable="A"]').querySelector('circle').getAttribute('cx');const select=e.q('[data-field="denominator"]');select.focus();e.input('denominator','constrained');assert.equal(e.doc.activeElement,select);assert.equal(e.q('[data-variable="A"]').querySelector('circle').getAttribute('cx'),before);assert.ok(e.q('svg').textContent.includes('60.000%'));assert.ok(e.q('.rda-stage').textContent.includes('30.556%'));e.input('denominator','total');assert.ok(e.q('svg').textContent.includes('41.667%'));
});
test('variable versus village plots preserve full-raw-correlation warning',()=>{
 const e=env();e.click('[data-step="4"]');for(const value of ['0.272166','0.894427','0.816497'])assert.ok(e.q('.rda-stage').textContent.includes(value));assert.equal(e.panel.querySelectorAll('[data-variable]').length,4);assert.equal(e.panel.querySelectorAll('[data-village]').length,0);
 const select=e.q('[data-field="view"]');select.focus();e.input('view','observations');assert.equal(e.doc.activeElement,select);assert.equal(e.panel.querySelectorAll('[data-village]').length,4);assert.equal(e.panel.querySelectorAll('[data-variable]').length,0);assert.ok(e.q('.rda-stage').textContent.includes('观察标准化分数投影'));assert.ok(e.q('.rda-stage').textContent.includes('不是原文响应指标的圆点'));
});
test('zero-eigenvalue correlations stay undefined and never become plotted zeros',()=>{
 const singular=records.map(r=>({...r,perception_a:r.village_id==='V4'?3.75:r.perception_a,perception_b:r.village_id==='V4'?3.75:r.perception_a}));
 const e=env({records:singular});e.click('[data-step="4"]');assert.equal(e.panel.querySelectorAll('[data-variable]').length,0);assert.ok(e.q('.rda-stage').textContent.includes('未定义（零方差轴）'));assert.ok(e.q('.rda-stage').textContent.includes('绝不把未定义坐标当成0'));assert.ok(!/NaN|Infinity/.test(e.panel.textContent));e.input('view','observations');assert.equal(e.q('svg'),null);assert.equal(e.panel.querySelectorAll('[data-village]').length,0);assert.ok(e.q('.rda-stage').textContent.includes('二维村庄图不绘制'));assert.ok(e.q('.rda-stage').textContent.includes('未定义（零方差轴）'));
});
test('source points are indicators; original figure and field timing are preserved',()=>{
 const e=env();e.click('[data-step="5"]');assert.equal(e.q('img').getAttribute('src'),config.source.figurePath);assert.ok(e.q('.rda-stage').textContent.includes('不是35个村庄'));assert.ok(e.q('.rda-stage').textContent.includes('不是利润'));for(const v of config.variables){assert.ok(e.q('.rda-stage').textContent.includes(v.unit));assert.ok(e.q('.rda-stage').textContent.includes(v.year));}assert.ok(e.panel.querySelectorAll('a').some(a=>a.getAttribute('href')===config.source.sourcePage));
 const image=e.q('img');image.listeners.error();assert.equal(image.hidden,true);assert.equal(e.q('.rda-image-status').hidden,false);
});
test('single-file view explicitly omits image and all synthetic content still renders',()=>{
 const e=env({protocol:'file:'});e.click('[data-step="5"]');assert.equal(e.q('img'),null);assert.ok(e.q('.rda-stage').textContent.includes('原图未嵌入'));e.click('[data-step="4"]');assert.ok(e.q('svg'));assert.ok(e.q('table'));
});
test('native scrolling and form arrow keys are not intercepted',()=>{
 const e=env();for(const [i,sel] of [[0,'.rda-table-scroll'],[4,'.rda-chart-scroll'],[4,'[data-field="v4B"]']]){e.click(`[data-step="${i}"]`);let prevented=false;e.panel.listeners.keydown({target:e.q(sel),key:'ArrowRight',preventDefault(){prevented=true}});assert.equal(prevented,false);assert.equal(e.ctl.getState().step,i);}
 let prevented=false;e.panel.listeners.keydown({target:e.panel,key:'Home',preventDefault(){prevented=true}});assert.equal(prevented,true);assert.equal(e.ctl.getState().step,0);e.panel.listeners.keydown({target:e.panel,key:'ArrowRight',preventDefault(){}});assert.equal(e.ctl.getState().step,1);
});
test('duplicate mount, route change, detachment and explicit destroy release guards',()=>{
 const e=env();assert.equal(e.api.mount(e.container),e.ctl);assert.equal(e.container.children.length,1);e.input('v4B',4.25);e.win.listeners.popstate();e.win.listeners.hashchange();assert.equal(e.ctl.getState().mounted,true);assert.equal(e.api.isBusy(),true);e.win.location.hash='#/another-lesson';e.win.listeners.hashchange();assert.equal(e.ctl.getState().mounted,false);assert.equal(e.api.isBusy(),false);assert.equal(e.container.children.length,0);
 const again=e.api.mount(e.container);assert.notEqual(again,e.ctl);e.container.remove();for(const o of e.observers)if(!o.off)o.f();assert.equal(again.getState().mounted,false);assert.equal(e.api.isBusy(),false);again.destroy();
 const other=env();other.ctl.destroy();assert.equal(other.api.isBusy(),false);assert.equal(other.win.listeners.hashchange,undefined);assert.equal(other.win.listeners.popstate,undefined);
});
test('all generated controls and graphics have names without legacy annotation selectors',()=>{
 const e=env();assert.ok(e.panel.getAttribute('data-no-terms')!==null);
 for(let i=0;i<6;i++){e.click(`[data-step="${i}"]`);const ids=e.panel.querySelectorAll('[id]').map(n=>n.id);assert.equal(new Set(ids).size,ids.length);for(const input of e.panel.querySelectorAll('input,select'))assert.ok(e.panel.querySelectorAll('label').some(l=>l.getAttribute('for')===input.id));for(const svg of e.panel.querySelectorAll('svg')){assert.ok(svg.querySelector('title'));assert.ok(svg.querySelector('desc'));}for(const t of e.panel.querySelectorAll('table'))assert.ok(t.querySelector('caption'));assert.equal(e.panel.querySelectorAll('.prose,[data-block]').length,0);}
});
console.log(JSON.stringify({passed,scope:'DOM simulation only; not actual browser rendering, screen reader, mobile or pixel verification'}));
