"""Cross-language checks on declared synthetic settings only; no author-data claims."""
from pathlib import Path
import json,subprocess,sys,math
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'examples'))
from dong_boundary_lab import Parameters,invert_ammonia,conditional_interval,boundary_ledger,synthetic_flows,Flow
cases=[]
for f in [.1,.4,.75,.99]:
 for ag in [.2,.4,.8]:
  for limit in [0,1,10,20]:
   p=Parameters(share_fe_fix=f,agricultural_land_fraction=ag)
   cases.append({'p':{'share_fe_fix':f,'agricultural_land_fraction':ag},'limit':limit,'expected':invert_ammonia(limit,p),'intervals':[conditional_interval(t,limit,p) for t in [0,50,55]]})
node="""const m=require(process.argv[1]),fs=require('node:fs'),a=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(a.map(c=>({upper:m.invert(c.limit,c.p),intervals:[0,50,55].map(t=>m.interval(t,c.limit,c.p))}))));"""
r=subprocess.run(['node','-e',node,str(ROOT/'src/dong-boundary-model.js')],input=json.dumps(cases),capture_output=True,text=True,check=True);actual=json.loads(r.stdout);comparisons=0;maximum=0
for a,e in zip(actual,cases):
 for got,expected in [(a['upper'],e['expected']),*zip(a['intervals'],e['intervals'])]:
  assert got.keys()==expected.keys()
  for k,v in expected.items():
   if isinstance(v,bool):assert got[k] is v
   else:
    error=abs(got[k]-v);maximum=max(maximum,error);assert math.isfinite(got[k]) and error<=1e-8,(e,k,got[k],v)
   comparisons+=1
node="""const m=require(process.argv[1]);console.log(JSON.stringify(['crop','livestock','combined'].flatMap(b=>[0,123].map(x=>({boundary:b,extra:x,value:m.ledger(b,x)})))));"""
r=subprocess.run(['node','-e',node,str(ROOT/'src/dong-boundary-model.js')],capture_output=True,text=True,check=True)
for row in json.loads(r.stdout):
 flows=synthetic_flows()+([Flow('outside','crop','extra',row['extra'])] if row['extra'] else [])
 members={'crop','livestock'} if row['boundary']=='combined' else {row['boundary']};expected=boundary_ledger(flows,members)
 for k,v in expected.items():assert row['value'][k]==v;comparisons+=1
out={'passed':True,'syntheticParameterCases':len(cases),'scalarComparisons':comparisons,'maximumAbsoluteError':maximum,'tolerance':1e-8,'scope':'Our JS versus our independently reviewed Python, not author raw-data or NUFER reproduction'}
(ROOT/'test-results').mkdir(exist_ok=True);(ROOT/'test-results/dong-parity.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
