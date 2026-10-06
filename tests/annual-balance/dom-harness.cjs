/* Deliberately minimal DOM simulation. NOT Chromium or layout/accessibility proof. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'../..');
const decode=s=>s.replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&#39;/g,"'");
class Node {
 constructor(tag,attrs={},doc){this.tagName=tag.toUpperCase();this.attrs=attrs;this.ownerDocument=doc;this.children=[];this.parentNode=null;this.listeners={};this._text='';this.value=attrs.value||'';this.checked=false;this.open='open'in attrs;this.disabled=false;this.hidden='hidden'in attrs;this.dataset={};for(const[k,v]of Object.entries(attrs))if(k.startsWith('data-'))this.dataset[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=v;
 this.classList={toggle:(c,on)=>{const a=new Set((this.attrs.class||'').split(/\s+/));on?a.add(c):a.delete(c);this.attrs.class=[...a].join(' ')},contains:c=>(this.attrs.class||'').split(/\s+/).includes(c)};}
 get id(){return this.attrs.id||''}set id(v){this.attrs.id=v}get className(){return this.attrs.class||''}set className(v){this.attrs.class=v}
 get isConnected(){return this===this.ownerDocument?.documentElement||!!this.parentNode?.isConnected}
 append(...nodes){for(const n of nodes){n.parentNode=this;this.children.push(n)}}
 set innerHTML(html){this.html=html;for(const c of this.children)c.parentNode=null;this.children=[];this._text='';const stack=[this];const token=/<\/?[^>]+>|[^<]+/g;let m;while((m=token.exec(html))){const t=m[0];if(t.startsWith('</')){if(stack.length>1)stack.pop();continue}if(t.startsWith('<')){const match=t.match(/^<([\w-]+)([\s\S]*?)\/?\s*>$/);if(!match)continue;const attrs={};for(const a of match[2].matchAll(/([\w:-]+)(?:="([^"]*)"|='([^']*)'|=([^\s>]+))?/g))attrs[a[1]]=decode(a[2]??a[3]??a[4]??'');const n=new Node(match[1],attrs,this.ownerDocument);stack.at(-1).append(n);if(!['input','br','hr','meta','link','img','source'].includes(match[1])&&!t.endsWith('/>'))stack.push(n)}else{const n=new Node('#text',{},this.ownerDocument);n._text=decode(t);stack.at(-1).append(n)}}}
 get innerHTML(){return this.html||this.textContent}get textContent(){return this._text+this.children.map(n=>n.textContent).join('')}set textContent(v){for(const c of this.children)c.parentNode=null;this.children=[];this._text=String(v)}
 matches(selector){if(selector.startsWith('#'))return this.id===selector.slice(1);if(selector.startsWith('.'))return this.classList.contains(selector.slice(1));const attr=selector.match(/^\[([^=\]]+)(?:="([^"]*)")?\]$/);if(attr)return attr[1]in this.attrs&&(attr[2]===undefined||this.attrs[attr[1]]===attr[2]);return this.tagName.toLowerCase()===selector.toLowerCase()}
 querySelectorAll(sel){const found=[],selectors=sel.split(',');function walk(n){for(const c of n.children){if(selectors.some(s=>c.matches(s.trim())))found.push(c);walk(c)}}walk(this);return found}
 querySelector(s){return this.querySelectorAll(s)[0]||null}closest(s){return s.split(',').some(v=>this.matches(v.trim()))?this:this.parentNode?.closest(s)||null}
 contains(n){return n===this||this.children.some(c=>c.contains(n))}setAttribute(k,v){this.attrs[k]=String(v)}getAttribute(k){return this.attrs[k]??null}removeAttribute(k){delete this.attrs[k]}
 addEventListener(k,f){this.listeners[k]=f}removeEventListener(k,f){if(this.listeners[k]===f)delete this.listeners[k]}
 focus(){this.ownerDocument.activeElement=this}scrollIntoView(){this.scrolled=true}click(){this.clicked=true}remove(){if(this.parentNode){this.parentNode.children=this.parentNode.children.filter(c=>c!==this);this.parentNode=null}}
}
function env(options={}) {
 const observers=[],revoked=[],blobs=[],timers=new Map();let timerId=0;
 const doc={activeElement:null,createElement:tag=>new Node(tag,{},doc)};doc.documentElement=new Node('html',{},doc);
 const container=new Node('div',{id:'isolated-annual'},doc);doc.documentElement.append(container);
 const win={location:{protocol:options.protocol||'https:',hash:'#/farmdesign-2012-balance-walkthrough/annual-balance',href:'https://paper-annual.invalid/#/farmdesign-2012-balance-walkthrough/annual-balance'},history:{state:null,replaceState(value){this.state=value}},listeners:{},selection:null,
  addEventListener(k,f){(this.listeners[k] ||=new Set()).add(f)},removeEventListener(k,f){this.listeners[k]?.delete(f)},dispatch(k){[...(this.listeners[k]||[])].forEach(f=>f())},getSelection(){return this.selection},
  MutationObserver:class{constructor(f){this.f=f;observers.push(this)}observe(){}disconnect(){this.off=true}},
  URL:{createObjectURL(blob){blobs.push(blob);return 'blob:test-'+blobs.length},revokeObjectURL(url){revoked.push(url)}},Blob:class{constructor(parts,opts){this.parts=parts;this.opts=opts}},
  setTimeout(f){const id=++timerId;timers.set(id,()=>{timers.delete(id);f()});return id},clearTimeout(id){timers.delete(id)}};doc.defaultView=win;
 for(const file of ['annual-balance-model.js','annual-balance-walkthrough.js'])vm.runInNewContext(fs.readFileSync(path.join(root,'src',file),'utf8'),{window:win,Set,WeakMap,Map,Number,Object,Array,String,Math,JSON,TypeError,RangeError,Error});
 const api=win.PaperAnnualBalance,ctl=api.mount(container),panel=container.children[0],q=s=>panel.querySelector(s);
 const click=s=>{const target=q(s);if(!target)throw new Error(s);panel.listeners.click({target})};
 const input=(key,value)=>{const target=q(`[data-annual-field="${key}"]`);if(!target)throw new Error(key);if(key==='replaceRetained')target.checked=value;else target.value=String(value);panel.listeners.input({target})};
 return{api,ctl,panel,q,click,input,doc,win,container,observers,revoked,blobs,timers};
}
module.exports={env,Node,root};
