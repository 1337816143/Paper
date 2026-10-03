#!/usr/bin/env python3
"""Three auditable, synthetic teaching exercises; Python standard library only.

These fixtures are NOT author data, FarmDESIGN/FarmM3 implementations or Hainan
predictions. Units and boundaries are part of each fixture, not inferred.

python model_reasoning_lab.py --case units
python model_reasoning_lab.py --case boundary
python model_reasoning_lab.py --case robustness
python model_reasoning_lab.py --test
"""
from __future__ import annotations
import argparse
import json
import math
import unittest


def finite(values, *, nonnegative=False):
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool)
               and math.isfinite(x) and (not nonnegative or x >= 0) for x in values):
        raise ValueError('Finite numeric values required; quantities must respect their sign domain')


def farm_plan(grain_ha=2, forage_ha=2, animals=3, feed_import_kg_DM_year=0):
    """Fixed coefficients and annual, constant homogeneous herd for this toy only."""
    finite([grain_ha, forage_ha, animals, feed_import_kg_DM_year], nonnegative=True)
    feed_supply = 3000 * forage_ha + feed_import_kg_DM_year
    feed_need = 2000 * animals
    labour = 120 * grain_ha + 80 * forage_ha + 200 * animals
    margins = {'land_ha': 4 - grain_ha - forage_ha,
               'feed_kg_DM_year': feed_supply - feed_need,
               'labour_h_year': 1100 - labour}
    return {'inputs': {'grain_ha': grain_ha, 'forage_ha': forage_ha,
                       'constant_animals_head': animals,
                       'feed_import_kg_DM_year': feed_import_kg_DM_year},
            'feed_supply_kg_DM_year': feed_supply, 'feed_need_kg_DM_year': feed_need,
            'labour_h_year': labour, 'constraint_margins': margins,
            'feasible_under_toy_constraints': all(x >= 0 for x in margins.values())}


def units_case():
    return {'units': {'area': 'ha', 'herd': 'constant head during year',
                     'yield': 'kg DM/(ha year)', 'feed_need': 'kg DM/(head year)',
                     'labour_crop': 'h/(ha year)', 'labour_animal': 'h/(head year)'},
            'baseline': farm_plan(), 'extra_animal': farm_plan(animals=4),
            'extra_animal_with_feed_import': farm_plan(animals=4, feed_import_kg_DM_year=2000),
            'omitted': ['feed quality/energy/protein', 'procurement labour', 'seasonal peaks',
                        'feed losses', 'dynamic herd and production responses']}


def efficiency_percent(outputs, inputs):
    finite([outputs, inputs], nonnegative=True)
    return None if inputs == 0 else outputs / inputs * 100


def boundary_case():
    # Every flow below is a cumulative kg N during the same year. Stocks are
    # end minus beginning kg N. Receiving/exporting farms count a transfer once
    # at their own gates; the combined system cancels BOTH internal directions.
    a = {'external_inputs': 100, 'received_manure': 30, 'external_products': 40,
         'exported_feed_to_b': 20, 'stock_change': 10}
    b = {'external_inputs': 70, 'received_feed': 20, 'external_products': 30,
         'exported_manure_to_a': 30, 'stock_change': 5}
    a_inputs = a['external_inputs'] + a['received_manure']
    b_inputs = b['external_inputs'] + b['received_feed']
    a_outputs = a['external_products'] + a['exported_feed_to_b']
    b_outputs = b['external_products'] + b['exported_manure_to_a']
    a_residual = a_inputs - a_outputs - a['stock_change']
    b_residual = b_inputs - b_outputs - b['stock_change']
    internal = a['exported_feed_to_b'] + b['exported_manure_to_a']
    system_inputs = a_inputs + b_inputs - internal
    system_outputs = a_outputs + b_outputs - internal
    stock = a['stock_change'] + b['stock_change']
    return {'unit': 'kg N accumulated over the same year; stock change in kg N',
            'farm_a': a, 'farm_b': b,
            'farm_gate_inputs': [a_inputs, b_inputs],
            'farm_gate_outputs_including_manure': [a_outputs, b_outputs],
            'residuals': [a_residual, b_residual], 'internal_transfer_cancelled': internal,
            'combined_external_inputs': system_inputs,
            'combined_external_outputs': system_outputs,
            'combined_stock_change': stock,
            'combined_residual': system_inputs - system_outputs - stock,
            'gate_output_input_efficiency_percent': [efficiency_percent(a_outputs, a_inputs),
                                                     efficiency_percent(b_outputs, b_inputs)],
            'combined_efficiency_percent': efficiency_percent(system_outputs, system_inputs),
            'b_animal_product_only_percent': efficiency_percent(b['external_products'], b_inputs),
            'warning': 'Residual is not measured leaching. Output categories follow the cited Qu definition; all numbers are synthetic.'}


def compare_profits(rows, probabilities=None):
    """Rows are fixed decisions; columns are the same known, feasible scenarios.

    Regret is for a maximized scalar profit only. Feasibility must be established
    separately; impossible actions are not valid benchmark alternatives.
    """
    if not rows or not rows[0] or any(len(r) != len(rows[0]) for r in rows):
        raise ValueError('A non-empty rectangular decision-by-scenario matrix is required')
    for r in rows:
        finite(r)
    if probabilities is not None:
        finite(probabilities, nonnegative=True)
        if len(probabilities) != len(rows[0]) or not math.isclose(sum(probabilities), 1):
            raise ValueError('Explicit probabilities must match scenarios and sum to one')
    best = [max(r[s] for r in rows) for s in range(len(rows[0]))]
    regrets = [[best[s] - value for s, value in enumerate(r)] for r in rows]
    return {'profits': rows, 'scenario_best': best, 'regrets': regrets,
            'maximum_regret': [max(r) for r in regrets], 'worst_profit': [min(r) for r in rows],
            'probabilities': probabilities,
            'expected_profit': None if probabilities is None else
                [sum(x * p for x, p in zip(r, probabilities)) for r in rows],
            'perfect_information_expected_benchmark': None if probabilities is None else
                sum(x * p for x, p in zip(best, probabilities))}


def robustness_case():
    profits = compare_profits([[120, -20], [80, 40]], [.5, .5])
    capacity = [1100, 1000]
    demands = [1100, 950]
    margins = [[available - demand for available in capacity] for demand in demands]
    return {'fixed_feasible_decision_profit_example': profits,
            'separate_labour_feasibility_example': {
                'unit': 'h/year', 'capacity': capacity, 'fixed_plan_demands': demands,
                'margins': margins, 'feasible_by_scenario': [[x >= 0 for x in r] for r in margins]},
            'warning': 'Equal probabilities are an explicit teaching assumption. Profit and labour examples are separate; no free recourse or foresight is assumed.'}


CASES = {'units': units_case, 'boundary': boundary_case, 'robustness': robustness_case}


class Tests(unittest.TestCase):
    def test_baseline_units_and_feasibility(self):
        r = farm_plan()
        self.assertEqual(r['constraint_margins'], {'land_ha': 0, 'feed_kg_DM_year': 0, 'labour_h_year': 100})
        self.assertTrue(r['feasible_under_toy_constraints'])

    def test_import_only_repairs_feed_constraint(self):
        r = farm_plan(animals=4)
        self.assertEqual(r['constraint_margins']['feed_kg_DM_year'], -2000)
        r = farm_plan(animals=4, feed_import_kg_DM_year=2000)
        self.assertEqual(r['constraint_margins']['feed_kg_DM_year'], 0)
        self.assertEqual(r['constraint_margins']['labour_h_year'], -100)
        self.assertFalse(r['feasible_under_toy_constraints'])

    def test_zero_and_invalid_inputs(self):
        self.assertTrue(farm_plan(0, 0, 0, 0)['feasible_under_toy_constraints'])
        for value in [-1, float('nan'), float('inf'), True]:
            with self.assertRaises(ValueError):
                farm_plan(animals=value)

    def test_boundary_cancellation_and_conservation(self):
        r = boundary_case()
        self.assertEqual(r['residuals'], [60, 25])
        self.assertEqual(r['internal_transfer_cancelled'], 50)
        self.assertEqual(r['combined_external_inputs'], 170)
        self.assertEqual(r['combined_external_outputs'], 70)
        self.assertEqual(r['combined_stock_change'], 15)
        self.assertEqual(r['combined_residual'], sum(r['residuals']))
        self.assertEqual(r['combined_external_inputs'], r['combined_external_outputs'] + r['combined_stock_change'] + r['combined_residual'])

    def test_efficiency_definition_and_boundary(self):
        r = boundary_case()
        self.assertAlmostEqual(r['gate_output_input_efficiency_percent'][1], 200 / 3)
        self.assertAlmostEqual(r['b_animal_product_only_percent'], 100 / 3)
        self.assertAlmostEqual(r['combined_efficiency_percent'], 700 / 17)
        self.assertNotAlmostEqual(sum(r['gate_output_input_efficiency_percent']) / 2, r['combined_efficiency_percent'])
        self.assertIsNone(efficiency_percent(0, 0))

    def test_fixed_plans_regret_and_no_foresight(self):
        r = compare_profits([[120, -20], [80, 40]], [.5, .5])
        self.assertEqual(r['expected_profit'], [50, 60])
        self.assertEqual(r['regrets'], [[0, 60], [40, 0]])
        self.assertEqual(r['maximum_regret'], [60, 40])
        self.assertEqual(r['worst_profit'], [-20, 40])
        self.assertEqual(r['perfect_information_expected_benchmark'], 80)
        self.assertNotIn(r['scenario_best'], r['profits'])

    def test_no_probability_no_expected_profit_claim(self):
        r = compare_profits([[120, -20], [80, 40]])
        self.assertIsNone(r['expected_profit'])
        self.assertIsNone(r['perfect_information_expected_benchmark'])

    def test_invalid_scenario_matrix_and_probability(self):
        for rows, p in [([], None), ([[]], None), ([[1], [1, 2]], None),
                        ([[float('nan')]], None), ([[1, 2]], [.5]),
                        ([[1, 2]], [.6, .6]), ([[1, 2]], [-.5, 1.5])]:
            with self.assertRaises(ValueError):
                compare_profits(rows, p)

    def test_feasibility_separate_from_profit(self):
        r = robustness_case()['separate_labour_feasibility_example']
        self.assertEqual(r['margins'], [[0, -100], [150, 50]])
        self.assertEqual(r['feasible_by_scenario'], [[True, False], [True, True]])

    def test_serialization(self):
        for fn in CASES.values():
            json.dumps(fn(), allow_nan=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=sorted(CASES))
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()
    if args.test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        raise SystemExit(not result.wasSuccessful())
    if not args.case:
        parser.error('Choose --case NAME or --test')
    print(json.dumps({'evidence_status': 'synthetic teaching, NOT author data or model reproduction',
                      'case': args.case, 'result': CASES[args.case]()}, ensure_ascii=False, indent=2, allow_nan=False))
