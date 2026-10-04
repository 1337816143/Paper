#!/usr/bin/env python3
"""Seven independent synthetic worked calculations using Liang 2022 main Eqs 1–8.

Not author data, a jointly calibrated farm, or an implementation of the missing
supplementary electricity/N-loss/GHG/dose-response equations. Missing factors
are not invented. DEY coefficients 3.17/3.35 and recharge 0.2 are in the article;
all other example inputs are invented or explicitly already-estimated outputs.
"""
import argparse,json,math


def calculate():
    area=0.6
    revenue=6*300+8*250
    gm=revenue-(1000+900)
    dey=6*3.17+8*3.35
    activities={
        'wheat':[(2,3),(1,8),(3,1.5),(3,4),(1,5),(1,10)],
        'maize':[(1,3),(0,8),(3,1.5),(1,4),(1,5),(1,12)],
    }
    labor={crop:sum(n*h for n,h in rows) for crop,rows in activities.items()}
    irrigation=300+150
    recharge=0.2*(500+irrigation)
    gwd=irrigation-recharge
    n_paths={'wheat':[20,25,2],'maize':[15,20,1.5]}
    n_seasons={crop:sum(values) for crop,values in n_paths.items()}
    nl=sum(n_seasons.values())
    ghg_emi=sum([2.0,0.8,0.2,1.0]);q_soc=1.5;ghg_net=ghg_emi-q_soc
    dose_groups={'insecticide':2+1,'herbicide':1+1,'fungicide':1+0}
    pu=sum(dose_groups.values())
    return {
        'scope':'Independent synthetic arithmetic examples; not a jointly calibrated farm or author reproduction',
        'author_result_reproduced':False,
        'original_coefficients':{'wheat_GCal_per_Mg':3.17,'maize_GCal_per_Mg':3.35,'Liang2022_recharge_alpha':0.2},
        'missing_original_tables':['Table S2 original prices','Table S3 operation labor constants'],
        'missing_original_submodels':['electricity_to_irrigation','fertilizer_to_N_pathways','complete_GHG_factors_and_SOC','nonstandard_pesticide_doses'],
        'gm':{'formula':'sum(Y_i * PR_i - VC_i)','revenue':revenue,'costs':1900,'per_ha_year':gm,'total_0_6_ha':gm*area,'unit':'USD'},
        'dey':{'formula':'sum(Y_i * E_i)','wheat':6*3.17,'maize':8*3.35,'per_ha_year':dey,'total_0_6_ha':dey*area,'kcal_per_ha_year':dey*1e6,'unit':'GCal'},
        'labor':{'formula':'sum_i(sum_j(L_ji * N_ji))','activities_synthetic':activities,'season_totals':labor,'per_ha_year':sum(labor.values()),'total_0_6_ha':sum(labor.values())*area,'unit':'h'},
        'gwd':{'formula':'sum(IR_i) - alpha * (P + sum(IR_i))','irrigation_mm':irrigation,'recharge_mm':recharge,'per_year_mm':gwd,'m3_per_ha_year':gwd*10,'m3_for_0_6_ha_year':gwd*10*area},
        'nl':{'formula':'sum_i(NLNH3_i + NLNO3_i + NLN2O_i)','synthetic_path_outputs':n_paths,'season_totals':n_seasons,'per_ha_year':nl,'total_0_6_ha':nl*area,'unit':'kg N'},
        'ghg':{'formula':'GHGemi - QSOC','synthetic_already_converted_components':[2.0,0.8,0.2,1.0],'emissions':ghg_emi,'soil_C_sequestration_CO2eq':q_soc,'net_per_ha_year':ghg_net,'kg_net_per_ha_year':ghg_net*1000,'total_0_6_ha':ghg_net*area,'unit':'Mg CO2-eq'},
        'pu':{'formula':'IUtotal + HUtotal + FUtotal','annual_groups':dose_groups,'annual_total':pu,'unit':'doses/year','area_scaling':'Do not multiply this frequency-like indicator by area'},
        'separate_unit_examples':{'NH3_to_N':17*14/17,'NO3_to_N':62*14/62,'N2O_to_N':4.4*28/44,'Mg_C_to_Mg_CO2':0.3*44/12,'spray_liquid_L_per_ha':20*15},
    }


def test():
    r=calculate()
    expected=[(r['gm']['per_ha_year'],1900),(r['gm']['total_0_6_ha'],1140),
              (r['dey']['per_ha_year'],45.82),(r['dey']['total_0_6_ha'],27.492),
              (r['labor']['season_totals']['wheat'],45.5),(r['labor']['season_totals']['maize'],28.5),
              (r['labor']['per_ha_year'],74),(r['labor']['total_0_6_ha'],44.4),
              (r['gwd']['recharge_mm'],190),(r['gwd']['per_year_mm'],260),
              (r['gwd']['m3_for_0_6_ha_year'],1560),(r['nl']['per_ha_year'],83.5),
              (r['nl']['total_0_6_ha'],50.1),(r['ghg']['net_per_ha_year'],2.5),
              (r['ghg']['total_0_6_ha'],1.5),(r['pu']['annual_total'],6),
              (r['separate_unit_examples']['N2O_to_N'],2.8),(r['separate_unit_examples']['Mg_C_to_Mg_CO2'],1.1)]
    for actual,target in expected:assert math.isclose(actual,target,rel_tol=1e-12),(actual,target)
    assert math.isclose(r['gwd']['per_year_mm'],0.8*450-0.2*500)
    assert set(r['pu']['annual_groups'])=={'insecticide','herbicide','fungicide'}
    assert not r['author_result_reproduced'] and len(r['missing_original_submodels'])==4
    return {'passed':True,'scope':'Seven main-text arithmetic chains and independent dimensional conversions only'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--test',action='store_true');a=p.parse_args()
    print(json.dumps(test() if a.test else calculate(),ensure_ascii=False,indent=2))
