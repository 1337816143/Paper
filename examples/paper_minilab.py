#!/usr/bin/env python3
"""Paper Lab mechanisms, Python standard library only.
Exercise inputs are synthetic except the explicitly labeled Table 3 arithmetic
check. These are NOT the authors' input data, software or model reproductions.
python paper_minilab.py --case liang-2023
python paper_minilab.py --test
"""
from __future__ import annotations
import argparse,itertools,json,math,statistics,unittest
from typing import Iterable

def dominates(a:Iterable[float],b:Iterable[float])->bool:
    a,b=list(a),list(b)
    if len(a)!=len(b) or not a or not all(math.isfinite(x) for x in a+b):raise ValueError('Finite equal-width minimization vectors required')
    return all(x<=y for x,y in zip(a,b)) and any(x<y for x,y in zip(a,b))
def nondominated(rows):
    if not rows:return []
    width=len(rows[0])
    if not width or any(len(r)!=width for r in rows):raise ValueError('Rectangular matrix required')
    return [i for i,r in enumerate(rows) if not any(i!=j and dominates(q,r) for j,q in enumerate(rows))]
def efficiency(rows):
    K=len(rows[0]);front=set(nondominated(rows));scores=[None]*len(rows)
    for k in range(1,K+1):
        passing=front.copy()
        for cols in itertools.combinations(range(K),k):passing &= set(nondominated([[r[c] for c in cols] for r in rows]))
        for i in passing:
            if scores[i] is None:scores[i]=k
    return scores

def distance(distances):
    if not distances or any(not math.isfinite(x) or x<0 for x in distances):raise ValueError('Non-negative finite distances required')
    return {'MIDIP':math.sqrt(sum(x*x for x in distances)), 'HDIP':statistics.stdev(distances) if len(distances)>1 else 0}
def pareto_case():
    # profit and energy negated; remaining five objectives minimized.
    raw=[['A',100,12,30,40,8,4,2],['B',90,10,40,50,9,5,3],['C',120,11,35,60,10,6,4],['D',95,12,20,30,7,3,2]]
    rows=[[-r[1],-r[2],*r[3:]] for r in raw]
    return {'input':raw,'columns':['id','profit','energy','labour','water','N_loss','GHG','dose'],'first_front':[raw[i][0] for i in nondominated(rows)],'balanced_distance':distance([.2,.2,.2]),'uneven_distance':distance([0,0,.5]),'warning':'Seven toy indicators are not the paper input matrix; no original 56/9 counts claimed.'}
def sequence_case():
    acts={'grain':{'profit':8,'labour':2,'water':5},'legume':{'profit':7,'labour':3,'water':2},'vegetable':{'profit':14,'labour':7,'water':6}}
    sequences=[s for s in itertools.product(acts,repeat=3) if all(s[i]!=s[i+1] for i in range(2))]
    plans=[];rejected=None
    for a,b in itertools.product(sequences,repeat=2):
        labour=[acts[x]['labour']+acts[y]['labour'] for x,y in zip(a,b)]
        if max(labour)>10:
            rejected=rejected or {'A':a,'B':b,'labour':labour};continue
        plans.append({'A':a,'B':b,'labour':labour,'profit':sum(acts[x]['profit'] for x in a+b),'water':sum(acts[x]['water'] for x in a+b)})
    front=nondominated([[-p['profit'],p['water']] for p in plans])
    return {'activities':acts,'sequences_per_plot':len(sequences),'combinations':len(sequences)**2,'feasible':len(plans),'non_dominated':len(front),'rejected_local_feasible_combination':rejected,'first_plan':plans[0],'warning':'Not FarmSTEPS/ROTAT code or its published case study.'}
def weighted_case():
    areas=[1,3];water=[100,200];total=sum(a*w for a,w in zip(areas,water))
    return {'areas_ha':areas,'water_per_ha':water,'total_water':total,'water_per_ha_area_weighted':total/sum(areas),'incorrect_equal_plot_average':statistics.mean(water),'annual_labour':[200,150],'MCI':[2,1],'labour_per_crop_cycle':[100,150]}
def qsort_case():
    a=[1]*2+[2]*4+[3]*8+[4]*4+[5]*2;b=[6-x for x in a]
    def valid(r):return [r.count(i) for i in range(1,6)]==[2,4,8,4,2]
    def corr(x,y):
        xx=[v-statistics.mean(x) for v in x];yy=[v-statistics.mean(y) for v in y]
        return sum(a*b for a,b in zip(xx,yy))/math.sqrt(sum(v*v for v in xx)*sum(v*v for v in yy))
    return {'sort_a':a,'sort_b':b,'capacity':[2,4,8,4,2],'both_valid':valid(a) and valid(b),'correlation':corr(a,b),'not_run':'PCA, varimax, factor extraction or any inference about the 327 original participants.'}
def join_case():
    crop=[{'id':'c1','margin':100},{'id':'c2','margin':200},{'id':'c3','margin':300}];manure=[{'id':'m1','N':10},{'id':'m2','N':20}]
    naive=list(itertools.product(crop,manure))
    return {'naive_rows':len(naive),'incorrect_margin':sum(a['margin'] for a,b in naive),'incorrect_N':sum(b['N'] for a,b in naive),'correct_margin':sum(r['margin'] for r in crop),'correct_N':sum(r['N'] for r in manure),'rule':'Aggregate each table at its actual unit before joining; keep identifiers and periods.'}
def farm_case():
    plans=[]
    for grain,forage,animals in itertools.product(range(5),range(5),range(7)):
        feed=3*forage;need=2*animals;labour=2*grain+forage+animals
        if grain+forage<=4 and feed>=need and labour<=10:
            plans.append({'grain_ha':grain,'forage_ha':forage,'animals':animals,'feed':feed,'need':need,'labour':labour,'margin':5*grain+3*animals-forage})
    return {'feasible_count':len(plans),'highest_toy_margin':max(plans,key=lambda x:x['margin']),'verification':all(p['grain_ha']+p['forage_ha']<=4 and p['feed']>=p['need'] and p['labour']<=10 for p in plans),'not_run':'FarmDESIGN processes, P-MODE or the Dutch 96ha farm.'}
def spatial_case():
    def edges(cells):
        s=set(cells);return sum((r+1,c) in s for r,c in s)+sum((r,c+1) in s for r,c in s)
    a=[(0,0),(0,1),(0,2)];b=[(0,0),(1,1),(2,2)]
    return {'continuous':a,'dispersed':b,'area_each':3,'shared_edges':[edges(a),edges(b)],'warning':'Adjacency count is a toy spatial indicator, not validated ecological connectivity.'}
def coding_case():
    rows=[{'study':'a','risk':'reported'},{'study':'b','risk':'explicitly_absent'},{'study':'c','risk':'not_reported'}]
    return {'coding':rows,'counts':{k:sum(x['risk']==k for x in rows) for k in ['reported','explicitly_absent','not_reported']},'warning':'Not reported is NOT evidence of not performed. No original review percentages estimated.'}
def qualitative_case():
    return {'observations':['A farmer reports holding spare fodder.','Income increased after a shock.'],'candidate_mechanism':'Spare fodder may relax a shortage constraint.','causal_gap':'Need comparator, timing, competing explanations and evidence that the shock itself improved outcomes.','not_run':'No numeric antifragility index or qualitative original-data reproduction.'}
def systems_case():
    return {'nodes':['irrigation','yield','feed','animals','total_water'],'edges':[{'from':'irrigation','to':'yield','status':'hypothesis to verify'},{'from':'yield','to':'feed','status':'depends on product use'},{'from':'feed','to':'animals','status':'depends on resource and market limits'},{'from':'animals','to':'total_water','status':'requires coefficients and boundary'}],'warning':'A teaching causal sketch is not an estimated structural causal model.'}
def nutrient_case():
    # All model inputs below are synthetic. The separate Table 3 check is an
    # arithmetic reading of published values, not a NUFER reimplementation.
    lower=80
    upper={'groundwater':110,'ammonia':95,'runoff':90}
    tightest=min(upper,key=upper.get)
    crop_external=120;livestock_external=50;manure_transfer=30
    crop_receipts=crop_external+manure_transfer
    livestock_receipts=livestock_external
    system_external=crop_receipts+livestock_receipts-manure_transfer
    printed_s5_p_out=[1.2,0.1,23.4,19.7,1.9]
    return {'synthetic_lower':lower,'synthetic_environmental_upper':upper,'tightest':tightest,
            'feasible_interval':[lower,upper[tightest]],'crop_receipts':crop_receipts,
            'livestock_receipts':livestock_receipts,'internal_manure_transfer':manure_transfer,
            'system_external_after_internal_cancellation':system_external,
            'published_table_3_s5_component_sum_Gg':round(sum(printed_s5_p_out),1),
            'published_table_3_s5_printed_total_Gg':68,
            'warning':'Toy interval and flows are synthetic; Table 3 arithmetic check is not the authors NUFER model or a corrected paper result.'}
def thesis_case(kind):
    if kind=='cheng':return {'stages':['perceived system','relative priorities','landscape options'],'interface_to_verify':['Q factors are not automatic objective weights','Check final chapter mapping and constraints'],'unavailable':'Complete original chapter and input/code not obtained.'}
    if kind=='xu':return {'scenarios':[{'configuration_changed':c,'management_changed':m} for c,m in itertools.product([False,True],repeat=2)],'evaluated_indicators':8,'optimized_objectives':7,'post_evaluated':'crop diversity','warning':'Scenario structure is a teaching reconstruction; original parameters and full numerical results are not reproduced.'}
    return {'stages':['observed farm cases','generated plot rotations','whole-farm temporal/spatial plans'],'new_information':['local farming records','rotation rules and activity inputs','land units, timeline and cross-plot limits'],'warning':'This teaching sequence is not a claim about unverified thesis chapter numbers.'}
CASES={
'liang-2022':pareto_case,'liang-2023':lambda:{'minimize_rows':[[1,1,1],[0,2,2],[2,0,2],[2,2,0]],'score':efficiency([[1,1,1],[0,2,2],[2,0,2],[2,2,0]])},
'farmsteps-2026':sequence_case,'cheng-2023':lambda:{'scores':[5,4,None],'mean_valid':4.5,'incorrect_zero_filled':3,'RDA_unit':'village','not_run':'RDA and original permutation tests'},'cheng-2025':qsort_case,
'xu-2024':weighted_case,'xu-data-2024':join_case,'farmdesign-2012':farm_case,'landscape-2018':spatial_case,'landscape-2007':spatial_case,
'novotny-2024':lambda:{'production':120,'need':100,'export':40,'production_self_sufficiency':1.2,'retained_supply_ratio':.8,'not_measured':'intake, distribution and nutritional health'},
'ditzler-2019':lambda:{'farm_gain':1000,'extra_hours':200,'potential_offfarm_wage':8,'opportunity_cost':1600,'net_opportunity_difference':-600,'assumption':'Off-farm work is actually available; not an observed household outcome.'},
'qu-2025':lambda:{'input':100,'product':40,'stock_change':10,'residual_loss':50,'storage_reduction':10,'downstream_increase_case_total_loss':50,'product_absorption_case_total_loss':40},
'breure-2024':coding_case,'toorop-2023':qualitative_case,'mixed-2026':systems_case,
'verdouw-2021':lambda:{'object':'plot-A','observations':[{'time':'2026-01-01','soil_water':20},{'time':'2026-01-02','soil_water':19}],'state_update_present':True,'process_model_present':False,'action_feedback_present':False,'warning':'A state history alone is not a complete digital twin.'},
'liang-thesis':lambda:thesis_case('liang'),'cheng-thesis':lambda:thesis_case('cheng'),'xu-thesis':lambda:thesis_case('xu'),
'groot-2017':lambda:{'levels':{'crop':'yield per hectare','household':'available food after sales and purchases','community':'total nutritional supply'},'warning':'The levels require different data and cannot stand in for each other.'},
'dong-2026':nutrient_case}
class Tests(unittest.TestCase):
    def test_pareto(self):self.assertEqual(pareto_case()['first_front'],['A','C','D'])
    def test_efficiency(self):self.assertEqual(efficiency([[1,1,1],[0,2,2],[2,0,2],[2,2,0]]),[2,3,3,3])
    def test_distances(self):self.assertAlmostEqual(distance([.2,.2,.2])['MIDIP'],math.sqrt(.12));self.assertEqual(distance([.8,.8,.8])['HDIP'],0)
    def test_duplicate(self):self.assertFalse(dominates([1,1],[1,1]))
    def test_invalid(self):
        with self.assertRaises(ValueError):dominates([float('nan')],[1])
    def test_qsort(self):self.assertTrue(qsort_case()['both_valid']);self.assertAlmostEqual(qsort_case()['correlation'],-1)
    def test_join(self):self.assertEqual(join_case()['naive_rows'],6);self.assertEqual(join_case()['correct_N'],30)
    def test_weight(self):self.assertEqual(weighted_case()['water_per_ha_area_weighted'],175)
    def test_farm(self):self.assertTrue(farm_case()['verification'])
    def test_spatial(self):self.assertEqual(spatial_case()['shared_edges'],[2,0])
    def test_sequence(self):self.assertEqual(sequence_case()['sequences_per_plot'],12);self.assertLess(sequence_case()['feasible'],144)
    def test_nutrient_boundary(self):
        result=nutrient_case()
        self.assertEqual(result['tightest'],'runoff')
        self.assertEqual(result['feasible_interval'],[80,90])
        self.assertEqual(result['system_external_after_internal_cancellation'],170)
        self.assertEqual(result['published_table_3_s5_component_sum_Gg'],46.3)
    def test_all_serializable(self):
        self.assertEqual(len(CASES),22)
        for f in CASES.values():json.dumps(f(),allow_nan=False)
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--case',choices=sorted(CASES));ap.add_argument('--test',action='store_true');ap.add_argument('--all',action='store_true');a=ap.parse_args()
    if a.test:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));raise SystemExit(not result.wasSuccessful())
    if not (a.case or a.all):ap.error('Choose --case ID, --all, or --test')
    out={i:{'data':'synthetic teaching fixture, NOT author data','result':CASES[i]()} for i in (sorted(CASES) if a.all else [a.case])};print(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False))
