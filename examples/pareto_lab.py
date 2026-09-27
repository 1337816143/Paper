"""Synthetic teaching examples, NOT author data or full paper replication.
Run: python pareto_lab.py --test ; python pareto_lab.py
Python 3.10+, standard library only. All numeric objectives are minimized.
"""
from itertools import combinations
from math import isfinite, sqrt
from statistics import stdev
import argparse, unittest

def validate(rows):
    if not rows or not rows[0]:raise ValueError('Non-empty rectangular matrix required')
    m=len(rows[0])
    if any(len(r)!=m or any(not isinstance(v,(int,float)) or not isfinite(v) for v in r) for r in rows):raise ValueError('Finite rectangular numeric matrix required')

def dominates(a,b):
    return all(x<=y for x,y in zip(a,b)) and any(x<y for x,y in zip(a,b))

def nondominated(rows):
    validate(rows)
    return [not any(j!=i and dominates(s,r) for j,s in enumerate(rows)) for i,r in enumerate(rows)]

def pareto_rank(rows):
    validate(rows);remaining=list(range(len(rows)));rank=[0]*len(rows);level=1
    while remaining:
        flags=nondominated([rows[i] for i in remaining]);front=[i for i,ok in zip(remaining,flags) if ok]
        for i in front:rank[i]=level
        remaining=[i for i in remaining if i not in front];level+=1
    return rank

def efficiency_score(rows):
    """Small transparent implementation: smallest k with ND in ALL k-subsets.
    Compared against the complete supplied matrix. Dominated cases get None.
    Complexity is exponential in objective count; not a production optimizer.
    """
    validate(rows);n,m=len(rows),len(rows[0]);result=[None]*n
    active={i for i,ok in enumerate(nondominated(rows)) if ok}
    for k in range(1,m+1):
        survives=set(active)
        for subset in combinations(range(m),k):
            flags=nondominated([[r[j] for j in subset] for r in rows])
            survives.intersection_update(i for i,ok in enumerate(flags) if ok)
            if not survives:break
        for i in survives:result[i]=k
        active-=survives
        if not active:break
    return result

def ideal_distance(centroid,population):
    validate(population)
    if len(centroid)!=len(population[0]):raise ValueError('Dimension mismatch')
    distances=[]
    for k,p in enumerate(centroid):
        lo=min(r[k] for r in population);hi=max(r[k] for r in population)
        distances.append(abs(p-lo)/(hi-lo) if hi>lo else 0.0)
    return {'distances':distances,'MIDIP':sqrt(sum(v*v for v in distances)),'HDIP':stdev(distances) if len(distances)>1 else 0.0}

class Tests(unittest.TestCase):
    def test_duplicate(self):self.assertEqual(nondominated([[1,1],[1,1],[2,2]]),[True,True,False])
    def test_tradeoff(self):self.assertEqual(nondominated([[1,3],[2,2],[3,1]]),[True]*3)
    def test_rank(self):self.assertEqual(pareto_rank([[1,1],[2,2],[3,3]]),[1,2,3])
    def test_efficiency(self):self.assertEqual(efficiency_score([[1,1,1],[0,2,2],[2,0,2],[2,2,0]]),[2,3,3,3])
    def test_dominated(self):self.assertEqual(efficiency_score([[0,0],[1,1]]),[1,None])
    def test_distance(self):
        r=ideal_distance([.2,.2,.2],[[0,0,0],[1,1,1]])
        self.assertAlmostEqual(r['MIDIP'],sqrt(.12));self.assertEqual(r['HDIP'],0)
    def test_constant(self):self.assertEqual(ideal_distance([2,1],[[2,1],[2,3]])['MIDIP'],0)
    def test_bad(self):
        with self.assertRaises(ValueError):nondominated([[float('nan')]])
    def test_invariance(self):
        x=[[1,3],[2,2],[3,1],[3,3]]
        self.assertEqual(nondominated(x),nondominated([[a*10+7,b*2-1] for a,b in x]))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--test',action='store_true');a=p.parse_args()
    if a.test:unittest.main(argv=['pareto_lab.py'])
    else:
        rows=[[1,1,1],[0,2,2],[2,0,2],[2,2,0]]
        print('SYNTHETIC DATA; minimize all objectives')
        print('Rows:',rows);print('Non-dominated:',nondominated(rows));print('Efficiency scores:',efficiency_score(rows))
