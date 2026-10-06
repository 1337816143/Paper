/* Independent hand-calculated fixtures plus whole reviewed domain; no browser claims. */
const assert = require('node:assert/strict');
const M = require('../../src/annual-balance-model.js');
const near = (actual, expected, label) => assert.ok(Math.abs(actual - expected) <= 1e-9, `${label}: ${actual} != ${expected}`);
const cases = [
  [{herd:8,forageArea:6,lossFraction:.2,replaceRetained:false}, {forageHarvest:36,feedDemand:40,feedConsumed:36,feedImported:4,feedExported:0,forageHarvestNitrogen:900,feedNitrogenConsumed:900,feedNitrogenImported:100,feedNitrogenExported:0,cashProductNitrogen:240,animalProductNitrogen:160,manureExcretedNitrogen:840,chainLoss:168,manureToSoil:672,baseMineralNitrogen:920,retainedNitrogen:0,mineralNitrogen:920,depositionNitrogen:100,soilResidual:552,farmInputs:1120,farmOutputs:400,farmSurplus:720,checkError:0}],
  [{...M.defaults,lossFraction:.1}, {chainLoss:84,manureToSoil:756,retainedNitrogen:84,mineralNitrogen:920,soilResidual:636,farmInputs:1120,farmOutputs:400,farmSurplus:720}],
  [{...M.defaults,lossFraction:.1,replaceRetained:true}, {chainLoss:84,manureToSoil:756,mineralNitrogen:836,soilResidual:552,farmInputs:1036,farmOutputs:400,farmSurplus:636}],
  [{...M.defaults,herd:0,forageArea:0}, {forageHarvest:0,feedDemand:0,feedConsumed:0,feedImported:0,feedExported:0,manureExcretedNitrogen:0,chainLoss:0,manureToSoil:0,mineralNitrogen:800,soilResidual:300,farmInputs:900,farmOutputs:600,farmSurplus:300}],
  [{...M.defaults,herd:0,forageArea:10}, {forageHarvest:60,feedConsumed:0,feedExported:60,feedNitrogenExported:1500,animalProductNitrogen:0,manureExcretedNitrogen:0,chainLoss:0,soilResidual:-400,farmInputs:1100,farmOutputs:1500,farmSurplus:-400}],
  [{...M.defaults,herd:4}, {forageHarvest:36,feedDemand:20,feedConsumed:20,feedImported:0,feedExported:16,feedNitrogenConsumed:500,feedNitrogenExported:400,manureExcretedNitrogen:420,chainLoss:84,manureToSoil:336,soilResidual:216,farmInputs:1020,farmOutputs:720,farmSurplus:300}],
  [{...M.defaults,herd:2,forageArea:0}, {feedImported:10,feedNitrogenImported:250,animalProductNitrogen:40,manureExcretedNitrogen:210,chainLoss:42,soilResidual:468,farmInputs:1150,farmOutputs:640,farmSurplus:510}],
  [{...M.defaults,herd:20,forageArea:0,lossFraction:0,replaceRetained:true}, {feedImported:100,manureExcretedNitrogen:2100,retainedNitrogen:420,mineralNitrogen:380,chainLoss:0,soilResidual:1980,farmInputs:2980,farmOutputs:1000,farmSurplus:1980}]
];
for (const [input, expected] of cases) { const actual = M.calculate(input); for (const [key, value] of Object.entries(expected)) near(actual[key],value,key); assert.deepEqual(actual.inputs,input); }
assert.equal(M.calculate({...M.defaults,herd:2,forageArea:0}).flags.feedImportExceeded,false);
assert.equal(M.calculate({...M.defaults,herd:3,forageArea:0}).flags.feedImportExceeded,true);
assert.equal(M.calculate({...M.defaults,herd:0,forageArea:4}).soilResidual,20);
assert.equal(M.calculate({...M.defaults,herd:0,forageArea:4.5}).soilResidual,-15);
assert.equal(M.calculate({...M.defaults,herd:0,forageArea:4}).feasible,true);
assert.equal(M.calculate({...M.defaults,herd:0,forageArea:4.5}).feasible,false);
const invalid = [null, [], {}, {...M.defaults,extra:1}, {...M.defaults,herd:'8'}, {...M.defaults,herd:null}, {...M.defaults,herd:false}, {...M.defaults,herd:NaN}, {...M.defaults,herd:Infinity}, {...M.defaults,herd:-1}, {...M.defaults,herd:21}, {...M.defaults,herd:8.5}, {...M.defaults,forageArea:''}, {...M.defaults,forageArea:6.1}, {...M.defaults,forageArea:10.5}, {...M.defaults,lossFraction:-.05}, {...M.defaults,lossFraction:.25}, {...M.defaults,lossFraction:.11}, {...M.defaults,replaceRetained:'false'}, {...M.defaults,replaceRetained:0}];
for(const input of invalid) assert.throws(()=>M.calculate(input));
let configurations = 0;
for(let herd=0;herd<=20;herd++) for(let areaIndex=0;areaIndex<=20;areaIndex++) for(let lossIndex=0;lossIndex<=4;lossIndex++) for(const replaceRetained of [false,true]) {
  const forageArea=areaIndex/2,lossFraction=lossIndex/20,r=M.calculate({herd,forageArea,lossFraction,replaceRetained});
  for(const key of Object.keys(M.units)) assert.ok(Number.isFinite(r[key]),key);
  // Algebraically reduced soil ledger, independent of the implementation's intermediate sums.
  const expectedSoil=300-70*forageArea+105*herd*(replaceRetained?.8:1-lossFraction);
  near(r.soilResidual,expectedSoil,'reduced soil ledger');
  near(r.forageHarvest,r.feedConsumed+r.feedExported,'all harvest has a destination');
  near(r.feedDemand,r.feedConsumed+r.feedImported,'all demand supplied before cap check');
  near(r.feedNitrogenConsumed+r.feedNitrogenImported,r.animalProductNitrogen+r.manureExcretedNitrogen,'animal boundary');
  near(r.manureExcretedNitrogen,r.chainLoss+r.manureToSoil,'manure boundary');
  near(r.farmInputs-r.farmOutputs,r.chainLoss+r.soilResidual,'whole farm boundary');
  assert.ok(r.mineralNitrogen>=0,'reviewed grid never creates negative mineral input');
  assert.equal(r.feasible,!r.flags.feedImportExceeded&&!r.flags.soilSupplyDeficit);
  configurations++;
}
assert.equal(configurations,4410);
assert.ok(Object.isFrozen(M.constants)&&Object.isFrozen(M.defaults)&&Object.isFrozen(M.domain));
console.log(JSON.stringify({status:'passed',hand_calculated_fixtures:cases.length,invalid_inputs:invalid.length,configurations,scope:'Pure JavaScript arithmetic and validation. No browser/layout claim.'}));
