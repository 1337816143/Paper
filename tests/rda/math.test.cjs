const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'../..'),m=require(path.join(root,'src/rda-model.js'));
const lines=fs.readFileSync(path.join(root,'examples/rda_synthetic_villages.csv'),'utf8').trim().split(/\r?\n/),keys=lines.shift().split(','),rows=lines.map(line=>Object.fromEntries(line.split(',').map((v,i)=>[keys[i],i?Number(v):v])));
let checks=0;
function near(a,b){if(a===null||b===null)return assert.equal(a,b);assert.ok(Math.abs(a-b)<1e-10,`${a} != ${b}`);}
function equal(a,b){if(Array.isArray(a)){assert.equal(a.length,b.length);a.forEach((v,i)=>equal(v,b[i]));}else if(typeof a==='number')near(a,b);else assert.equal(a,b);}
for(const v of [undefined,0,1,2,3.75,4.25,5]){const actual=m.calculate(rows,v),expected=JSON.parse(execFileSync('python',[path.join(root,'examples/rda_walkthrough.py'),...(v===undefined?[]:['--v4-b',String(v)])],{encoding:'utf8'}));for(const key of Object.keys(expected))equal(actual[key],expected[key]);checks++;}
const def=m.calculate(rows);near(def.Y_raw_correlation,Math.sqrt(2/27));near(def.Y_coordinate_cosine,0);near(def.X1_YA_coordinate_cosine,2/Math.sqrt(5));near(def.X1_YA_raw_correlation,Math.sqrt(2/3));checks++;
const changed=m.calculate(rows,4.25);assert.ok(Math.abs(changed.eigenvectors_columns[0][1])>.1);near(changed.constrained_eigenvalues[0],137/204+Math.sqrt(257)/68);near(changed.constrained_eigenvalues[1],137/204-Math.sqrt(257)/68);checks++;
const singular=m.calculate(rows.map(r=>({...r,perception_b:r.perception_a})));assert.deepEqual(singular.axis_defined,[true,false]);assert.ok(singular.Y_axis_correlations.every(r=>r[1]===null));checks++;
for(const bad of ['',null,NaN,Infinity,-1,6])assert.throws(()=>m.calculate(rows,bad));
for(const bad of [rows.map(r=>({...r,distance_km:1})),rows.map(r=>({...r,distance_km:r.crop_share_percent*2})),rows.concat(rows[0]),rows.map(r=>({...r,perception_a:''}))])assert.throws(()=>m.calculate(bad));checks++;
const reversed=m.calculate([...rows].reverse());equal(reversed.constrained_eigenvalues,def.constrained_eigenvalues);const units=m.calculate(rows.map(r=>({...r,distance_km:r.distance_km*1000,crop_share_percent:r.crop_share_percent/100})));equal(units.fitted_Y,def.fitted_Y);checks++;
console.log(JSON.stringify({passed:true,checks,scope:'JS/Python full-matrix parity at7 inputs, dynamic eigensystem, angle-vs-raw-correlation counterexample, undefined-axis, invalid-input and unit/row invariance'}));
