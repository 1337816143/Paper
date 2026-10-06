'use strict';
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {Node}=require('../annual-balance/dom-harness.cjs');
const root=path.resolve(__dirname,'../..');
const doc={activeElement:null,createElement:tag=>new Node(tag,{},doc)};doc.documentElement=new Node('html',{},doc);
let host=doc.createElement('div');doc.documentElement.append(host);
const observers=[],revoked=[],blobs=[],timers=new Map();let timer=0;
const win={location:{hash:'#/dong-si-boundary-walkthrough',href:'https://paper.invalid/#/dong-si-boundary-walkthrough'},history:{state:null,replaceState(s){this.state=s}},listeners:{},
 addEventListener(k,f){(this.listeners[k] ||=new Set()).add(f)},removeEventListener(k,f){this.listeners[k]?.delete(f)},getSelection(){return this.selection},
 MutationObserver:class{constructor(f){observers.push(this);this.f=f}observe(){}disconnect(){this.off=true}},
 URL:{createObjectURL(b){blobs.push(b);return 'blob:test-'+blobs.length},revokeObjectURL(u){revoked.push(u)}},
 setTimeout(f){timers.set(++timer,f);return timer},clearTimeout(i){timers.delete(i)},PAPER_DATA:{files:{'dong_boundary_lab.py':'synthetic code sentinel'}}};
for(const name of ['dong-boundary-model.js','dong-boundary.js'])vm.runInNewContext(fs.readFileSync(path.join(root,'src',name),'utf8'),{window:win,Blob,Date,Set,Map,WeakMap,Number,Object,Array,String,Math,JSON,Error});
let ctl=win.PaperDong.mount(host),panel=host.children[0];const q=s=>panel.querySelector(s);
const input=(key,val)=>{const e=q(`[data-dong-field="${key}"]`);e.value=String(val);panel.listeners.input({target:e})};
const click=s=>panel.listeners.click({target:q(s)});
assert.equal(ctl.result,undefined);assert.equal(ctl.getState().result.upper.managed_input,100);assert.equal(win.PaperDong.mount(host),ctl);assert.equal(host.children.length,1);
const field=q('[data-dong-field="target"]');input('target',55);assert.equal(ctl.getState().result.interval.nonempty,false);assert.equal(q('[data-dong-field="target"]'),field);assert.equal(win.PaperDong.isBusy(),true);
input('target','');assert.match(ctl.getState().invalid,/收获/);assert.equal(ctl.getState().result.target,55);assert.equal(q('[data-dong-download="result"]').disabled,true);
const saved=win.history.state;host.remove();observers.at(-1).f();assert.equal(ctl.getState().mounted,false);assert.equal(win.PaperDong.isBusy(),false);
host=doc.createElement('div');doc.documentElement.append(host);ctl=win.PaperDong.mount(host);panel=host.children[0];assert.equal(win.history.state.paperDongEntry,saved.paperDongEntry);assert.match(ctl.getState().invalid,/收获/);assert.equal(ctl.getState().result.target,55);assert.equal(q('[data-dong-download="result"]').disabled,true);
input('target',50);input('extra',123);assert.equal(ctl.getState().result.ledger.residual,123);click('[data-dong-download="result"]');assert.equal(blobs.length,1);assert.equal(timers.size,1);assert.equal(win.PaperDong.isBusy(),true);
click('[data-dong-action="reset"]');assert.equal(win.PaperDong.isBusy(),true);assert.equal(ctl.getState().result.ledger.residual,0);timers.get(1)();assert.equal(revoked.length,1);assert.equal(win.PaperDong.isBusy(),false);
ctl.destroy();assert.equal(host.children.length,0);assert.equal(win.PaperDong.isBusy(),false);assert.equal([...Object.values(win.listeners)].every(s=>s.size===0),true);
console.log('PASS Dong synthetic DOM identity, invalid history, real-output export lifecycle, idle guard and cleanup (not browser evidence)');
