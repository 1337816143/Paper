"""Compare real R/qmethod exports against the synthetic Python pipeline.

No fixture is synthesized here and missing R output fails. Versions, archive
hashes and tolerances are fixed in reference-manifest.json before R execution.
Run from any directory:
  python tests/q/compare_r_reference.py --fetch-sources /tmp/q-r-sources
  # Install the verified official source archives in the pinned R CI runtime.
  Rscript examples/qmethod_reference.R --output-dir /tmp/q-r-reference
  python tests/q/compare_r_reference.py --reference-dir /tmp/q-r-reference

The matched eps=1e-12 run gates parity. The native-default eps=1e-5 run reports
differences without relabelling them as tolerance passes. This is parity for
two invented scenarios, never a recreation of the author's data or software.
"""

import argparse
import csv
import hashlib
import itertools
import json
import sys
from pathlib import Path
from urllib.request import urlopen

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples"))
from q_pipeline import SCENARIOS, analyze  # noqa: E402

MANIFEST = json.loads(Path(__file__).with_name("reference-manifest.json").read_text(encoding="utf-8"))


def best_alignment(reference, candidate):
    """Return column permutation/signs mapping candidate (10x2) to reference.

    Search all 2! x 2^2 possibilities; never align only the first two columns
    of an unsupported multifactor result and never use a general Procrustes
    transform that could conceal a different varimax solution.
    """
    reference = np.asarray(reference, dtype=float)
    candidate = np.asarray(candidate, dtype=float)
    if reference.shape != (10, 2) or candidate.shape != reference.shape:
        raise ValueError("Factor alignment requires exactly two factors and ten people")
    if not np.isfinite(reference).all() or not np.isfinite(candidate).all():
        raise ValueError("Factor alignment requires finite loadings")
    alternatives = []
    for permutation in itertools.permutations(range(2)):
        for signs in itertools.product((-1, 1), repeat=2):
            aligned = candidate[:, permutation] * signs
            alternatives.append((float(np.sum((aligned - reference)**2)), permutation, signs))
    _, permutation, signs = min(alternatives)
    return list(permutation), list(signs)


def read_matrix(directory, name, boolean=False):
    """Read R write.csv output while retaining labels for identity checks."""
    path = directory / f"{name}.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if len(rows) < 2 or len(rows[0]) < 2 or any(len(row) != len(rows[0]) for row in rows[1:]):
        raise ValueError(f"Malformed R matrix: {path}")
    cells = [row[1:] for row in rows[1:]]
    if boolean:
        if any(value not in ("TRUE", "FALSE") for row in cells for value in row):
            raise ValueError(f"Non-boolean R flag in {path}")
        matrix = np.array([[value == "TRUE" for value in row] for row in cells])
    else:
        matrix = np.asarray(cells, dtype=float)
        if not np.isfinite(matrix).all():
            raise ValueError(f"Non-finite R output in {path}")
    return matrix, [row[0] for row in rows[1:]], rows[0][1:]


def compare_matrix(name, actual, expected, *, exact=False, core=False):
    """Check a shape first, then the predeclared tolerance, returning max error."""
    actual, expected = np.asarray(actual), np.asarray(expected)
    if actual.shape != expected.shape:
        raise AssertionError(f"{name}: R shape {actual.shape} != Python shape {expected.shape}")
    if not np.isfinite(actual).all() or not np.isfinite(expected).all():
        raise AssertionError(f"{name}: non-finite values are not comparable")
    tolerance = MANIFEST["tolerances"]
    prefix = "matrix_eigen" if core else "arithmetic"
    matches = np.array_equal(actual, expected) if exact else np.allclose(
        actual, expected, atol=tolerance[f"{prefix}_atol"], rtol=tolerance[f"{prefix}_rtol"]
    )
    error = float(np.max(abs(actual.astype(float) - expected.astype(float))))
    if not matches:
        contract = "exact equality" if exact else f"atol={tolerance[f'{prefix}_atol']}, rtol={tolerance[f'{prefix}_rtol']}"
        raise AssertionError(f"{name}: max absolute difference {error:.12g}; required {contract}. Investigate; do not widen the tolerance.")
    return error


def read_metadata(directory, scenario, mode):
    with (directory / "metadata.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    metadata = {row["key"]: row["value"] for row in rows}
    if len(metadata) != len(rows):
        raise AssertionError("Duplicate R metadata keys")
    required = {key: value for key, value in MANIFEST["runtime"].items() if key != "numpy"}
    required.update(scenario=scenario, mode=mode, nfactors="2", normalize="TRUE", author_data_reproduced="FALSE", input_sha256=MANIFEST["input"]["sha256"])
    for source in MANIFEST["sources"]:
        required[f"{source['package']}_source_sha256"] = source["sha256"]
    for key, expected in required.items():
        if metadata.get(key) != expected:
            raise AssertionError(f"R metadata {key!r}: expected {expected!r}, found {metadata.get(key)!r}")
    eps = 1e-12 if mode == "matched" else 1e-5
    if float(metadata["eps"]) != eps:
        raise AssertionError(f"Wrong rotation tolerance for {mode}")
    for name in ("raw_qmethod_result.rds", "canonical_qmethod_result.rds"):
        path = directory / name
        if not path.is_file() or path.stat().st_size == 0:
            raise AssertionError(f"Missing actual R audit object: {path}")
    return metadata


def compare_scenario(reference_dir, scenario):
    python = analyze(scenario=scenario)
    directory = reference_dir / scenario / "matched"
    read_metadata(directory, scenario, "matched")
    checks = {}
    identities = {"data": ([row["id"] for row in python["statements"]], python["participants"])}
    data, row_ids, col_ids = read_matrix(directory, "data")
    if (row_ids, col_ids) != identities["data"]:
        raise AssertionError("R data row/column identities do not match the Python scenario")
    checks["data"] = compare_matrix("data", data, python["data"], exact=True)
    for name, field in (("correlation", "person_correlation"), ("eigenvalues", "all_eigenvalues")):
        values, labels, _ = read_matrix(directory, name)
        if name == "correlation" and labels != python["participants"]:
            raise AssertionError("R person correlation labels have changed")
        expected = np.asarray(python[field])
        if name == "eigenvalues":
            values = values[:, 0]
        checks[name] = compare_matrix(name, values, expected, core=True)

    raw, people, _ = read_matrix(directory, "loadings_raw")
    if people != python["participants"]:
        raise AssertionError("R loading rows must follow participant IDs")
    permutation, signs = best_alignment(python["rotated_loadings"], raw)
    aligned = raw[:, permutation] * signs
    checks["raw_loadings_aligned"] = compare_matrix("raw loadings aligned by sign/permutation", aligned, python["rotated_loadings"])
    canonical, _, _ = read_matrix(directory, "loadings")
    checks["R_canonicalization"] = compare_matrix("independent R canonicalization", canonical, aligned, core=True)
    with (directory / "alignment.csv").open(encoding="utf-8", newline="") as handle:
        alignment = list(csv.DictReader(handle))
    if [int(row["raw_column"]) - 1 for row in alignment] != permutation or [int(row["sign"]) for row in alignment] != signs:
        raise AssertionError("R and Python factor alignment records disagree")
    if [row["anchor"] for row in alignment] != python["canonical_factor_anchors"]:
        raise AssertionError("Factor anchor identities disagree")

    unrotated, _, _ = read_matrix(directory, "unrotated_loadings")
    permutation_u, signs_u = best_alignment(python["unrotated_loadings"], unrotated)
    checks["unrotated_loadings"] = compare_matrix("unrotated PCA loadings", unrotated[:, permutation_u] * signs_u, python["unrotated_loadings"], core=True)
    checks["retained_reconstruction"] = compare_matrix("retained correlation reconstruction", canonical @ canonical.T, python["retained_correlation_approximation"], core=True)
    for name, field, exact in (
        ("flags", "flagged", True), ("weights", "weights", False),
        ("weighted_totals", "weighted_totals", False), ("zscores", "statement_z", False),
        ("factor_arrays", "factor_arrays", True), ("ranks", "ranks", True),
    ):
        values, labels, _ = read_matrix(directory, name, boolean=name == "flags")
        expected_labels = python["participants"] if name in ("flags", "weights") else row_ids
        if labels != expected_labels:
            raise AssertionError(f"R {name} row identities differ")
        checks[name] = compare_matrix(name, values, python[field], exact=exact)

    characteristics, _, columns = read_matrix(directory, "factor_characteristics")
    for column, expected, exact in (
        ("nload", python["flagged_counts"], True),
        ("av_rel_coef", [python["assumed_individual_reliability"]] * 2, True),
        ("reliability", python["composite_reliability"], False),
        ("se_fscores", python["factor_standard_errors"], False),
    ):
        checks[column] = compare_matrix(column, characteristics[:, columns.index(column)], expected, exact=exact)
    sed, _, _ = read_matrix(directory, "sed")
    checks["SED"] = compare_matrix("SED", sed[0, 1], python["SED"])
    with (directory / "distinguishing.csv").open(encoding="utf-8", newline="") as handle:
        comparisons = list(csv.DictReader(handle))
    if [row[""] for row in comparisons] != row_ids:
        raise AssertionError("R distinguishing rows differ")
    checks["z_difference"] = compare_matrix("z-score differences", [float(row["f1_f2"]) for row in comparisons], [row["difference"] for row in python["statement_comparisons"]])
    for r_row, p_row in zip(comparisons, python["statement_comparisons"]):
        significance = r_row["sig_f1_f2"]
        if significance not in ("", "*", "**", "***", "6*"):
            raise AssertionError(f"Unrecognized qmethod significance level: {significance!r}")
        if (significance != "") != p_row["distinguishing_p05"] or (significance not in ("", "*")) != p_row["distinguishing_p01"]:
            raise AssertionError("R and Python distinguishing decisions differ")
        expected_label = "Distinguishing" if p_row["distinguishing_p05"] else "Consensus"
        if r_row["dist.and.cons"] != expected_label:
            raise AssertionError("R and Python consensus labels differ")

    default_dir = reference_dir / scenario / "native-default"
    read_metadata(default_dir, scenario, "native-default")
    default_loadings, _, _ = read_matrix(default_dir, "loadings_raw")
    p_default, s_default = best_alignment(python["rotated_loadings"], default_loadings)
    default_z, _, _ = read_matrix(default_dir, "zscores")
    default_flags, _, _ = read_matrix(default_dir, "flags", boolean=True)
    default_arrays, _, _ = read_matrix(default_dir, "factor_arrays")
    return {
        "scenario": scenario, "matched_passed": True, "checked_outputs": len(checks),
        "factor_alignment": {"R_columns_for_python_zero_based": permutation, "signs": signs},
        "max_absolute_errors": checks,
        "native_default_diagnostic": {
            "is_acceptance_gate": False, "eps": 1e-5,
            "max_loading_absolute_difference": float(np.max(abs(default_loadings[:, p_default] * s_default - python["rotated_loadings"]))),
            "max_z_absolute_difference": float(np.max(abs(default_z - python["statement_z"]))),
            "flags_equal": bool(np.array_equal(default_flags, python["flagged"])),
            "factor_arrays_equal": bool(np.array_equal(default_arrays, python["factor_arrays"])),
        },
    }


def fetch_sources(destination):
    """Download, never execute, the two official hash-pinned CRAN archives."""
    destination.mkdir(parents=True, exist_ok=True)
    verified = []
    for source in MANIFEST["sources"]:
        path = destination / source["filename"]
        if path.exists():
            payload = path.read_bytes()
        else:
            with urlopen(source["url"], timeout=60) as response:
                payload = response.read()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != source["sha256"]:
            raise AssertionError(f"Source hash mismatch for {source['package']}; nothing installed")
        if not path.exists():
            path.write_bytes(payload)
        verified.append({"path": str(path), "sha256": digest})
    return {"downloaded_and_hash_verified": verified, "installed": False}


def compare_all(reference_dir):
    if np.__version__ != MANIFEST["runtime"]["numpy"]:
        raise AssertionError(f"Use pinned NumPy {MANIFEST['runtime']['numpy']}; found {np.__version__}")
    for name in ("R_session_info.txt", "R_package_versions.csv"):
        if not (reference_dir / name).is_file():
            raise FileNotFoundError(f"Real R provenance missing: {reference_dir / name}")
    return {
        "passed": True, "scope": "Actual R/qmethod comparison for two synthetic scenarios only; no author data reproduced",
        "versions": MANIFEST["runtime"], "predeclared_tolerances": MANIFEST["tolerances"],
        "scenarios": [compare_scenario(reference_dir, scenario) for scenario in SCENARIOS],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--reference-dir", type=Path)
    operation.add_argument("--fetch-sources", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = fetch_sources(args.fetch_sources) if args.fetch_sources else compare_all(args.reference_dir)
    except (AssertionError, ValueError, OSError, KeyError) as exc:
        report = {"passed": False, "error": str(exc), "scope": "No R parity claim; diagnose the failure without changing the tolerance"}
        text = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")
        print(text)
        raise SystemExit(1)
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
