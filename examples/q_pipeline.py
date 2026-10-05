"""Complete, explicitly synthetic two-factor Q-method arithmetic.

Python >=3.11 and NumPy are required (tested with NumPy 2.3.5). No network,
interviews or author data are used. Put this file beside q_synthetic.csv:
  python q_pipeline.py --scenario baseline --output q_results.json
  python q_pipeline.py --scenario reverse-p03 --output q_reverse.json
  python q_pipeline.py --test

The CSV is always the unchanged baseline: 20 invented statements x 10 invented
people. reverse-p03 replaces P03's scores by 6-score BEFORE the entire analysis.
Two retained factors and Kaiser-normalized varimax are teaching choices, not
claims about the author's exact settings. The third eigenvalue also exceeds 1.

Numerical contract (declared before reference execution): varimax uses the R
stats relative objective stopping rule with eps=1e-12; finite/unit guards use
1e-12. Local algebra invariants use atol=1e-10. R comparison tolerances are fixed
in tests/q/reference-manifest.json. A passing Python test is NOT R parity.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
GRID = np.array([1] * 2 + [2] * 4 + [3] * 8 + [4] * 4 + [5] * 2)
SCENARIOS = ("baseline", "reverse-p03")
VARIMAX_EPS = 1e-12
NUMERIC_GUARD = 1e-12
RETAINED_FACTORS = 2


def _matrix(value, name):
    """Return a finite float matrix; never silently broadcast missing axes."""
    try:
        matrix = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain numeric values") from exc
    if matrix.ndim != 2 or not all(matrix.shape):
        raise ValueError(f"{name} must be a nonempty two-dimensional matrix")
    if not np.isfinite(matrix).all():
        raise ValueError(f"{name} must contain only finite values")
    return matrix


def validate_data(data):
    """Validate and return D (20 statements x 10 complete Q-sorts)."""
    data = _matrix(data, "Data")
    if data.shape != (20, 10):
        raise ValueError("This fixed example requires 20 statements x 10 Q-sorts")
    if not np.all(np.sort(data, axis=0) == GRID[:, None]):
        raise ValueError("Each Q-sort must have exactly 2/4/8/4/2 scores in 1..5")
    return data


def read_data(path=ROOT / "q_synthetic.csv"):
    """Return statement dictionaries, participant IDs and validated D (20x10)."""
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        if not fields or fields[:2] != ["statement_id", "statement"]:
            raise ValueError("CSV must start with statement_id,statement")
        people = fields[2:]
        if len(people) != 10 or len(set(fields)) != len(fields) or any(not p for p in people):
            raise ValueError("CSV requires ten unique, nonempty participant IDs")
        rows = list(reader)
    if not rows or any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("CSV contains empty or ragged rows")
    ids = [row["statement_id"] for row in rows]
    if len(set(ids)) != len(ids) or any(not value for value in ids):
        raise ValueError("Statement identifiers must be unique and nonempty")
    if any(not row["statement"].strip() for row in rows):
        raise ValueError("Every invented statement needs its teaching text")
    try:
        data = np.array([[float(row[person]) for person in people] for row in rows])
    except (TypeError, ValueError) as exc:
        raise ValueError("Every Q-sort cell must be numeric") from exc
    return rows, people, validate_data(data)


def varimax(loadings, tolerance=VARIMAX_EPS, max_iterations=1000):
    """L (people x factors) -> rotated L, orthogonal T, iteration count.

    Kaiser normalization divides each person's row by its retained loading
    vector length, optimizes the axes, then restores those lengths. The update
    and relative stopping rule match stats::varimax(normalize=TRUE, eps=...).
    Rotation preserves L L^T, the retained approximation, not the full C.
    """
    loadings = _matrix(loadings, "Loadings")
    if loadings.shape[1] < 2 or loadings.shape[0] < loadings.shape[1]:
        raise ValueError("Varimax needs at least two factors and enough loading rows")
    if not np.isfinite(tolerance) or tolerance <= 0 or not isinstance(max_iterations, int) or max_iterations < 1:
        raise ValueError("Varimax requires positive tolerance and iteration limit")
    norm = np.linalg.norm(loadings, axis=1)
    if np.any(norm < NUMERIC_GUARD):
        raise ValueError("Zero communalities need a defined normalization policy")
    normalized = loadings / norm[:, None]
    rotation = np.eye(loadings.shape[1])
    previous = 0.0
    for iteration in range(1, max_iterations + 1):
        projected = normalized @ rotation
        gradient = normalized.T @ (
            projected**3
            - projected @ np.diag((projected**2).sum(axis=0)) / normalized.shape[0]
        )
        left, singular, right = np.linalg.svd(gradient)
        rotation = left @ right
        objective = float(singular.sum())
        if objective < previous * (1 + tolerance):
            return loadings @ rotation, rotation, iteration
        previous = objective
    raise ValueError("Varimax did not converge within its declared iteration limit")


def automatic_flags(loading, nstat):
    """Loadings (people x factors) -> bool flags of same shape, threshold.

    This rule also supports isolated three-factor teaching cards. Only the
    postprocessing/comparison chain below is restricted to exactly two factors.
    Both inequalities are strict; negative defining loadings are allowed.
    """
    loading = _matrix(loading, "Loadings")
    if isinstance(nstat, bool) or not isinstance(nstat, (int, np.integer)) or nstat < 2:
        raise ValueError("nstat must be an integer of at least two")
    if np.any(abs(loading) > 1 + NUMERIC_GUARD):
        raise ValueError("Correlation loadings must lie in [-1, 1]")
    threshold = 1.96 / math.sqrt(nstat)
    squares = loading**2
    flags = (abs(loading) > threshold) & (squares > squares.sum(axis=1)[:, None] - squares)
    return flags, threshold


def rank_to_grid(z, grid=GRID):
    """z (20,) -> factor array (20,), mean ranks (20,), exact tie records.

    Ascending mean ranks and truncation of fractional numeric subscripts match
    qmethod/R. A tie crossing grid slots can change the nominal slot occupancy;
    we report it instead of inventing a statement-ID tie-break.
    """
    z = np.asarray(z, dtype=float)
    grid = np.asarray(grid, dtype=float)
    if z.shape != (20,) or not np.isfinite(z).all():
        raise ValueError("A z profile must be a finite vector of length 20")
    if grid.shape != GRID.shape or not np.array_equal(grid, GRID):
        raise ValueError("This example uses the sorted 2/4/8/4/2 grid only")
    sorted_z = np.sort(z)
    ranks = np.array([np.flatnonzero(sorted_z == value).mean() + 1 for value in z])
    array = GRID[ranks.astype(int) - 1]
    ties = []
    for value in np.unique(z):
        indices = np.flatnonzero(z == value)
        if len(indices) > 1:
            ties.append({"statement_indices": indices.tolist(), "mean_rank": float(ranks[indices[0]]), "score": int(array[indices[0]])})
    return array, ranks, ties


def postprocess(data, loading, flags, reliability_assumption=0.8):
    """D (20x10), L/flags (10x2) -> signed weights and all statement outputs.

    W (10x2) contains l/(1-l^2) only at flagged positions. T=D@W (20x2)
    sums raw grid-score contributions. Each column of T is centered/scaled
    ACROSS the 20 statements with sample SD (ddof=1), producing Z (20x2).
    This is explicitly a two-factor SED comparison, not a multifactor qdc clone.
    """
    data = validate_data(data)
    loading = _matrix(loading, "Loadings")
    if loading.shape != (data.shape[1], RETAINED_FACTORS):
        raise ValueError("Postprocessing requires exactly two factors and one loading row per person")
    flags = np.asarray(flags)
    if flags.shape != loading.shape or flags.dtype.kind != "b":
        raise ValueError("Flags must be a boolean matrix matching the loadings")
    if np.any(abs(loading) > 1 + NUMERIC_GUARD):
        raise ValueError("Correlation loadings must lie in [-1, 1]")
    if not np.isfinite(reliability_assumption) or not 0 < reliability_assumption < 1:
        raise ValueError("Reliability assumption must be between 0 and 1")
    if np.any(abs(loading[flags]) >= 1 - NUMERIC_GUARD):
        raise ValueError("Unit defining loading has infinite weight; no arbitrary cap is used")
    if np.any(flags.sum(axis=0) == 0):
        raise ValueError("A factor without flagged sorts has no statement profile")
    weights = np.zeros_like(loading)
    weights[flags] = loading[flags] / (1 - loading[flags]**2)
    totals = data @ weights
    means = totals.mean(axis=0)
    sd = totals.std(axis=0, ddof=1)
    if np.any(sd <= NUMERIC_GUARD):
        raise ValueError("Constant weighted totals cannot define a z profile")
    zs = (totals - means) / sd
    arrays, ranks, ties = [], [], []
    for factor in range(RETAINED_FACTORS):
        array, rank, tied = rank_to_grid(zs[:, factor])
        arrays.append(array)
        ranks.append(rank)
        ties.append(tied)
    count = flags.sum(axis=0)
    reliability = count * reliability_assumption / (1 + (count - 1) * reliability_assumption)
    se = zs.std(axis=0, ddof=1) * np.sqrt(1 - reliability)
    sed = float(np.sqrt(se[0]**2 + se[1]**2))
    comparisons = [{
        "difference": float(delta), "SED": sed,
        "threshold_p05": 1.96 * sed, "threshold_p01": 2.576 * sed,
        "distinguishing_p05": bool(abs(delta) > 1.96 * sed),
        "distinguishing_p01": bool(abs(delta) > 2.576 * sed),
        "label": "Distinguishing" if abs(delta) > 1.96 * sed else "Consensus under this test",
    } for delta in zs[:, 0] - zs[:, 1]]
    return {
        "weights": weights.tolist(), "weighted_totals": totals.tolist(),
        "weighted_total_means": means.tolist(), "weighted_total_sample_sd": sd.tolist(),
        "statement_z": zs.tolist(), "factor_arrays": np.array(arrays).T.tolist(),
        "ranks": np.array(ranks).T.tolist(), "exact_ties": ties,
        "array_slot_counts": [[int((a == score).sum()) for score in range(1, 6)] for a in arrays],
        "flagged_counts": count.tolist(), "assumed_individual_reliability": reliability_assumption,
        "composite_reliability": reliability.tolist(), "factor_standard_errors": se.tolist(),
        "SED": sed, "statement_comparisons": comparisons,
        "weight_sums": weights.sum(axis=0).tolist(), "comparison_scope": "F1 versus F2 only; exactly two retained factors",
    }


def analyze(path=ROOT / "q_synthetic.csv", scenario="baseline", nfactors=RETAINED_FACTORS):
    """Read one baseline CSV and return a JSON-safe, fully recomputed result.

    Shapes: D=20x10 -> C=10x10 -> retained V/L=10x2 -> W=10x2 -> Z/array=20x2.
    The UI reads these precomputed results; it does not fit arbitrary data.
    """
    if isinstance(nfactors, bool) or nfactors != RETAINED_FACTORS:
        raise ValueError("This walkthrough compares exactly two factors; other counts are unsupported")
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario {scenario!r}; choose one of {SCENARIOS}")
    rows, people, data = read_data(path)
    if scenario == "reverse-p03":
        if "P03" not in people:
            raise ValueError("reverse-p03 requires the baseline participant P03")
        data = data.copy()
        data[:, people.index("P03")] = 6 - data[:, people.index("P03")]
    validate_data(data)
    nstat, npeople = data.shape
    centered = data - data.mean(axis=0)
    ss = (centered**2).sum(axis=0)
    corr = centered.T @ centered / np.sqrt(np.outer(ss, ss))
    eigen, vectors = np.linalg.eigh(corr)
    order = np.argsort(eigen)[::-1]
    eigen, vectors = eigen[order], vectors[:, order]
    if eigen[RETAINED_FACTORS - 1] <= NUMERIC_GUARD:
        raise ValueError("Data do not support two nonzero retained components")
    # Eigensolvers may choose either sign for each eigenvector. Stabilize the
    # displayed PCA substitutions independently of the later rotated-factor
    # convention: largest-magnitude entry positive; ties within 1e-12 use the
    # first participant in CSV order. This does not alter eigenvalues/subspace.
    unrotated_anchors = []
    for factor in range(RETAINED_FACTORS):
        magnitude = abs(vectors[:, factor])
        anchor = int(np.flatnonzero(np.isclose(magnitude, magnitude.max(), atol=NUMERIC_GUARD, rtol=0))[0])
        unrotated_anchors.append(people[anchor])
        if vectors[anchor, factor] < 0:
            vectors[:, factor] *= -1
    loadings = vectors[:, :RETAINED_FACTORS] * np.sqrt(eigen[:RETAINED_FACTORS])
    rotated, rotation, iterations = varimax(loadings)
    # Axis signs/order are conventions, not new findings. Point each factor's
    # strongest absolute participant loading positive; order by that person's
    # CSV position. P03 is not either anchor in these two declared scenarios.
    signs = np.array([1 if rotated[np.argmax(abs(rotated[:, j])), j] >= 0 else -1 for j in range(RETAINED_FACTORS)])
    rotated, rotation = rotated * signs, rotation * signs
    anchors = [int(np.argmax(abs(rotated[:, j]))) for j in range(RETAINED_FACTORS)]
    factor_order = np.argsort(anchors, kind="stable")
    rotated, rotation = rotated[:, factor_order], rotation[:, factor_order]
    flags, threshold = automatic_flags(rotated, nstat)
    post = postprocess(data, rotated, flags)
    result = {
        "schema": "synthetic-q-walkthrough.v1", "author_data_reproduced": False,
        "source_paper": "https://doi.org/10.1016/j.agsy.2024.104187", "numpy_version": np.__version__,
        "scenario": scenario, "available_scenarios": list(SCENARIOS),
        "scenario_transformation": "none" if scenario == "baseline" else "P03 score = 6 - baseline score; entire chain recomputed",
        "baseline_csv_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "statements": [{"id": row["statement_id"], "text": row["statement"]} for row in rows],
        "participants": people, "data": data.astype(int).tolist(), "nstat": nstat, "npeople": npeople,
        "grid_scores": [1, 2, 3, 4, 5], "grid_counts": [2, 4, 8, 4, 2],
        "input_orientation": "statements as rows; people/Q-sorts as columns",
        "means": data.mean(axis=0).tolist(), "sample_sd": data.std(axis=0, ddof=1).tolist(),
        "centered_sum_squares": ss.tolist(), "person_correlation": corr.tolist(),
        "all_eigenvalues": eigen.tolist(), "retained_factors": RETAINED_FACTORS,
        "retained_factor_reason": "Fixed teaching choice, not automatic model selection or the author 327-person result",
        "retained_eigenvectors": vectors[:, :RETAINED_FACTORS].tolist(),
        "unrotated_loadings": loadings.tolist(), "rotation_matrix": rotation.tolist(),
        "unrotated_axis_sign_convention": "Largest absolute eigenvector component positive; ties within 1e-12 use first participant in CSV order",
        "unrotated_axis_anchors": unrotated_anchors,
        "rotation_iterations": iterations,
        "rotation_setting": "Orthogonal varimax; Kaiser row normalization; R stats relative stopping rule with eps=1e-12",
        "rotation_tolerance": VARIMAX_EPS, "rotation_max_iterations": 1000,
        "rotated_loadings": rotated.tolist(), "loading_threshold": threshold, "flagged": flags.tolist(),
        "unassigned": [person for person, flag in zip(people, flags) if not flag.any()],
        "canonical_factor_anchors": [people[anchors[i]] for i in factor_order],
        "retained_variance_percent": float(eigen[:RETAINED_FACTORS].sum() / npeople * 100),
        "retained_correlation_approximation": (loadings @ loadings.T).tolist(),
        "retained_loading_lengths": np.linalg.norm(loadings, axis=1).tolist(),
        **post,
        "boundaries": [
            "No author original sorts, supplemental calculation sheet or exact author package version acquired.",
            "The reference harness requires real R/qmethod output; Python tests alone do not establish R parity.",
            "No interview reasons exist for the invented people. Interpretive labels are hypotheses, not empirical findings.",
            "Q loadings, z-scores, factor scores and reliability are not optimization objective weights or population proportions.",
        ],
    }
    # Fail at the computation boundary instead of emitting NaN/Infinity as JSON.
    json.dumps(result, allow_nan=False)
    return result


def test():
    """Small standalone smoke check; the repository adds independent math tests."""
    baseline = analyze()
    reverse = analyze(scenario="reverse-p03")
    assert baseline["flagged_counts"] == [5, 4] and baseline["unassigned"] == ["P10"]
    assert reverse["rotated_loadings"][2][0] < 0 and reverse["weights"][2][0] < 0
    assert baseline["factor_arrays"] == reverse["factor_arrays"]
    assert np.allclose(baseline["statement_z"], reverse["statement_z"], atol=1e-10, rtol=0)
    assert baseline["flagged"] == reverse["flagged"]
    return {"passed": True, "scenarios": list(SCENARIOS), "scope": "Fixed synthetic Python smoke checks only; not R parity or browser acceptance"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default="baseline")
    parser.add_argument("--input", type=Path, default=ROOT / "q_synthetic.csv")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    output = test() if args.test else analyze(args.input, scenario=args.scenario)
    encoded = json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)
