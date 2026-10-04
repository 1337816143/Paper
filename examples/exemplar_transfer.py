#!/usr/bin/env python3
"""Complete synthetic counterexample, not Liang data or an official farm engine.

All four potential-outcome cells are invented. No causal effect is estimated
from observations. Three objectives (margin max, water min, labor min) only.
The optional extra hiring scenario is feasible only if labor is available.
"""
import argparse
import json
import math

SYNTHETIC = [
    {'id':'H-B','context':'H','management':'B','margin':1800,'water':220,'labor':60},
    {'id':'H-M','context':'H','management':'M','margin':2100,'water':170,'labor':90},
    {'id':'L-B','context':'L','management':'B','margin':1000,'water':240,'labor':80},
    {'id':'L-M','context':'L','management':'M','margin':1100,'water':190,'labor':120},
]


def dominates(a,b):
    av=(-a['margin'],a['water'],a['labor'])
    bv=(-b['margin'],b['water'],b['labor'])
    return all(x<=y for x,y in zip(av,bv)) and any(x<y for x,y in zip(av,bv))


def difference(a,b):
    return {k:a[k]-b[k] for k in ('margin','water','labor')}


def evaluate(records=None,area_ha=1,available_labor_h=90,wage_per_h=15,hiring_available=True):
    if not all(math.isfinite(v) for v in [area_ha,available_labor_h,wage_per_h]) or area_ha<=0 or available_labor_h<0 or wage_per_h<0:
        raise ValueError('Area must be positive; labor and wage must be nonnegative')
    records=SYNTHETIC if records is None else records
    rows={r['id']:r for r in records}
    if len(rows)!=len(records) or set(rows)!={'H-B','H-M','L-B','L-M'}:
        raise ValueError('Exactly four uniquely identified synthetic cells are required')
    # This contrast holds a feasible baseline fixed; it does not model hiring
    # already needed by an infeasible baseline. Reject that different question.
    if rows['L-B']['labor']*area_ha>available_labor_h:
        raise ValueError('This counterexample requires a feasible baseline without extra hiring')
    if not all(math.isfinite(r[k]) for r in records for k in ('margin','water','labor')):
        raise ValueError('Synthetic outcomes must be finite numbers')
    frontier=[r['id'] for r in records if not any(dominates(o,r) for o in records)]
    delta=difference(rows['L-M'],rows['L-B'])
    demand=rows['L-M']['labor']*area_ha
    shortage=max(0,demand-available_labor_h)
    feasible=shortage==0
    adapted_feasible=feasible or hiring_available
    return {
        'basis':'SYNTHETIC invented four-cell counterexample; not an estimated causal effect',
        'official_model_run':False,'author_result_reproduced':False,
        'feasibility_scope':'Annual labor only; not seasonal peaks or every farm resource',
        'units':{'margin':'USD/ha/year','water':'mm/year','labor':'h/ha/year'},
        'records':records,'frontier':frontier,
        'pooled_HM_minus_LB':difference(rows['H-M'],rows['L-B']),
        'within_L_M_minus_B':delta,
        'low_resource_case':{
            'area_ha':area_ha,'labor_capacity_h_per_year':available_labor_h,
            'baseline_feasible':rows['L-B']['labor']*area_ha<=available_labor_h,
            'candidate_labor_h_per_year':demand,'shortfall_h_per_year':shortage,
            'candidate_feasible_without_hiring':feasible,
            'additional_hiring_available':hiring_available,
            'additional_hiring_wage_USD_per_h':wage_per_h,
            'candidate_feasible_with_hiring':adapted_feasible,
            'net_increment_USD_per_year_after_extra_hiring':delta['margin']*area_ha-shortage*wage_per_h if adapted_feasible else None,
            'cost_boundary':'Only extra hiring cost not already included in synthetic margin is subtracted',
        },
    }


def test():
    r=evaluate()
    assert r['frontier']==['H-B','H-M']
    assert r['pooled_HM_minus_LB']=={'margin':1100,'water':-70,'labor':10}
    assert r['within_L_M_minus_B']=={'margin':100,'water':-50,'labor':40}
    x=r['low_resource_case']
    assert x['baseline_feasible'] and not x['candidate_feasible_without_hiring']
    assert x['shortfall_h_per_year']==30 and x['net_increment_USD_per_year_after_extra_hiring']==-350
    assert not dominates(SYNTHETIC[0],SYNTHETIC[0])
    assert sorted(evaluate(list(reversed(SYNTHETIC)))['frontier'])==sorted(r['frontier'])
    assert evaluate(available_labor_h=120)['low_resource_case']['net_increment_USD_per_year_after_extra_hiring']==100
    nohire=evaluate(hiring_available=False)['low_resource_case']
    assert not nohire['candidate_feasible_with_hiring'] and nohire['net_increment_USD_per_year_after_extra_hiring'] is None
    double=evaluate(area_ha=2,available_labor_h=180)['low_resource_case']
    assert double['shortfall_h_per_year']==60 and double['net_increment_USD_per_year_after_extra_hiring']==-700
    for args in [{'area_ha':0},{'available_labor_h':-1},{'available_labor_h':79},{'wage_per_h':-1},{'area_ha':float('nan')},{'wage_per_h':float('inf')},{'available_labor_h':float('inf')}]:
        try:evaluate(**args)
        except ValueError:pass
        else:raise AssertionError('Invalid units/input accepted')
    return {'passed':True,'scope':'Synthetic mechanism and feasibility accounting only'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test',action='store_true')
    args=parser.parse_args()
    print(json.dumps(test() if args.test else evaluate(),ensure_ascii=False,indent=2))
