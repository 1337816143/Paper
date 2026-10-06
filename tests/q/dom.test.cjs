/* DOM simulation only. This is NOT a browser, pixel, mobile or screen-reader check. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),cp=require('node:child_process');
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
 focus(){this.ownerDocument.activeElement=this}scrollIntoView(){this.scrolled=true}click(){this.clicked=true}remove(){if(this.parentNode){this.parentNode.children=this.parentNode.children.filter(c=>c!==this);this.parentNode=null}}
}

const config=JSON.parse(fs.readFileSync(path.join(root,'resources/q-walkthrough-v556.json'),'utf8'));
const python=process.env.PYTHON || 'python';
for(const scenario of config.scenarioDefinitions) {
 const result=cp.spawnSync(python,['-c','import json,sys;sys.path.insert(0,sys.argv[1]);from q_pipeline import analyze;print(json.dumps(analyze(scenario=sys.argv[2])))',path.join(root,'examples'),scenario.id],{encoding:'utf8'});
 assert.equal(result.status,0,result.stderr);scenario.result=JSON.parse(result.stdout);
}
config.scenarios=config.scenarioDefinitions;
const files=Object.fromEntries(config.downloads.map(name=>[name,fs.readFileSync(path.join(root,'examples',name),'utf8')]));
function env(options={}) {
 const observers=[],revoked=[],blobs=[],timers=new Map();let timerId=0;
 const doc={activeElement:null,createElement:tag=>new Node(tag,{},doc)};doc.documentElement=new Node('html',{},doc);
 const container=new Node('div',{id:'isolated-q'},doc);doc.documentElement.append(container);
 const win={PAPER_Q:config,PAPER_DATA:{files},location:{protocol:options.protocol||'https:',hash:'#/cheng-2025-q-walkthrough',href:'https://paper-q.invalid/#/cheng-2025-q-walkthrough'},history:{state:null,replaceState(value){this.state=value}},listeners:{},selection:null,
  addEventListener(k,f){(this.listeners[k] ||= new Set()).add(f)},removeEventListener(k,f){this.listeners[k]?.delete(f)},dispatch(k){[...(this.listeners[k]||[])].forEach(f=>f())},getSelection(){return this.selection},
  MutationObserver:class{constructor(f){this.f=f;observers.push(this)}observe(){}disconnect(){this.off=true}},
  URL:{createObjectURL(blob){blobs.push(blob);return 'blob:test-'+blobs.length},revokeObjectURL(url){revoked.push(url)}},Blob:class{constructor(parts,opts){this.parts=parts;this.opts=opts}},
  setTimeout(f){const id=++timerId;timers.set(id,()=>{timers.delete(id);f()});return id},clearTimeout(id){timers.delete(id)}};doc.defaultView=win;
 vm.runInNewContext(fs.readFileSync(path.join(root,'src/q-walkthrough.js'),'utf8'),{window:win,Set,WeakMap,Map,Number,Object,Array,String,Math,TypeError,Error});
 const api=win.PaperQWalkthrough,ctl=api.mount(container),panel=container.children[0],q=s=>panel.querySelector(s);
 const click=s=>{const target=q(s);assert.ok(target,s);panel.listeners.click({target})};
 const input=(key,value,type='input')=>{const target=q(`[data-field="${key}"]`);assert.ok(target,key);target.value=String(value);panel.listeners[type]({target})};
 return{api,ctl,panel,q,click,input,doc,win,container,observers,revoked,blobs,timers};
}
let passed=0;function test(name,fn){fn();passed++;console.log('PASS DOM-simulated',name)}
const F=(v,n=6)=>(Math.abs(v)<.5*10**-n?0:v).toFixed(n);
test('official SI positive common scaling follows both current scenarios and factors without mutating fixtures',()=>{
 const e=env();const before=JSON.stringify(config.scenarios);
 for(const scenario of config.scenarios){e.input('scenario',scenario.id);for(const f of [0,1]){e.input('factor',f);e.input('person','P03');e.input('statement','S12');e.click('[data-step="4"]');const r=scenario.result,c=10/Math.max(...r.weights.map(row=>row[f])),text=e.q('.q-si-weight').textContent;for(const v of [c,c*r.weights[2][f],c*r.weighted_totals[11][f],r.statement_z[11][f]])assert.ok(text.includes(F(v)));assert.ok(text.includes('SI仅写SD'));}}
 assert.equal(JSON.stringify(config.scenarios),before);
});
test('official category formula and source conflict are visible separately from synthetic controls',()=>{
 const e=env();e.click('[data-step="7"]');const text=e.q('.q-stage').textContent;
 for(const term of ['13/7–29/7','43.75','33.33','72个','恰好50不算','Company_2','327份原始排序'])assert.ok(text.includes(term),term);
 assert.ok(e.panel.querySelectorAll('a').some(a=>a.getAttribute('href')===config.source.supplement.url+'#page=14'));
});
test('all 18 published viewpoints recalculate 72 cells and keep selection focus',()=>{
 const e=env();e.click('[data-step="7"]');const select=e.q('[data-field="sourcePerspective"]');select.focus();
 for(const row of config.source.publishedTables.rows){e.input('sourcePerspective',row.perspective);assert.equal(e.doc.activeElement,select);assert.equal(e.q('[data-field="sourcePerspective"]'),select);const text=e.q('.q-stage').textContent;assert.ok(text.includes(row.perspective));const current=e.q('.q-si-current').querySelector('tbody').children;assert.equal(current.length,4);let offset=0;for(let k=0;k<4;k++){const c=config.source.categoryExample.categories[k],scores=row.factorScores.slice(offset,offset+c.count);offset+=c.count;const scaled=100*(scores.reduce((a,b)=>a+b,0)-c.minimumSum)/(c.maximumSum-c.minimumSum);assert.equal(current[k].children[1].textContent,scores.join(', '));assert.equal(current[k].children[6].textContent,F(scaled,2)+' / '+F(row.reportedCategoryScores[k],2));assert.equal(current[k].children[7].textContent,scaled>50?'优先':'不超过50');assert.ok(Math.abs(Number(e.q('[data-category="'+k+'"]').querySelector('rect').getAttribute('width'))-scaled*4)<1e-9);}assert.equal(e.panel.querySelectorAll('[data-category]').length,4);}
 assert.ok(e.q('.q-si-all-published').textContent.includes('11、9、4、7'));e.input('sourcePerspective','Company_2');assert.ok(e.q('.q-stage').textContent.includes('不超过50'));e.ctl.reset();assert.equal(e.ctl.getState().sourcePerspective,'Farmer_1');
});
test('both complete current-companion scenarios render all eight stages',()=>{
 const e=env();assert.equal(e.api.isBusy(),false);assert.equal(e.ctl.getState().person,'P01');assert.equal(e.ctl.getState().statement,'S01');
 for(const scenario of config.scenarios){e.input('scenario',scenario.id);for(let i=0;i<8;i++){e.click(`[data-step="${i}"]`);assert.equal(e.ctl.getState().step,i);assert.ok(e.q('.q-stage').textContent.length>400);assert.ok(!/NaN|Infinity/.test(e.q('.q-stage').textContent));}}
 assert.equal(e.ctl.getState().pendingTimer,false);
});
test('P07/S18 selected cell, product, eigenvector, flag and contribution truly follow selection',()=>{
 const e=env(),r=config.scenarios[0].result,p=6,s=17,f=1,o=3;
 e.input('person','P07');e.input('other','P04');e.input('statement','S18');e.input('factor',1);
 assert.ok(e.q('.q-stage').textContent.includes('D[S18, P07] = '+r.data[s][p]));assert.ok(e.q('.q-selected-cell').textContent.includes(String(r.data[s][p])));
 e.click('[data-step="1"]');assert.ok(e.q('.q-stage').textContent.includes('corr(P07, P04)'));assert.ok(e.q('.q-stage').textContent.includes(F(r.person_correlation[p][o])));assert.equal(e.q('[data-correlation="6-3"]').querySelector('rect').getAttribute('stroke-width'),'4');
 e.click('[data-step="2"]');assert.ok(e.q('.q-stage').textContent.includes(F(r.retained_eigenvectors[p][f])));assert.ok(e.q('.q-stage').textContent.includes(F(r.unrotated_loadings[p][f])));assert.ok(e.q('[data-person="P07"]').textContent.includes('（选）'));
 e.click('[data-step="3"]');assert.ok(e.q('.q-stage').textContent.includes('P07 对 F2'));assert.ok(e.q('.q-stage').textContent.includes(F(r.rotated_loadings[p][f])));
 e.click('[data-step="4"]');assert.ok(e.q('.q-stage').textContent.includes('P07 对 F2'));assert.ok(e.q('.q-stage').textContent.includes(F(r.weights[p][f]*r.data[s][p])));assert.equal(e.q('[data-contribution="P07"]').querySelector('rect').getAttribute('stroke-width'),'3');
 e.click('[data-step="5"]');assert.ok(e.q('.q-stage').textContent.includes(F(r.statement_z[s][f])));assert.ok(e.q('.q-stage').textContent.includes('S18：z='));
 e.click('[data-step="6"]');assert.ok(e.q('.q-stage').textContent.includes('S18：两份网格分数='));assert.ok(e.q('[data-difference="S18"]').textContent.includes('*'));
});
test('selectors retain DOM identity and focus, only relevant controls are shown',()=>{
 const e=env(),select=e.q('[data-field="person"]');select.focus();e.input('person','P10');assert.equal(e.doc.activeElement,select);assert.equal(e.q('[data-field="person"]'),select);assert.equal(e.api.isBusy(),true);
 e.click('[data-step="5"]');assert.equal(e.q('[data-control="person"]').hidden,true);assert.equal(e.q('[data-control="other"]').hidden,true);assert.equal(e.q('[data-control="statement"]').hidden,false);
 e.click('[data-step="6"]');assert.equal(e.q('[data-control="factor"]').hidden,true);e.click('[data-step="7"]');for(const c of e.panel.querySelectorAll('[data-control]'))assert.equal(c.hidden,c.getAttribute('data-control')!=='sourcePerspective');
});
test('navigation announces and scrolls the new heading after long tables; form edits keep focus',()=>{
 const e=env();e.click('[data-action="next"]');assert.equal(e.doc.activeElement,e.q('h3'));assert.equal(e.q('h3').scrolled,true);
 const input=e.q('[data-field="statement"]');input.focus();e.input('statement','S12');assert.equal(e.doc.activeElement,input);assert.notEqual(e.q('h3').scrolled,true);
});
test('retained information and reconstruction distinguish full correlation from two axes',()=>{
 const e=env();e.click('[data-step="2"]');const text=e.q('.q-stage').textContent;for(const value of ['63.029929%','−1','1.267696'])if(value!=='−1')assert.ok(text.includes(value),value);
 assert.ok(text.includes('原始相关 = -0.458333'));assert.ok(text.includes('旋转前 -0.479628'));assert.ok(text.includes('固定 varimax 后 -0.479628'));assert.ok(text.includes('未恢复省略轴的信息'));
});
test('geometry preview rotates retained points but cannot alter downstream numbers',()=>{
 const e=env();e.click('[data-step="2"]');e.input('loadingView','geometry');const field=e.q('[data-field="angle"]');field.focus();const before=e.q('[data-person="P01"]').querySelector('circle').getAttribute('cx');e.input('angle',45);const after=e.q('[data-person="P01"]').querySelector('circle').getAttribute('cx');assert.notEqual(after,before);assert.equal(e.doc.activeElement,field);assert.ok(e.q('.q-stage').textContent.includes('GEOMETRY PREVIEW'));assert.ok(e.q('.q-stage').textContent.includes('当前显示 -0.479628'));
 e.click('[data-step="4"]');const fixed=e.q('.q-stage').textContent;e.click('[data-step="2"]');e.input('angle',-93);e.click('[data-step="4"]');assert.equal(e.q('.q-stage').textContent,fixed);
});
function loadingLayout(e,r,view,angle=0) {
 // These are conservative model envelopes, NOT measured browser text bounds.
 // Actual SVG getBBox/font and pixel checks belong to browser_test.py.
 const labels=e.panel.querySelectorAll('.q-point-label'),markers=e.panel.querySelectorAll('[data-point-marker]');
 assert.equal(labels.length,10);assert.equal(markers.length,10);
 assert.deepEqual(labels.map(n=>n.getAttribute('data-person-label')).sort(),[...r.participants].sort());
 assert.deepEqual(markers.map(n=>n.getAttribute('data-point-marker')).sort(),[...r.participants].sort());
 const boxes=labels.map(n=>({id:n.getAttribute('data-person-label'),x:Number(n.getAttribute('x'))-3,y:Number(n.getAttribute('y'))-14,width:6+[...n.textContent].reduce((v,c)=>v+(c.charCodeAt(0)>255?13:8),0),height:20}));
 const overlap=(a,b,gap=0)=>a.x<b.x+b.width+gap && a.x+a.width+gap>b.x && a.y<b.y+b.height+gap && a.y+a.height+gap>b.y;
 const state=e.ctl.getState(),rad=angle*Math.PI/180;
 const points=(view==='varimax'?r.rotated_loadings:r.unrotated_loadings).map(([a,b])=>view==='geometry'?[a*Math.cos(rad)-b*Math.sin(rad),a*Math.sin(rad)+b*Math.cos(rad)]:[a,b]);
 const centers=markers.map(n=>{
  let cx,cy;
  if(n.tagName==='CIRCLE'){cx=Number(n.getAttribute('cx'));cy=Number(n.getAttribute('cy'));}
  else if(n.tagName==='RECT'){cx=Number(n.getAttribute('x'))+Number(n.getAttribute('width'))/2;cy=Number(n.getAttribute('y'))+Number(n.getAttribute('height'))/2;}
  else {const match=n.getAttribute('d').match(/^M([\d.e+-]+),([\d.e+-]+)/);assert.ok(match);cx=Number(match[1]);cy=Number(match[2])+7;}
  const id=n.getAttribute('data-point-marker'),i=r.participants.indexOf(id),expected=points[i];
  assert.ok(Math.abs(cx-(62+(expected[0]+1.1)/2.2*410))<1e-9,id+' actual marker x');
  assert.ok(Math.abs(cy-(442-(expected[1]+1.1)/2.2*410))<1e-9,id+' actual marker y');
  const radius=id===state.person||id===state.other?13:8;
  return{id,cx,cy,radius,x:cx-radius-3,y:cy-radius-3,width:2*(radius+3),height:2*(radius+3)};
 });
 for(const [i,box]of boxes.entries()){
  assert.ok([box.x,box.y,box.width,box.height].every(Number.isFinite),box.id+' finite envelope');
  assert.ok(box.x>=64 && box.y>=34 && box.x+box.width<=470 && box.y+box.height<=440,box.id+' inside plot');
  for(const other of boxes.slice(i+1))assert.equal(overlap(box,other,3.99),false,box.id+'/'+other.id+' label envelopes');
  for(const marker of centers)assert.equal(overlap(box,marker),false,box.id+'/'+marker.id+' marker clearance');
 }
 const leaderLayer=e.q('.q-point-leaders'),groups=e.panel.querySelectorAll('.q-point');
 assert.ok(groups.every(n=>n.parentNode===leaderLayer.parentNode && n.parentNode.children.indexOf(n)>n.parentNode.children.indexOf(leaderLayer)),'all leaders paint behind all points/text');
 assert.equal(leaderLayer.children.length,10);
 for(const leader of leaderLayer.children){
  const id=leader.getAttribute('data-person-leader'),marker=centers.find(m=>m.id===id),box=boxes.find(b=>b.id===id);
  const [x1,y1,x2,y2]=['x1','y1','x2','y2'].map(k=>Number(leader.getAttribute(k)));
  assert.ok([x1,y1,x2,y2].every(Number.isFinite));
  assert.ok(Math.abs(Math.hypot(x1-marker.cx,y1-marker.cy)-marker.radius)<1e-9,id+' leader starts outside marker');
  assert.ok(x2>=box.x && x2<=box.x+box.width && y2>=box.y && y2<=box.y+box.height,id+' leader ends at label');
  assert.ok(Math.hypot(x2-x1,y2-y1)<=85,id+' short leader');
 }
 for(const label of labels){const id=label.getAttribute('data-person-label');assert.equal(label.textContent,id+(id===state.person?'（选）':id===state.other?'（比较）':''));}
 return labels.map(n=>[n.getAttribute('data-person-label'),n.getAttribute('x'),n.getAttribute('y'),n.textContent]);
}
test('loading label envelopes avoid each other and every fixed marker across views and selections',()=>{
 const e=env(),before=JSON.stringify(config.scenarios);e.click('[data-step="2"]');
 for(const scenario of config.scenarios){
  e.input('scenario',scenario.id);
  for(const [person,other]of [['P01','P05'],['P07','P04'],['P10','P03'],['P03','P03']]){
   e.input('person',person);e.input('other',other);
   for(const view of ['varimax','unrotated','geometry']){
    e.input('loadingView',view);
    for(const angle of view==='geometry'?[-180,-135,-93,-90,-45,-1,0,1,37,45,90,93,135,179,180]:[0]){
     if(view==='geometry')e.input('angle',angle);
     loadingLayout(e,scenario.result,view,angle);
    }
   }
  }
 }
 assert.equal(JSON.stringify(config.scenarios),before,'label placement cannot mutate any statistical result');
});
test('loading placement is deterministic after control changes and history restoration',()=>{
 const e=env(),r=config.scenarios[0].result;e.click('[data-step="2"]');
 const original=loadingLayout(e,r,'varimax');
 e.input('loadingView','geometry');e.input('angle',37);e.input('person','P07');e.input('other','P04');
 e.input('loadingView','varimax');e.input('person','P01');e.input('other','P05');
 assert.deepEqual(loadingLayout(e,r,'varimax'),original);
 const saved={...e.win.history.state};e.win.history.state={};e.win.location.hash='#/cheng-2025';e.win.dispatch('popstate');
 e.win.history.state=saved;e.win.location.hash='#/cheng-2025-q-walkthrough';e.api.mount(e.container);e.win.dispatch('hashchange');
 const labels=e.container.querySelectorAll('.q-point-label').map(n=>[n.getAttribute('data-person-label'),n.getAttribute('x'),n.getAttribute('y'),n.textContent]);
 assert.deepEqual(labels,original);
});
test('invalid geometry preserves last valid angle, including recovery to the same angle',()=>{
 const e=env();e.click('[data-step="2"]');e.input('loadingView','geometry');e.input('angle',45);
 for(const invalid of ['',181,-181,'abc',1.5,'Infinity']){e.input('angle',invalid);assert.equal(e.ctl.getState().angle,45);assert.equal(e.ctl.getState().invalid,true);assert.equal(e.q('[data-field="angle"]').getAttribute('aria-invalid'),'true');}
 e.input('angle',45);assert.equal(e.ctl.getState().invalid,false);assert.equal(e.q('.q-error').hidden,true);assert.equal(e.q('[data-field="angle"]').getAttribute('aria-invalid'),'false');
});
test('strict flag examples, P10 and coherent negative P03 remain distinct',()=>{
 const e=env();e.click('[data-step="3"]');for(const term of ['(.60, .50)','(.50, .50)','(.65, .55, .50)','不是把当前主分析变为三因子','−2.222222'])assert.ok(e.q('.q-stage').textContent.includes(term),term);
 e.click('[data-person-select="P10"]');assert.equal(e.ctl.getState().person,'P10');assert.ok(e.q('.q-stage').textContent.includes('否，不标记在该因子'));
 e.click('[data-scenario-select="reverse-p03"]');assert.equal(e.ctl.getState().scenario,'reverse-p03');assert.equal(e.ctl.getState().person,'P03');assert.ok(e.q('.q-stage').textContent.includes('是，标记为定义排序'));
 const r=config.scenarios[1].result;e.click('[data-step="4"]');assert.ok(r.weights[2][0]<0);assert.ok(e.q('.q-stage').textContent.includes(F(r.weights[2][0])));assert.ok(e.q('.q-stage').textContent.includes('w′x′=wx−6w'));assert.deepEqual(config.scenarios[0].result.factor_arrays,r.factor_arrays);
});
test('weighted-average equivalence and rank mapping use current statement/factor numbers',()=>{
 const e=env(),r=config.scenarios[0].result; e.click('[data-step="4"]');for(const term of ['16.050','4.624','1.003','41.66%','不是农场优化目标权重'])assert.ok(e.q('.q-stage').textContent.includes(term),term);
 e.input('statement','S03');e.input('factor',1);assert.ok(e.q('.q-stage').textContent.includes(F(r.statement_z[2][1])));e.click('[data-step="5"]');assert.ok(e.q('.q-stage').textContent.includes('不是把 z 四舍五入'));assert.ok(e.q('.q-stage').textContent.includes('20−1'));assert.ok(e.q('.q-stage').textContent.includes('平均名次2.5'));
});
test('S04 and S12 shortcuts show the correct two significance outcomes',()=>{
 const e=env();e.click('[data-step="6"]');e.click('[data-statement="S04"]');assert.equal(e.ctl.getState().statement,'S04');assert.ok(e.q('.q-stage').textContent.includes('S04：两份网格分数=3 / 4'));assert.ok(e.q('.q-stage').textContent.includes('→ p<.05 未检出差异'));
 e.click('[data-statement="S12"]');assert.ok(e.q('.q-stage').textContent.includes('→ p<.05 可区分'));assert.ok(e.q('.q-stage').textContent.includes('p<.01 未检出差异'));assert.ok(e.q('.q-stage').textContent.includes('这是软件假设，不是本数据实测'));
});
test('source originals, published Table5 means and missing scaling are clearly separated',()=>{
 const e=env();e.click('[data-step="7"]');assert.equal(e.panel.querySelectorAll('img').length,3);config.source.figures.forEach((figure,i)=>assert.equal(e.q(`[data-source-image="${i}"]`).getAttribute('src'),figure.path));
 for(const term of ['2.857143','2.500000','精确缩放公式已确认','Ungrouped','不是因果证明','不是原始农户记录'])if(term!=='不是原始农户记录')assert.ok(e.q('.q-stage').textContent.includes(term),term);
 const img=e.q('[data-source-image="1"]');img.listeners.error();assert.equal(img.hidden,true);assert.equal(e.q('[data-image-status="1"]').hidden,false);
 const f=env({protocol:'file:'});f.click('[data-step="7"]');assert.equal(f.panel.querySelectorAll('img').length,0);assert.ok(f.q('.q-stage').textContent.includes('原图未嵌入'));f.click('[data-step="1"]');assert.ok(f.q('svg'));
});
test('native scrolling and form keys remain native, panel-only arrow navigation works',()=>{
 const e=env();e.click('[data-step="1"]');for(const selector of ['.q-table-scroll','.q-chart-scroll','[data-field="person"]']){let blocked=false;e.panel.listeners.keydown({target:e.q(selector),key:'ArrowRight',preventDefault(){blocked=true}});assert.equal(blocked,false);assert.equal(e.ctl.getState().step,1);}
 let blocked=false;e.panel.listeners.keydown({target:e.panel,key:'End',preventDefault(){blocked=true}});assert.equal(blocked,true);assert.equal(e.ctl.getState().step,7);
});
test('release guards cover focused controls, text selection and nondefault choices',()=>{
 const e=env();e.q('[data-field="person"]').focus();assert.equal(e.api.isBusy(),true);e.panel.focus();assert.equal(e.api.isBusy(),false);e.win.selection={isCollapsed:false,anchorNode:e.q('h2')};assert.equal(e.api.isBusy(),true);e.win.selection=null;e.input('person','P10');assert.equal(e.api.isBusy(),true);e.ctl.reset();e.panel.focus();assert.equal(e.api.isBusy(),false);
});
test('same-route popstate/hashchange preserves newly mounted panel; route leave and detach clean up',()=>{
 const e=env();assert.equal(e.api.mount(e.container),e.ctl);e.input('person','P10');e.win.dispatch('popstate');e.win.dispatch('hashchange');assert.equal(e.ctl.getState().mounted,true);
 e.win.location.hash='#/cheng-2025';e.win.dispatch('popstate');e.win.dispatch('hashchange');assert.equal(e.ctl.getState().mounted,false);assert.equal(e.api.isBusy(),false);
 e.win.location.hash='#/cheng-2025-q-walkthrough';const fresh=e.api.mount(e.container);e.win.dispatch('hashchange');assert.equal(fresh.getState().mounted,true);e.container.remove();e.observers.filter(o=>!o.off).forEach(o=>o.f());assert.equal(fresh.getState().mounted,false);assert.equal(e.api.isBusy(),false);
});
test('history entries restore choices and expanded explanations without storing them in history',()=>{
 const e=env();e.input('person','P07');e.input('statement','S18');e.click('[data-step="7"]');
 const detail=e.q('.q-stage').querySelector('details');detail.open=true;e.panel.listeners.toggle();
 const saved={...e.win.history.state};assert.deepEqual(Object.keys(saved),['paperQEntry']);
 e.win.history.state={};e.win.location.hash='#/original/cheng-2025';e.win.dispatch('popstate');
 assert.equal(e.api.isBusy(),false);
 e.win.history.state=saved;e.win.location.hash='#/cheng-2025-q-walkthrough';
 const returned=e.api.mount(e.container);e.win.dispatch('hashchange');
 assert.equal(returned.getState().step,7);assert.equal(returned.getState().person,'P07');assert.equal(returned.getState().statement,'S18');
 assert.equal(e.container.querySelector('.q-stage').querySelector('details').open,true);
 returned.destroy();e.win.history.state={pl:true,y:0};const separate=e.api.mount(e.container);
 assert.equal(separate.getState().step,0);assert.equal(separate.getState().person,'P01');
});
test('negative weight substitution squares a parenthesized signed loading',()=>{
 const e=env();e.input('scenario','reverse-p03');e.input('person','P03');e.click('[data-step="4"]');
 assert.ok(e.q('.q-equation').textContent.includes('1 − (-0.845881)²'));
});
test('downloads use only checked packaged text and revoke Blob URLs on completion/destroy',()=>{
 const e=env(),name=config.downloads[0];e.click(`[data-q-download="${name}"]`);assert.equal(e.blobs.length,1);assert.equal(e.blobs[0].parts[0],files[name]);assert.equal(e.ctl.getState().lastDownload,name);assert.equal(e.ctl.getState().pendingTimer,true);
 for(const fn of [...e.timers.values()])fn();assert.equal(e.ctl.getState().pendingTimer,false);assert.equal(e.revoked.length,1);e.click(`[data-q-download="${name}"]`);e.ctl.destroy();assert.equal(e.revoked.length,2);assert.equal(e.timers.size,0);assert.equal(e.win.listeners.popstate.size,0);assert.equal(e.win.listeners.hashchange.size,0);
});
test('all controls, SVGs, tables and scroll regions are named; no legacy annotation selectors',()=>{
 const e=env();for(let step=0;step<8;step++){e.click(`[data-step="${step}"]`);const ids=e.panel.querySelectorAll('[id]').map(n=>n.id);assert.equal(new Set(ids).size,ids.length);for(const input of e.panel.querySelectorAll('input,select'))assert.ok(e.panel.querySelectorAll('label').some(l=>l.getAttribute('for')===input.id));for(const svg of e.panel.querySelectorAll('svg')){assert.ok(svg.querySelector('title'));assert.ok(svg.querySelector('desc'));}for(const table of e.panel.querySelectorAll('table'))assert.ok(table.querySelector('caption'));for(const region of e.panel.querySelectorAll('[role="region"]'))assert.ok(region.getAttribute('aria-label'));assert.equal(e.panel.querySelectorAll('.prose,[data-block]').length,0);}
});
console.log(JSON.stringify({passed,scope:'DOM simulation only; actual browser and layout verification are separate'}));
