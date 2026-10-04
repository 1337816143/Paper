#!/usr/bin/env python3
"""Reproduce the visual walkthrough's coherent SYNTHETIC four-farm calculations.

Python standard library only. Run: python farm_walkthrough.py --test
Or: python farm_walkthrough.py --input farm_walkthrough_synthetic.csv --labor-cap 100

Author reference: Liang et al.2022, DOI10.1016/j.agsy.2022.103471, Eqs1,3–5.
All farm records are invented. Alpha0.2 illustrates the paper's local parameter.
This program compares TWO objectives, not the paper's seven. Labor feasibility
is a teaching/research-transfer extension, not an author sampling filter. It
neither implements HCA nor reproduces the author344/56/9 counts. It makes no
crop-yield response, causal, local-calibration or original-data claim.
"""
import argparse,csv,json,math,statistics
from collections import defaultdict
from pathlib import Path

DATA=Path(__file__).with_name('farm_walkthrough_synthetic.csv')
NUMERIC=['area_ha','harvest_kg','price_usd_per_Mg','cost_usd_per_ha','irrigation_mm','labor_h_per_ha','annual_rain_mm','recharge_alpha','period_years']


def read_records(path=DATA):
    with Path(path).open(newline='',encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    if not rows:raise ValueError('At least one crop-event record is required')
    return rows


def calculate(records=None,labor_cap_h=100):
    if not math.isfinite(labor_cap_h) or labor_cap_h<0:raise ValueError('Labor cap must be finite and nonnegative')
    records=read_records() if records is None else records
    groups=defaultdict(list);keys=set()
    for original in records:
        r=dict(original)
        if not r.get('farm_id') or not r.get('crop_event'):raise ValueError('farm_id and crop_event are required')
        key=(r['farm_id'],r['crop_event'])
        if key in keys:raise ValueError('Duplicate farm/crop-event key')
        keys.add(key)
        for k in NUMERIC:
            try:r[k]=float(r[k])
            except (KeyError,TypeError,ValueError) as e:raise ValueError('Missing or invalid numeric field: '+k) from e
            if not math.isfinite(r[k]) or r[k]<0:raise ValueError('Expected finite, nonnegative '+k)
        if r['area_ha']<=0 or r['period_years']<=0:raise ValueError('Area and period length must be positive')
        if r['recharge_alpha']>1:raise ValueError('Recharge coefficient must be within0..1')
        groups[r['farm_id']].append(r)
    if not groups:raise ValueError('No records')
    computed=[]
    for id,events in groups.items():
        first=events[0]
        for k in ['area_ha','period_years','annual_rain_mm','recharge_alpha']:
            if any(e[k]!=first[k] for e in events):raise ValueError('Inconsistent farm-level '+k)
        area=first['area_ha'];years=first['period_years']
        converted=[dict(e,yield_Mg_per_ha=e['harvest_kg']/1000/area,revenue_usd_per_ha=e['harvest_kg']/1000/area*e['price_usd_per_Mg']) for e in events]
        revenue=sum(e['revenue_usd_per_ha'] for e in converted)
        cost=sum(e['cost_usd_per_ha'] for e in events)
        irrigation=sum(e['irrigation_mm'] for e in events)
        recharge=first['recharge_alpha']*(irrigation+first['annual_rain_mm']*years)
        labor=sum(e['labor_h_per_ha'] for e in events)/years
        computed.append({'id':id,'area_ha':area,'crop_events':converted,'revenue_per_ha_period':revenue,'cost_per_ha_period':cost,'irrigation_mm_period':irrigation,'recharge_mm_period':recharge,
                         'margin':(revenue-cost)/years,'water':(irrigation-recharge)/years,'labor':labor,'labor_total_h_year':labor*area})
    def dominates(a,b):return a['margin']>=b['margin'] and a['water']<=b['water'] and (a['margin']>b['margin'] or a['water']<b['water'])
    def fronts(rows):
        remaining=list(rows);result=[]
        while remaining:
            front=[r for r in remaining if not any(dominates(o,r) for o in remaining)]
            result.append([r['id'] for r in front]);remaining=[r for r in remaining if r not in front]
        return result
    feasible=[r for r in computed if r['labor_total_h_year']<=labor_cap_h]
    ideal=[max(r['margin'] for r in feasible),min(r['water'] for r in feasible)] if feasible else None
    ranges=[max(r['margin'] for r in feasible)-min(r['margin'] for r in feasible),max(r['water'] for r in feasible)-min(r['water'] for r in feasible)] if feasible else None
    distances={}
    for r in feasible:
        d=[abs(v-q)/span if span else 0 for v,q,span in zip([r['margin'],r['water']],ideal,ranges)]
        distances[r['id']]={'d':d,'MIDIP':math.sqrt(sum(v*v for v in d)),'HDIP':statistics.stdev(d)}
    return {'scope':'SYNTHETIC coherent input-to-output walkthrough; two-objective teaching example, no author-data reproduction',
            'author_result_reproduced':False,'objectives':['margin:max','water:min'],
            'units':{'margin':'USD/ha/year','water':'mm/year','labor':'h/ha/year','labor_cap':'h/year for each farm'},
            'constraint_role':'Teaching/research-transfer extension; not Liang2022 observational sampling',
            'rows':computed,'labor_cap_h_year':labor_cap_h,'observed_fronts_without_added_cap':fronts(computed),
            'feasible':[r['id'] for r in feasible],'excluded':[r['id'] for r in computed if r not in feasible],
            'fronts':fronts(feasible),'ideal':ideal,'ranges':ranges,'distances':distances}


def test():
    r=calculate();rows={x['id']:x for x in r['rows']}
    assert [rows[k]['margin'] for k in 'ABCD']==[1900,1700,2200,2600]
    assert [rows[k]['water'] for k in 'ABCD']==[260,280,300,180]
    assert [rows[k]['labor'] for k in 'ABCD']==[74,80,85,140]
    assert r['observed_fronts_without_added_cap'][0]==['D'] and r['fronts']==[['A','C'],['B']]
    assert r['excluded']==['D'] and r['ideal']==[2200,260] and r['ranges']==[500,40]
    assert r['distances']['A']['d']==[0.6,0] and math.isclose(r['distances']['A']['HDIP'],math.sqrt(0.18))
    assert r['distances']['C']['MIDIP']==1 and math.isclose(r['distances']['C']['HDIP'],math.sqrt(0.5))
    assert calculate(labor_cap_h=160)['fronts'][0]==['D']
    empty=calculate(labor_cap_h=0);assert empty['fronts']==[] and empty['ideal'] is None and empty['distances']=={}
    one=calculate(labor_cap_h=74);assert one['feasible']==['A'] and one['ranges']==[0,0] and one['distances']['A']['MIDIP']==0
    source=read_records();changed=[dict(x) for x in source];changed[0]['cost_usd_per_ha']=1200
    assert calculate(changed)['rows'][0]['margin']==1700
    invalid=[dict(x) for x in source];invalid[0]['area_ha']=0
    for bad in [invalid,source+[source[0]]]:
        try:calculate(bad)
        except ValueError:pass
        else:raise AssertionError('Invalid data accepted')
    for cap in [float('nan'),-1]:
        try:calculate(labor_cap_h=cap)
        except ValueError:pass
        else:raise AssertionError('Invalid cap accepted')
    json.dumps(r,allow_nan=False)
    return {'passed':True,'scope':'Coherent synthetic pipeline, constraints, fronts, distances and input validation'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,default=DATA);p.add_argument('--labor-cap',type=float,default=100);p.add_argument('--test',action='store_true');a=p.parse_args()
    print(json.dumps(test() if a.test else calculate(read_records(a.input),a.labor_cap),ensure_ascii=False,indent=2,allow_nan=False))
