/* DOM simulation only: lifecycle and event/state contracts, never browser conformance. */
const assert=require('node:assert/strict'),{env,Node}=require('./dom-harness.cjs');
let passed=0;
function test(name,fn){fn();passed++;console.log('PASS DOM-simulated',name);}
test('old history keys cannot alias another entry after a document reload',()=>{
 const old=env();old.input('herd',12);const oldState={...old.win.history.state};
 const fresh=env();fresh.input('herd',4);
 assert.notEqual(fresh.win.history.state.paperAnnualEntry,oldState.paperAnnualEntry);
 fresh.ctl.destroy();fresh.win.history.state=oldState;
 const restored=fresh.api.mount(fresh.container);
 assert.equal(restored.getState().inputs.herd,8);
 assert.equal(restored.getState().step,0);
});
test('all six manual stages use the same default model and scoped button attributes',()=>{
 const e=env();assert.equal(e.api.isBusy(),false);assert.equal(e.ctl.getState().pendingTimer,false);
 for(let i=0;i<6;i++){e.click(`[data-annual-stage="${i}"]`);assert.equal(e.ctl.getState().step,i);assert.ok(e.q('.annual-stage').textContent.length>160);assert.ok(!/NaN|Infinity/.test(e.panel.textContent));}
 assert.equal(e.panel.querySelectorAll('[data-step]').length,0);
 assert.ok(e.q('.annual-stage').textContent.includes('额外保留量大于0时'));
 e.click('[data-annual-action="reset"]');assert.equal(e.api.isBusy(),false);
 for(const [key,value] of [['farmSurplus','720.00'],['chainLoss','168.00'],['soilResidual','552.00']])assert.equal(e.q(`[data-annual-value="${key}"]`).textContent,value);
});
test('persistent controls retain identity, keyboard focus and native step properties',()=>{
 const e=env(),control=e.q('[data-annual-field="lossFraction"]');control.focus();e.input('lossFraction',.1);
 assert.equal(e.doc.activeElement,control);assert.equal(e.q('[data-annual-field="lossFraction"]'),control);assert.equal(e.ctl.getState().step,0);
 assert.equal(e.q('[data-annual-value="chainLoss"]').textContent,'84.00');assert.equal(e.q('[data-annual-diagram="soilResidual"]').textContent,'636.00');
 assert.ok(e.q('.annual-all-table').textContent.includes('636.00'));assert.equal(e.api.isBusy(),true);
});
test('invalid drafts keep and visibly label the last valid result; no downloads',()=>{
 const e=env();e.input('lossFraction',.1);const expected=JSON.stringify(e.ctl.getState().result);
 for(const invalid of ['', 'abc', 'Infinity', 'NaN', '0x0', ' 0.1 ', -.1, .11, .25]){
  e.input('lossFraction',invalid);assert.equal(e.ctl.getState().invalid,true);assert.equal(JSON.stringify(e.ctl.getState().result),expected);
  assert.equal(e.q('[data-annual-field="lossFraction"]').getAttribute('aria-invalid'),'true');assert.ok(e.q('.annual-status').textContent.includes('保留上次有效结果'));assert.ok(e.q('.annual-figure-caption').textContent.startsWith('上次有效结果'));
  for(const button of e.panel.querySelectorAll('[data-annual-download]'))assert.equal(button.disabled,true);
  assert.throws(()=>e.ctl.getExportData());
 }
 e.input('herd','');e.input('lossFraction',.1);assert.equal(e.ctl.getState().invalid,true);
 e.input('herd',8);assert.equal(e.ctl.getState().invalid,false);assert.equal(e.q('[data-annual-download="inputs"]').disabled,false);
});
test('three manual scenarios preserve herd/area and make the input reduction explicit',()=>{
 const e=env();e.click('[data-annual-stage="5"]');e.click('[data-annual-scenario="retain"]');
 assert.equal(e.ctl.getState().result.chainLoss,84);assert.equal(e.ctl.getState().result.soilResidual,636);assert.equal(e.ctl.getState().result.farmSurplus,720);
 e.click('[data-annual-scenario="replace"]');assert.equal(e.ctl.getState().result.mineralNitrogen,836);assert.equal(e.ctl.getState().result.soilResidual,552);assert.equal(e.ctl.getState().result.farmSurplus,636);assert.equal(e.q('[data-annual-field="replaceRetained"]').checked,true);
 e.input('herd',4);e.click('[data-annual-scenario="reference"]');assert.equal(e.ctl.getState().inputs.herd,4);assert.equal(e.ctl.getState().inputs.forageArea,6);assert.equal(e.ctl.getState().inputs.lossFraction,.2);assert.equal(e.ctl.getState().inputs.replaceRetained,false);
});
test('zero herd exports full harvest and negative soil residual remains an explicit failure',()=>{
 const e=env();e.input('herd',0);e.input('forageArea',10);const r=e.ctl.getState().result;
 assert.equal(r.feedNitrogenExported,1500);assert.equal(r.manureExcretedNitrogen,0);assert.equal(r.soilResidual,-400);assert.equal(r.feasible,false);
 assert.ok(e.q('.annual-constraints').textContent.includes('供应赤字 400.00'));assert.equal(e.q('[data-annual-diagram="feedNitrogenExported"]').textContent,'1500.00');
 e.click('[data-annual-stage="3"]');assert.ok(e.q('.annual-stage').textContent.includes('− 1500.00'));assert.ok(e.q('.annual-stage').textContent.includes('不是“负污染”'));
 e.input('herd',2);e.input('forageArea',0);assert.equal(e.ctl.getState().result.flags.feedImportExceeded,false);e.input('herd',3);assert.equal(e.ctl.getState().result.flags.feedImportExceeded,true);
});
test('safe-update guard covers stages, form focus, opened ledger, selection, modified and invalid work',()=>{
 const e=env();const control=e.q('[data-annual-field="herd"]');control.focus();assert.equal(e.api.isBusy(),true);e.doc.activeElement=null;assert.equal(e.api.isBusy(),false);
 e.q('.annual-ledger').open=true;assert.equal(e.api.isBusy(),true);e.click('[data-annual-action="reset"]');assert.equal(e.q('.annual-ledger').open,false);assert.equal(e.api.isBusy(),false);
 e.win.selection={isCollapsed:false,anchorNode:e.q('.annual-stage')};assert.equal(e.api.isBusy(),true);e.win.selection=null;
 e.click('[data-annual-stage="2"]');assert.equal(e.api.isBusy(),true);e.ctl.reset();assert.equal(e.api.isBusy(),false);assert.ok(e.doc.activeElement.isConnected);
 e.input('herd',12);assert.equal(e.api.isBusy(),true);e.input('herd','');assert.equal(e.api.isBusy(),true);e.click('[data-annual-action="reset"]');assert.equal(e.ctl.getState().invalid,false);assert.equal(e.q('[data-annual-field="herd"]').value,'8');assert.equal(e.api.isBusy(),false);
});
test('opaque entry snapshots restore valid and invalid inputs, stage and expansion in memory',()=>{
 const e=env();e.input('herd',12);e.click('[data-annual-stage="4"]');e.q('.annual-ledger').open=true;e.panel.listeners.toggle();e.input('forageArea','');
 const saved=e.win.history.state;assert.deepEqual(Object.keys(saved),['paperAnnualEntry']);
 e.ctl.destroy();const again=e.api.mount(e.container);assert.equal(again.getState().inputs.herd,12);assert.equal(again.getState().step,4);assert.equal(again.getState().invalid,true);assert.equal(e.container.querySelector('.annual-ledger').open,true);assert.equal(e.container.querySelector('[data-annual-field="forageArea"]').value,'');
 again.destroy();e.win.history.state={};const fresh=e.api.mount(e.container);assert.equal(fresh.getState().inputs.herd,8);assert.equal(fresh.getState().step,0);assert.equal(fresh.getState().invalid,false);
});
test('paired same-route events keep a fresh mount; navigation/detachment release handlers and guards',()=>{
 const e=env();assert.equal(e.api.mount(e.container),e.ctl);e.input('herd',12);e.win.dispatch('popstate');e.win.dispatch('hashchange');assert.equal(e.ctl.getState().mounted,true);
 e.win.location.hash='#/original/farmdesign-2012';e.win.dispatch('hashchange');assert.equal(e.ctl.getState().mounted,false);assert.equal(e.api.isBusy(),false);assert.equal(e.container.children.length,0);
 for(const key of ['hashchange','popstate','beforeprint','afterprint'])assert.equal(e.win.listeners[key].size,0);
 const fresh=e.api.mount(e.container);e.win.dispatch('popstate');e.win.dispatch('hashchange');assert.equal(fresh.getState().mounted,true);
 e.container.remove();e.observers.filter(o=>!o.off).forEach(o=>o.f());assert.equal(fresh.getState().mounted,false);assert.equal(e.api.isBusy(),false);
});
test('downloads distinguish executable four-column input from full precision result artifacts',()=>{
 const e=env();e.input('lossFraction',.1);e.input('replaceRetained',true);
 for(const type of ['inputs','json','csv'])e.click(`[data-annual-download="${type}"]`);
 assert.equal(e.blobs[0].parts.join(''),'herd,forageArea,lossFraction,replaceRetained\r\n8,6,0.1,true\r\n');
 const output=JSON.parse(e.blobs[1].parts.join(''));assert.equal(output.result.mineralNitrogen,836);assert.equal(output.units.farmSurplus,'kg N/year');assert.ok(output.caveats.some(s=>s.includes('不是作者数据')));
 const csv=e.blobs[2].parts.join('');assert.ok(csv.startsWith('\ufeff"category","key","label","value","unit"'));assert.ok(csv.includes('"farmSurplus","全场N盈余","636","kg N/year"'));assert.ok(csv.includes('"replaceRetained","replaceRetained","true","boolean"'));
 assert.equal(e.ctl.getState().pendingDownloads,3);assert.equal(e.api.isBusy(),true);e.ctl.destroy();assert.equal(e.revoked.length,3);assert.equal(e.timers.size,0);
});
test('printing exposes full current ledger then restores expansion state',()=>{
 const e=env();assert.equal(e.q('.annual-ledger').open,false);e.win.dispatch('beforeprint');assert.equal(e.q('.annual-ledger').open,true);assert.equal(e.api.isBusy(),true);e.win.dispatch('afterprint');assert.equal(e.q('.annual-ledger').open,false);assert.equal(e.api.isBusy(),false);
 e.q('.annual-ledger').open=true;e.win.dispatch('beforeprint');e.win.dispatch('afterprint');assert.equal(e.q('.annual-ledger').open,true);
});
test('native scrolling/form keys remain available and generated controls/figures have labels',()=>{
 const e=env();for(const target of [e.q('[data-annual-field="herd"]'),e.q('.annual-chart-scroll'),e.q('.annual-table-scroll')]){let prevented=false;e.panel.listeners.keydown({target,key:'ArrowRight',preventDefault(){prevented=true}});assert.equal(prevented,false);assert.equal(e.ctl.getState().step,0);}
 let prevented=false;e.panel.listeners.keydown({target:e.panel,key:'End',preventDefault(){prevented=true}});assert.equal(prevented,true);assert.equal(e.ctl.getState().step,5);
 const ids=e.panel.querySelectorAll('[id]').map(n=>n.id);assert.equal(ids.length,new Set(ids).size);
 for(const input of e.panel.querySelectorAll('input'))assert.ok(e.panel.querySelectorAll('label').some(label=>label.getAttribute('for')===input.id));
 for(const svg of e.panel.querySelectorAll('svg')){assert.ok(svg.querySelector('title'));assert.ok(svg.querySelector('desc'));}
 for(const t of e.panel.querySelectorAll('table'))assert.ok(t.querySelector('caption'));
 assert.equal(e.panel.querySelectorAll('.prose,[data-block]').length,0);assert.equal(e.panel.getAttribute('data-no-terms'),'true');
});
console.log(JSON.stringify({status:'passed',checks:passed,scope:'DOM simulation only; no actual browser, accessibility, screenshot or mobile layout claim.'}));
