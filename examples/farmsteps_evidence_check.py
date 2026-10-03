#!/usr/bin/env python3
"""Published-table arithmetic checks, NOT FarmSTEPS or a result reproduction.
Sources: Liang et al. DOI 10.1007/s13593-026-01097-8, PDF pp.10-12;
supplement Table S1 p.5. Values were visually verified 2026-10-03.
No choice of a corrected author parameter or Hainan coefficient is made here.
"""
import argparse
import json
import math
import unittest

SOURCE = 'https://doi.org/10.1007/s13593-026-01097-8'

def audit():
    crops = {
        'winter_wheat': {'margin_usd_ha': 1229, 'irrigation_mm': 296, 'labour_h_ha': 160},
        'summer_maize': {'margin_usd_ha': 1370, 'irrigation_mm': 166, 'labour_h_ha': 87},
    }
    margin = sum(c['margin_usd_ha'] for c in crops.values())
    irrigation = sum(c['irrigation_mm'] for c in crops.values())
    rainfall, recharge_fraction = 430, 0.02
    depletion = irrigation - recharge_fraction * (irrigation + rainfall)
    return {
        'scope': 'Published-table arithmetic only; NOT the original model or validated correction',
        'source': SOURCE,
        'published_inputs': crops,
        'labour': {
            'literal_total_limit_h_period': 520,
            'wheat_area_lower_bound_ha': 8,
            'wheat_area_rule': '>8 ha',
            'wheat_labour_strictly_greater_than_h': 8 * crops['winter_wheat']['labour_h_ha'],
            'status': 'Literal total-hours interpretation conflicts; area-normalized interpretation remains unconfirmed',
        },
        'naive_annual_pair_vs_reported_baseline': {
            'margin_table_sum_usd_ha': margin,
            'margin_reported_usd_ha_year': 2303,
            'irrigation_table_sum_mm': irrigation,
            'rainfall_mm_year': rainfall,
            'recharge_fraction': recharge_fraction,
            'depletion_from_direct_pair_mm': round(depletion, 2),
            'depletion_reported_mm_year': 284,
            'status': 'Unresolved input/version/boundary/period mapping; no corrected value inferred',
        },
        'suitable_plots': {
            'crops': ['peanut', 'garlic'],
            'paragraph_3_2_1': [1, 2],
            'table_1': [4, 5],
            'status': 'Unresolved; neither list selected as authoritative configuration',
        },
        'original_model_run': False,
        'original_plan_counts_reproduced': False,
        'hainan_parameter_recommendation': False,
    }

class EvidenceChecks(unittest.TestCase):
    def test_public_table_arithmetic(self):
        a = audit()['naive_annual_pair_vs_reported_baseline']
        self.assertEqual(a['margin_table_sum_usd_ha'], 2599)
        self.assertEqual(a['irrigation_table_sum_mm'], 462)
        self.assertTrue(math.isclose(a['depletion_from_direct_pair_mm'], 444.16))
    def test_no_silent_parameter_repair(self):
        a = audit()
        self.assertGreater(a['labour']['wheat_labour_strictly_greater_than_h'], 520)
        self.assertNotEqual(a['suitable_plots']['paragraph_3_2_1'], a['suitable_plots']['table_1'])
        self.assertFalse(a['original_model_run'])
        self.assertFalse(a['original_plan_counts_reproduced'])
        self.assertFalse(a['hainan_parameter_recommendation'])

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--test', action='store_true'); args = p.parse_args()
    if args.test:
        unittest.main(argv=['farmsteps_evidence_check'], verbosity=2)
    else:
        print(json.dumps(audit(), ensure_ascii=False, indent=2))
