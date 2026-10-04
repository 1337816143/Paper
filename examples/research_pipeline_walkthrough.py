#!/usr/bin/env python3
"""Synthetic data-grain, Pareto, and ideal-distance walkthrough. Not author data."""
import argparse,json,math,statistics


def dominates(a,b):
    return a['margin']>=b['margin'] and a['water']<=b['water'] and (a['margin']>b['margin'] or a['water']<b['water'])


def distances(centroid,ideal,ranges):
    if not len(centroid)==len(ideal)==len(ranges) or not centroid:raise ValueError('Matching nonempty vectors required')
    if not all(math.isfinite(v) for row in [centroid,ideal,ranges] for v in row) or any(r<0 for r in ranges):raise ValueError('Finite inputs and nonnegative ranges required')
    if any(r==0 and p!=q for p,q,r in zip(centroid,ideal,ranges)):raise ValueError('Constant-column values must equal its ideal')
    d=[abs(p-q)/r if r else 0 for p,q,r in zip(centroid,ideal,ranges)]
    return {'d':d,'MIDIP':math.sqrt(sum(v*v for v in d)),'HDIP':statistics.stdev(d) if len(d)>1 else None,'mean_d':statistics.mean(d)}


def calculate():
    crops_kg=[10000,20000,30000];manure_Mg=[5,7]
    crops_Mg=[x/1000 for x in crops_kg]
    wrongly_joined=[(c,m) for c in crops_Mg for m in manure_Mg]
    rows=[{'id':'A','margin':100,'water':30,'labor':80},{'id':'B','margin':80,'water':40,'labor':85},{'id':'C','margin':120,'water':50,'labor':90},{'id':'D','margin':200,'water':10,'labor':140}]
    feasible=[r for r in rows if r['labor']<=100]
    remaining=list(feasible);fronts=[]
    while remaining:
        front=[r for r in remaining if not any(dominates(o,r) for o in remaining)]
        fronts.append([r['id'] for r in front]);remaining=[r for r in remaining if r not in front]
    q=[max(r['margin'] for r in feasible),min(r['water'] for r in feasible)]
    ranges=[max(r['margin'] for r in feasible)-min(r['margin'] for r in feasible),max(r['water'] for r in feasible)-min(r['water'] for r in feasible)]
    return {'synthetic':True,'author_result_reproduced':False,
            'join':{'wrong_rows':len(wrongly_joined),'wrong_crop_Mg':sum(x[0] for x in wrongly_joined),'wrong_manure_Mg':sum(x[1] for x in wrongly_joined),'correct_rows':1,'correct_crop_Mg':sum(crops_Mg),'correct_manure_Mg':sum(manure_Mg)},
            'pareto':{'rows':rows,'labor_cap_h':100,'excluded':['D'],'fronts':fronts},
            'ideal_distance':{'ideal':q,'ranges':ranges,'A':distances([100,30],q,ranges),'C':distances([120,50],q,ranges),'scope':'Singleton teaching groups only; no original HCA or clustering reproduction'}}


def test():
    r=calculate();j=r['join'];assert (j['wrong_rows'],j['wrong_crop_Mg'],j['wrong_manure_Mg'])==(6,120,36)
    assert (j['correct_rows'],j['correct_crop_Mg'],j['correct_manure_Mg'])==(1,60,12)
    assert r['pareto']['fronts']==[['A','C'],['B']]
    d=r['ideal_distance'];assert d['ideal']==[120,30] and d['ranges']==[40,20]
    assert d['A']['d']==[0.5,0] and d['C']['d']==[0,1]
    assert d['A']['MIDIP']==0.5 and d['C']['MIDIP']==1
    assert math.isclose(d['A']['HDIP'],math.sqrt(0.125)) and math.isclose(d['C']['HDIP'],math.sqrt(0.5))
    assert distances([1],[1],[0])['HDIP'] is None
    assert distances([1,2],[1,1],[0,2])['d']==[0,0.5]
    try:distances([2],[1],[0])
    except ValueError:pass
    else:raise AssertionError('Inconsistent constant column accepted')
    assert not dominates(r['pareto']['rows'][0],r['pareto']['rows'][0])
    return {'passed':True,'scope':'Synthetic key/aggregation, feasibility, Pareto and distance calculations'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--test',action='store_true');a=p.parse_args()
    print(json.dumps(test() if a.test else calculate(),ensure_ascii=False,indent=2))
