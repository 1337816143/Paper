"""Synthetic 2-plot / 3-period planning exercise. NOT FarmSTEPS source code."""
from itertools import product
from pareto_lab import nondominated
CROPS={'grain':{'profit':8,'water':5,'labour':2},'legume':{'profit':7,'water':3,'labour':3},'vegetable':{'profit':14,'water':8,'labour':7}}
PERIODS=3;LABOUR_LIMIT=9
seq=[s for s in product(CROPS,repeat=PERIODS) if all(s[t]!=s[t-1] for t in range(1,PERIODS))]
plans=[]
for a,b in product(seq,repeat=2):
    labour=[CROPS[a[t]]['labour']+CROPS[b[t]]['labour'] for t in range(PERIODS)]
    if max(labour)>LABOUR_LIMIT:continue
    profit=sum(CROPS[c]['profit'] for c in a+b);water=sum(CROPS[c]['water'] for c in a+b)
    plans.append({'A':a,'B':b,'labour':labour,'profit':profit,'water':water})
flags=nondominated([[-p['profit'],p['water']] for p in plans])
assert all(max(p['labour'])<=LABOUR_LIMIT for p in plans)
print('SYNTHETIC EDUCATIONAL PROBLEM; not paper case-study counts')
print('Sequences per plot:',len(seq),'Feasible plans:',len(plans),'ND plans:',sum(flags))
for p,ok in list(zip(plans,flags))[:12]:print(p,'ND=',ok)
