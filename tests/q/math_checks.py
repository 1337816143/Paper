"""Independent invariants and consequential edge cases for the Q companion.

Run: python tests/q/math_checks.py
No R, browser, network or private data is used. These checks do NOT establish
R parity. Numerical bounds were fixed before reference execution: algebra and
scenario invariants use atol=1e-10, rtol=0; discrete decisions compare exactly.
"""

import csv
import hashlib
import itertools
import json
import math
import statistics
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import q_pipeline as q  # noqa: E402
from compare_r_reference import MANIFEST, best_alignment, compare_matrix  # noqa: E402

ATOL = 1e-10


class QMathChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = q.analyze()
        cls.reverse = q.analyze(scenario="reverse-p03")
        cls.data = np.array(cls.baseline["data"], dtype=float)
        cls.loadings = np.array(cls.baseline["rotated_loadings"])
        cls.flags = np.array(cls.baseline["flagged"])

    def close(self, actual, expected):
        np.testing.assert_allclose(actual, expected, atol=ATOL, rtol=0)

    def test_baseline_identity_and_result_contract(self):
        self.assertEqual(hashlib.sha256((ROOT / "examples/q_synthetic.csv").read_bytes()).hexdigest(), MANIFEST["input"]["sha256"])
        self.assertEqual(self.data.shape, (20, 10))
        for column in self.data.T:
            np.testing.assert_array_equal(np.sort(column), q.GRID)
        # Preserve every field from the audited unpublished prototype.
        original_fields = "schema author_data_reproduced source_paper numpy_version statements participants data nstat npeople grid_scores grid_counts input_orientation means sample_sd centered_sum_squares person_correlation all_eigenvalues retained_factors retained_factor_reason retained_eigenvectors unrotated_loadings rotation_matrix rotation_iterations rotation_setting rotated_loadings loading_threshold flagged unassigned weights weighted_totals weighted_total_means weighted_total_sample_sd statement_z factor_arrays ranks exact_ties array_slot_counts flagged_counts assumed_individual_reliability composite_reliability factor_standard_errors SED statement_comparisons boundaries".split()
        self.assertTrue(set(original_fields).issubset(self.baseline))
        self.assertFalse(self.baseline["author_data_reproduced"])
        for result in (self.baseline, self.reverse):
            json.dumps(result, allow_nan=False)

    def test_committed_scenarios_match_regenerated_results(self):
        fixture = json.loads((ROOT / "resources/q-results-v556.json").read_text(encoding="utf-8"))
        self.assertEqual(fixture["schema"], "paper.q.results.v1")
        self.assertEqual([item["id"] for item in fixture["scenarios"]], list(q.SCENARIOS))

        def same(saved, computed, path):
            # Float arithmetic permits the declared 1e-10 absolute variation.
            # Identities, text, settings, integer ranks/arrays, booleans, keys,
            # dimensions and all other metadata are compared exactly.
            self.assertIs(type(saved), type(computed), msg=path)
            if path.split(".")[-1] in {"ranks", "loading_threshold", "rotation_tolerance", "assumed_individual_reliability"}:
                self.assertEqual(saved, computed, msg=path)
            elif isinstance(computed, dict):
                self.assertEqual(saved.keys(), computed.keys(), msg=path)
                for key in computed:
                    same(saved[key], computed[key], f"{path}.{key}")
            elif isinstance(computed, list):
                self.assertEqual(len(saved), len(computed), msg=path)
                for index, (left, right) in enumerate(zip(saved, computed)):
                    same(left, right, f"{path}[{index}]")
            elif isinstance(computed, float):
                self.assertTrue(math.isfinite(saved) and math.isclose(saved, computed, abs_tol=ATOL, rel_tol=0), msg=f"{path}: {saved} != {computed}")
            else:
                self.assertEqual(saved, computed, msg=path)

        for item, computed in zip(fixture["scenarios"], (self.baseline, self.reverse)):
            same(item["result"], computed, item["id"])

    def test_correlation_independently_and_eigen_identity(self):
        corr = np.array(self.baseline["person_correlation"])
        self.close(corr, np.corrcoef(self.data, rowvar=False))
        # Hand-check P01/P05 from raw centered products, not the pipeline helper.
        a, b = self.data[:, 0], self.data[:, 4]
        numerator = sum((x - statistics.mean(a)) * (y - statistics.mean(b)) for x, y in zip(a, b))
        denominator = math.sqrt(sum((x - statistics.mean(a))**2 for x in a) * sum((y - statistics.mean(b))**2 for y in b))
        self.close(corr[0, 4], numerator / denominator)
        self.close(corr[0, 4], -11 / 24)
        eigen = np.array(self.baseline["all_eigenvalues"])
        vectors = np.array(self.baseline["retained_eigenvectors"])
        self.close(corr @ vectors, vectors * eigen[:2])
        self.close(vectors.T @ vectors, np.eye(2))
        for factor, person in enumerate(self.baseline["unrotated_axis_anchors"]):
            self.assertGreater(vectors[self.baseline["participants"].index(person), factor], 0)
        self.close(eigen.sum(), 10)
        self.assertGreater(eigen[2], 1)  # two factors are an explicit teaching choice

    def test_rotation_preserves_retained_approximation(self):
        unrotated = np.array(self.baseline["unrotated_loadings"])
        rotation = np.array(self.baseline["rotation_matrix"])
        self.close(rotation.T @ rotation, np.eye(2))
        self.close(unrotated @ rotation, self.loadings)
        self.close(unrotated @ unrotated.T, self.loadings @ self.loadings.T)
        corr = np.array(self.baseline["person_correlation"])
        self.assertGreater(np.max(abs(corr - self.loadings @ self.loadings.T)), 0.1)

    def test_varimax_against_independent_angle_search(self):
        normalized = self.loadings / np.linalg.norm(self.loadings, axis=1)[:, None]

        def objective(value):
            return float(np.sum(np.mean(value**4, axis=0) - np.mean(value**2, axis=0)**2))

        optimum = objective(normalized)
        # For two axes, all orthogonal rotations are covered by one angle plus
        # sign/reflection conventions, which do not change this objective.
        best_grid = max(objective(normalized @ np.array([[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]])) for theta in np.linspace(-math.pi / 4, math.pi / 4, 4001))
        self.assertGreaterEqual(optimum + 1e-10, best_grid)

    def test_reverse_person_recomputes_whole_chain(self):
        reversed_data = np.array(self.reverse["data"])
        expected = self.data.copy()
        expected[:, 2] = 6 - expected[:, 2]
        np.testing.assert_array_equal(reversed_data, expected)
        sign_matrix = np.eye(10)
        sign_matrix[2, 2] = -1
        self.close(self.reverse["person_correlation"], sign_matrix @ np.array(self.baseline["person_correlation"]) @ sign_matrix)
        self.assertFalse(np.array_equal(self.reverse["person_correlation"], self.baseline["person_correlation"]))
        self.close(self.reverse["all_eigenvalues"], self.baseline["all_eigenvalues"])
        self.close(self.reverse["rotated_loadings"], sign_matrix @ self.loadings)
        self.close(self.reverse["weights"], sign_matrix @ np.array(self.baseline["weights"]))
        self.assertTrue(self.reverse["flagged"][2][0])
        self.assertLess(self.reverse["weights"][2][0], 0)
        # (6-x)(-w) - xw = -6w, the SAME offset for each statement.
        offset = -6 * np.array(self.baseline["weights"])[2]
        self.close(np.array(self.reverse["weighted_totals"]) - self.baseline["weighted_totals"], np.broadcast_to(offset, (20, 2)))
        self.close(np.array(self.reverse["weighted_total_means"]) - self.baseline["weighted_total_means"], offset)
        for field in ("statement_z", "weighted_total_sample_sd", "composite_reliability", "factor_standard_errors", "SED"):
            self.close(self.reverse[field], self.baseline[field])
        for field in ("flagged", "ranks", "factor_arrays", "flagged_counts", "array_slot_counts"):
            self.assertEqual(self.reverse[field], self.baseline[field])
        self.assertEqual([row["distinguishing_p05"] for row in self.reverse["statement_comparisons"]], [row["distinguishing_p05"] for row in self.baseline["statement_comparisons"]])

    def test_weighted_z_independent_scalar_calculation(self):
        for factor in range(2):
            weights = [float(l) / (1 - float(l)**2) if flag else 0 for l, flag in zip(self.loadings[:, factor], self.flags[:, factor])]
            totals = [sum(score * weight for score, weight in zip(statement, weights)) for statement in self.data]
            zs = [(total - statistics.mean(totals)) / statistics.stdev(totals) for total in totals]
            self.close(np.array(self.baseline["statement_z"])[:, factor], zs)
            self.close(np.mean(zs), 0)
            self.close(statistics.stdev(zs), 1)
        # Positive nonzero scalar normalization of all totals leaves z unchanged.
        sums = np.array(self.baseline["weight_sums"])
        self.assertTrue(np.all(sums > 0))
        averages = np.array(self.baseline["weighted_totals"]) / sums
        self.close((averages - averages.mean(axis=0)) / averages.std(axis=0, ddof=1), self.baseline["statement_z"])

    def test_flags_reliability_and_two_levels_of_comparison(self):
        self.assertEqual(self.baseline["flagged_counts"], [5, 4])
        self.assertEqual(self.baseline["unassigned"], ["P10"])
        self.close(self.baseline["composite_reliability"], [20 / 21, 16 / 17])
        expected_sed = math.sqrt(1 / 21 + 1 / 17)
        self.close(self.baseline["SED"], expected_sed)
        for comparison in self.baseline["statement_comparisons"]:
            self.assertEqual(comparison["distinguishing_p05"], abs(comparison["difference"]) > 1.96 * expected_sed)
            self.assertEqual(comparison["distinguishing_p01"], abs(comparison["difference"]) > 2.576 * expected_sed)
        self.assertFalse(self.baseline["statement_comparisons"][3]["distinguishing_p05"])
        self.assertNotEqual(*self.baseline["factor_arrays"][3])  # S04: unequal grid scores, not significant
        self.assertTrue(self.baseline["statement_comparisons"][11]["distinguishing_p05"])
        self.assertFalse(self.baseline["statement_comparisons"][11]["distinguishing_p01"])

    def test_flag_rule_strict_boundaries_and_negative_pole(self):
        threshold = 1.96 / math.sqrt(20)
        flags, _ = q.automatic_flags([[threshold, 0], [.5, .5], [.6, .5], [-.8, .1], [.3, .2]], 20)
        self.assertEqual(flags.tolist(), [[False, False], [False, False], [True, False], [True, False], [False, False]])
        self.assertEqual(q.automatic_flags([[.65, .55, .5]], 20)[0].tolist(), [[False, False, False]])
        self.close(-.8 / (1 - .8**2), -20 / 9)

    def test_rank_ties_are_reported_not_invented(self):
        z = np.arange(20, dtype=float)
        z[1:3] = 1.5
        array, ranks, ties = q.rank_to_grid(z)
        self.close(ranks[1:3], [2.5, 2.5])
        self.assertEqual(int(sum(array == 1)), 3)
        self.assertEqual(ties, [{"statement_indices": [1, 2], "mean_rank": 2.5, "score": 1}])
        self.assertEqual(self.baseline["array_slot_counts"], [[2, 4, 8, 4, 2]] * 2)

    def test_factor_sign_and_statement_permutation_invariance(self):
        flipped = q.postprocess(self.data, self.loadings * [-1, 1], self.flags)
        self.close(flipped["statement_z"], np.array(self.baseline["statement_z"]) * [-1, 1])
        order = np.arange(19, -1, -1)
        permuted = q.postprocess(self.data[order], self.loadings, self.flags)
        self.close(permuted["statement_z"], np.array(self.baseline["statement_z"])[order])
        self.assertEqual(permuted["factor_arrays"], np.array(self.baseline["factor_arrays"])[order].tolist())

    def test_reject_inappropriate_factor_counts_and_shapes(self):
        for count in (0, 1, 3, True):
            with self.subTest(count=count), self.assertRaises(ValueError):
                q.analyze(nfactors=count)
        for shape in ((10, 1), (10, 3), (9, 2)):
            with self.subTest(shape=shape), self.assertRaises(ValueError):
                q.postprocess(self.data, np.full(shape, .5), np.ones(shape, dtype=bool))
        with self.assertRaises(ValueError):
            q.postprocess(self.data, self.loadings, self.flags.astype(int))
        with self.assertRaises(ValueError):
            q.postprocess(self.data, self.loadings, self.flags[:, :1])

    def test_reject_invalid_or_nonfinite_data_and_settings(self):
        for bad in (self.data.T, self.data[:, :9], self.data[:19], np.zeros_like(self.data)):
            with self.assertRaises(ValueError):
                q.validate_data(bad)
        for invalid in (np.nan, np.inf, -np.inf, 1.5, 9):
            bad = self.data.copy()
            bad[0, 0] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                q.validate_data(bad)
        with self.assertRaises(ValueError):
            q.analyze(scenario="swap-anything")
        for assumption in (0, 1, -1, np.nan):
            with self.assertRaises(ValueError):
                q.postprocess(self.data, self.loadings, self.flags, reliability_assumption=assumption)
        with self.assertRaises(ValueError):
            q.automatic_flags([[np.nan, .5]], 20)
        with self.assertRaises(ValueError):
            q.automatic_flags([[1.1, .5]], 20)
        with self.assertRaises(ValueError):
            q.automatic_flags([[.5, .5]], 0)
        with self.assertRaises(ValueError):
            q.rank_to_grid(np.arange(19))
        with self.assertRaises(ValueError):
            q.rank_to_grid(np.arange(20), grid=np.arange(20))

    def test_zero_definers_unit_loadings_and_constant_profile_fail(self):
        no_flags = self.flags.copy()
        no_flags[:, 0] = False
        with self.assertRaisesRegex(ValueError, "without flagged"):
            q.postprocess(self.data, self.loadings, no_flags)
        unit = self.loadings.copy()
        unit[0, 0] = 1
        with self.assertRaisesRegex(ValueError, "infinite weight"):
            q.postprocess(self.data, unit, self.flags)
        # An UNFLAGGED unit loading must not create 0*infinity or NaN.
        unit = self.loadings.copy()
        unit[9, 0] = 1
        with np.errstate(all="raise"):
            valid = q.postprocess(self.data, unit, self.flags)
        self.close(valid["statement_z"], self.baseline["statement_z"])
        cancel_data = self.data.copy()
        cancel_data[:, 1] = cancel_data[:, 0]
        cancel_loadings = np.zeros((10, 2))
        cancel_loadings[0, 0], cancel_loadings[1, 0], cancel_loadings[2, 1] = .8, -.8, .8
        with self.assertRaisesRegex(ValueError, "Constant weighted totals"):
            q.postprocess(cancel_data, cancel_loadings, cancel_loadings != 0)

    def test_varimax_zero_norm_nonconvergence_and_rank_deficiency_fail(self):
        zero_row = self.loadings.copy()
        zero_row[0] = 0
        with self.assertRaisesRegex(ValueError, "Zero communalities"):
            q.varimax(zero_row)
        with self.assertRaisesRegex(ValueError, "did not converge"):
            q.varimax(self.loadings, max_iterations=1)
        with self.assertRaises(ValueError):
            q.varimax(self.loadings, tolerance=float("nan"))
        with tempfile.TemporaryDirectory() as folder:
            rows, people, _ = q.read_data()
            path = Path(folder) / "same-sorts.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["statement_id", "statement", *people])
                writer.writeheader()
                for row in rows:
                    writer.writerow({**row, **{person: row[people[0]] for person in people}})
            with self.assertRaisesRegex(ValueError, "two nonzero"):
                q.analyze(path)

    def test_malformed_csv_identity_is_not_silently_lost(self):
        original = (ROOT / "examples/q_synthetic.csv").read_text(encoding="utf-8")
        mutations = [original.replace("P02", "P01", 1), original.replace("S02,", "S01,", 1), original.replace("S01,", ",", 1), original.replace(",5,5,5,4,", ",5,5,4,", 1)]
        with tempfile.TemporaryDirectory() as folder:
            for index, content in enumerate(mutations):
                path = Path(folder) / f"invalid-{index}.csv"
                path.write_text(content, encoding="utf-8")
                with self.subTest(index=index), self.assertRaises(ValueError):
                    q.read_data(path)

    def test_reference_alignment_and_tolerance_reject_false_parity(self):
        for permutation in itertools.permutations(range(2)):
            for signs in itertools.product((-1, 1), repeat=2):
                candidate = self.loadings[:, permutation] * signs
                order, direction = best_alignment(self.loadings, candidate)
                self.close(candidate[:, order] * direction, self.loadings)
        with self.assertRaises(ValueError):
            best_alignment(self.loadings, np.ones((10, 3)))
        with self.assertRaises(AssertionError):
            compare_matrix("wrong values", self.loadings + 1e-3, self.loadings)
        with self.assertRaises(AssertionError):
            compare_matrix("wrong shape", self.loadings[:1], self.loadings)
        with self.assertRaises(AssertionError):
            compare_matrix("discrete flag", [True], [False], exact=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
