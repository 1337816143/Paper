"""Tests of our teaching implementation; these do not validate the author's model."""
import sys
from dataclasses import replace
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"examples"))
from dong_boundary_lab import (Flow, Parameters, boundary_ledger, synthetic_flows,
                               forward, invert_ammonia, conditional_interval,
                               printed_table_audit, demonstration)


class LedgerTests(unittest.TestCase):
    def test_gross_and_net_boundaries(self):
        flows = synthetic_flows()
        crop = boundary_ledger(flows, {"crop"})
        animal = boundary_ledger(flows, {"livestock"})
        whole = boundary_ledger(flows, {"crop", "livestock"})
        self.assertEqual(crop["gross_receipts"],1960)
        self.assertEqual(animal["gross_receipts"],1050)
        self.assertEqual(whole["gross_receipts"],3010)
        self.assertEqual(whole["internal_receipts"],550)
        self.assertEqual(whole["external_receipts"],2460)
        self.assertEqual(whole["external_outputs_and_stock"],2460)
        for row in [crop, animal, whole]: self.assertEqual(row["residual"],0)

    def test_internal_transfer_does_not_create_external_input(self):
        flows = synthetic_flows()
        before = boundary_ledger(flows, {"crop", "livestock"})
        after = boundary_ledger(flows+[Flow("livestock","crop","extra_transfer",123)],
                                {"crop", "livestock"})
        self.assertEqual(before["external_receipts"],after["external_receipts"])
        self.assertEqual(after["gross_receipts"],before["gross_receipts"]+123)

    def test_external_input_does_not_disappear(self):
        result = boundary_ledger(synthetic_flows()+[Flow("outside","crop","extra",123)],
                                 {"crop","livestock"})
        self.assertEqual(result["residual"],123)

    def test_nue_uses_different_functional_outputs(self):
        r=demonstration()["synthetic_ledger"]
        self.assertAlmostEqual(r["crop_nue_gross_definition"],800/1960)
        self.assertAlmostEqual(r["livestock_nue"],200/1050)
        self.assertAlmostEqual(r["combined_nue"],700/2460)

    def test_invalid_flow_rejected(self):
        for value in [-1, float("inf"), float("nan"), True, "12"]:
            with self.assertRaises(ValueError): Flow("a","b","x",value)
        with self.assertRaises(ValueError): boundary_ledger([],set())


class BoundaryTests(unittest.TestCase):
    def test_exact_synthetic_output(self):
        r=invert_ammonia(10)
        expected={"managed_input":100, "fe_fix":75, "manure_straw":25,
                  "ammonia_emission":12.5, "deposition":10, "total_input":110,
                  "total_emission":17.5, "direct_runoff":5, "harvest":52.5,
                  "surplus":35, "leaching":24.5, "denitrification":10.5,
                  "subsurface_runoff":7.35, "groundwater":17.15,
                  "surface_water":12.35, "mass_balance_residual":0}
        for k,v in expected.items(): self.assertAlmostEqual(r[k],v,msg=k)

    def test_inverse_forward_roundtrip_parameter_grid(self):
        for share in [0.1,0.4,0.75,0.99]:
            for ag in [0.2,0.4,0.8]:
                for limit in [0,1,10,20]:
                    p=Parameters(share_fe_fix=share, agricultural_land_fraction=ag)
                    r=invert_ammonia(limit,p)
                    self.assertAlmostEqual(r["deposition"],limit)
                    self.assertAlmostEqual(r["ammonia_emission"],limit*.5/ag)
                    self.assertAlmostEqual(r["mass_balance_residual"],0)
                    self.assertAlmostEqual(r["leaching"],r["subsurface_runoff"]+r["groundwater"])

    def test_target_50_is_conditionally_feasible(self):
        r=conditional_interval(50,10)
        self.assertTrue(r["nonempty"])
        self.assertAlmostEqual(r["managed_input_lower"],50/.525)
        self.assertAlmostEqual(r["total_input_lower"],104.76190476190476)
        self.assertAlmostEqual(r["total_input_upper"],110)

    def test_target_55_is_conditionally_infeasible(self):
        r=conditional_interval(55,10)
        self.assertFalse(r["nonempty"])
        self.assertAlmostEqual(r["total_input_lower"],115.23809523809524)

    def test_exact_boundary_and_zero_target(self):
        self.assertTrue(conditional_interval(52.5,10)["nonempty"])
        self.assertTrue(conditional_interval(0,0)["nonempty"])

    def test_increasing_load_exceeds_deposition_limit(self):
        self.assertGreater(forward(101)["deposition"],10)

    def test_zero_emission_branch_has_no_finite_upper_bound(self):
        p=Parameters(nh3_ef_fe=0,nh3_ef_am=0)
        with self.assertRaises(ValueError): invert_ammonia(10,p)

    def test_negative_budget_rejected(self):
        p=Parameters(nh3_ef_fe=0,nh3_ef_am=0,
                     total_emission_ef_fe=1,total_emission_ef_am=1,
                     surface_runoff_fraction=.5)
        with self.assertRaises(ValueError): forward(10,p)

    def test_percent_and_singular_fraction_rejected(self):
        for kw in [dict(share_fe_fix=1),dict(share_fe_fix=0),
                   dict(agricultural_land_fraction=0),dict(nh3_fraction_of_deposition=0),
                   dict(harvest_fraction=60),dict(nh3_ef_fe=.5),
                   dict(leaching_fraction=float("nan"))]:
            with self.assertRaises(ValueError): Parameters(**kw)

    def test_invalid_targets_rejected(self):
        with self.assertRaises(ValueError): conditional_interval(-1,10)
        with self.assertRaises(ValueError): invert_ammonia(-1)
        with self.assertRaises(ValueError): forward(-1)
        with self.assertRaises(ValueError): conditional_interval(1,10,Parameters(harvest_fraction=0))


class SourceArithmeticTests(unittest.TestCase):
    def test_printed_table_sums(self):
        r=printed_table_audit()
        self.assertAlmostEqual(r["crop_input_component_sum"],314.1)
        self.assertAlmostEqual(r["livestock_input_component_sum"],169.8)
        self.assertAlmostEqual(r["consolidated_input_component_sum"],435.8)
        self.assertAlmostEqual(r["crop_less_deposition_and_fixation"],268.7)
        self.assertAlmostEqual(r["unexplained_difference"],.7)

    def test_correct_input_class_for_each_exceedance(self):
        e=printed_table_audit()["exceedance_percent"]
        self.assertAlmostEqual(e["source_EU_label_anthropogenic"],2.290076335877855)
        self.assertAlmostEqual(e["groundwater_total_input"],44.03669724770643)
        self.assertAlmostEqual(e["ammonia_total_input"],67.9144385026738)
        self.assertAlmostEqual(e["surface_water_total_input"],80.45977011494253)
        self.assertNotAlmostEqual(e["surface_water_total_input"],(268/174-1)*100)


if __name__ == "__main__": unittest.main(verbosity=2)
