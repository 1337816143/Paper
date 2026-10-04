const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const {model: m} = require(path.join(root, 'src/research-walkthrough.js'));
let count = 0;
const check = (name, fn) => { fn(); count++; console.log('PASS', name); };
const near = (a,b) => assert.ok(Math.abs(a-b)<1e-10, `${a} != ${b}`);
const python = file => JSON.parse(execFileSync('python',[path.join(root,'examples',file)],{encoding:'utf8'}));
check('audited join and legacy Pareto/distance Python parity',()=>{
  const p=python('research_pipeline_walkthrough.py'), j=m.aggregate([10000,20000,30000],[5,7]), d=m.decision();
  assert.deepEqual([j.wrong.length,j.wrongCrop,j.wrongManure],[p.join.wrong_rows,p.join.wrong_crop_Mg,p.join.wrong_manure_Mg]);
  assert.deepEqual([j.correctCrop,j.correctManure],[60,12]);
  assert.deepEqual(d.fronts,p.pareto.fronts); assert.deepEqual(d.ideal,p.ideal_distance.ideal); assert.deepEqual(d.ranges,p.ideal_distance.ranges);
  ['A','C'].forEach(id=>{assert.deepEqual(d.distances[id].d,p.ideal_distance[id].d);near(d.distances[id].MIDIP,p.ideal_distance[id].MIDIP);near(d.distances[id].HDIP,p.ideal_distance[id].HDIP)});
});
check('all seven independent indicator arithmetic equals audited Python',()=>{
  const p=python('seven_indicators_worked.py'), i=m.indicators();
  [[i.gm,p.gm.per_ha_year],[i.gmTotal,p.gm.total_0_6_ha],[i.dey,p.dey.per_ha_year],[i.deyTotal,p.dey.total_0_6_ha],[i.labor,p.labor.per_ha_year],[i.laborTotal,p.labor.total_0_6_ha],[i.gwd,p.gwd.per_year_mm],[i.gwdVolume,p.gwd.m3_for_0_6_ha_year],[i.nitrogen,p.nl.per_ha_year],[i.nitrogenTotal,p.nl.total_0_6_ha],[i.ghg,p.ghg.net_per_ha_year],[i.ghgTotal,p.ghg.total_0_6_ha],[i.pesticide,p.pu.annual_total]].forEach(([a,b])=>near(a,b));
});
check('one main fixture derives every annual result from raw seasons',()=>{
  const p=m.farmPipeline();
  assert.deepEqual(p.rows.map(r=>r.margin),[1900,1700,2200,2600]);
  assert.deepEqual(p.rows.map(r=>r.water),[260,280,300,180]);
  assert.deepEqual(p.rows.map(r=>r.labor),[74,80,85,140]);
  for(const r of p.rows){assert.deepEqual(r.yieldMgHa,[6,8]);assert.equal(r.revenue,3800);near(r.margin,r.revenue-r.source.costs[0]-r.source.costs[1]);near(r.water,.8*(r.source.irrigation[0]+r.source.irrigation[1])-.2*500)}
});
check('main CSV/Python companion matches every farm and feasibility boundary',()=>{
  for(const cap of [0,74,85,100,140,160]){
    const p=JSON.parse(execFileSync('python',[path.join(root,'examples/farm_walkthrough.py'),'--labor-cap',String(cap)],{encoding:'utf8'})),v=m.farmPipeline({laborCap:cap});
    for(let i=0;i<4;i++)for(const k of ['margin','water','labor'])near(v.rows[i][k],p.rows[i][k]);
    assert.deepEqual(v.fronts,p.fronts);assert.deepEqual(v.observedFronts,p.observed_fronts_without_added_cap);assert.deepEqual(v.ideal,p.ideal);assert.deepEqual(v.ranges,p.ranges);
    assert.deepEqual(v.feasible.map(r=>r.id),p.feasible);
    for(const id of p.feasible){assert.deepEqual(v.distances[id].d,p.distances[id].d);near(v.distances[id].MIDIP,p.distances[id].MIDIP);near(v.distances[id].HDIP,p.distances[id].HDIP)}
  }
});
check('observed-only ranking differs explicitly from added feasibility extension',()=>{
  const p=m.farmPipeline();
  assert.deepEqual(p.observedFronts,[['D'],['A','C'],['B']]);assert.deepEqual(p.fronts,[['A','C'],['B']]);assert.deepEqual(p.excluded.map(r=>r.id),['D']);
  assert.deepEqual(m.farmPipeline({laborCap:140}).fronts,p.observedFronts);
});
check('main ideal values, ranges and exact two-dimensional distances',()=>{
  const p=m.farmPipeline();assert.deepEqual(p.ideal,[2200,260]);assert.deepEqual(p.ranges,[500,40]);
  assert.deepEqual(p.distances.A.d,[.6,0]); near(p.distances.A.MIDIP,.6);near(p.distances.A.HDIP,Math.sqrt(.18));
  assert.deepEqual(p.distances.C.d,[0,1]);near(p.distances.C.MIDIP,1);near(p.distances.C.HDIP,Math.sqrt(.5));
  near(p.distances.B.HDIP,Math.sqrt(.125));
});
check('changing raw cost and water really propagates to frontiers and distance',()=>{
  const p=m.farmPipeline({costAW:600,waterAW:250});const a=p.rows[0];
  assert.equal(a.margin,2300);assert.equal(a.water,220);assert.deepEqual(p.fronts[0],['A']);assert.equal(p.distances.A.MIDIP,0);
});
check('empty and singleton feasible sets are honest',()=>{
  const empty=m.farmPipeline({laborCap:0});assert.equal(empty.ideal,null);assert.deepEqual(empty.distances,{});assert.deepEqual(empty.fronts,[]);
  const single=m.farmPipeline({laborCap:74});assert.deepEqual(single.fronts,[['A']]);assert.deepEqual(single.ranges,[0,0]);assert.deepEqual(single.distances.A.d,[0,0]);
});
check('constant columns handled without NaN or infinity',()=>{
  assert.deepEqual(m.distance([1,2],[1,1],[0,2]).d,[0,.5]);assert.equal(m.distance([1],[1],[0]).HDIP,null);
  assert.throws(()=>m.distance([2],[1],[0]));assert.throws(()=>m.distance([1],[1],[-1]));assert.throws(()=>m.distance([],[],[]));assert.throws(()=>m.distance([1],[1,2],[1]));
});
check('no self/equal-vector domination and ordering invariant',()=>{
  const a={id:'A',margin:10,water:10},b={id:'B',margin:10,water:10};assert.equal(m.dominates(a,a),false);assert.equal(m.dominates(a,b),false);assert.deepEqual(m.fronts([a,b]),[['A','B']]);
  const p=m.farmPipeline();assert.deepEqual(m.fronts([...p.feasible].reverse()).map(f=>f.sort()),p.fronts.map(f=>f.slice().sort()));
});
check('invalid, missing and fractional inputs',()=>{
  assert.throws(()=>m.calculate({costAW:NaN}));assert.throws(()=>m.calculate({costAW:Infinity}));assert.throws(()=>m.calculate({costAW:''}));assert.throws(()=>m.calculate({area:0}));assert.throws(()=>m.calculate({crop3:-1}));
  assert.throws(()=>m.aggregate([],[]));assert.throws(()=>m.aggregate([-2],[4]));
  near(m.aggregate([10000,20000,30001.5],[5,7]).correctCrop,60.0015);
});
check('independent side experiments never silently change main farm records',()=>{
  const before=m.farmPipeline(), after=m.farmPipeline({wheat:10,maize:15,irrigation:600,area:2,crop3:15000,manure2:12});assert.deepEqual(before,after);
  assert.equal(m.indicators({area:3}).pesticide,6);
});
check('deterministic finite outputs throughout all allowed cap states',()=>{
  for(let cap=0;cap<=160;cap++){const p=m.farmPipeline({laborCap:cap});for(const d of Object.values(p.distances)){assert.ok(Number.isFinite(d.MIDIP));assert.ok(Number.isFinite(d.HDIP));assert.ok(d.d.every(Number.isFinite))}}
});
console.log(JSON.stringify({passed:count,scope:'Exact arithmetic, Python parity, coherent source-to-output propagation, edge cases'}));
