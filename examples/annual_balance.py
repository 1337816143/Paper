#!/usr/bin/env python3
"""A synthetic annual N ledger, not FarmDESIGN/FarmM3 or a fertiliser model.

Run with Python 3 (standard library only). All quantities are invented.
See annual_balance_readme.md for units, omitted processes and interpretation.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

DEFAULTS = {"herd": 8, "forageArea": 6, "lossFraction": 0.2,
            "replaceRetained": False}
DOMAIN = {"herd": (0, 20, 1), "forageArea": (0, 10, 0.5),
          "lossFraction": (0, 0.2, 0.05)}
CONSTANTS = {"area": 10, "forageYield": 6, "feedPerAnimal": 5,
             "feedNConcentration": 25, "animalProductNPerAnimal": 20,
             "cashProductNPerHa": 60, "forageMineralNPerHa": 100,
             "cashMineralNPerHa": 80, "depositionNPerHa": 10,
             "baselineLossFraction": 0.2, "feedImportCap": 10}


def validate(values: dict) -> dict:
    """Do not turn an empty string into zero or silently clamp invalid input."""
    if not isinstance(values, dict) or set(values) != set(DEFAULTS):
        raise ValueError("Inputs must contain exactly herd, forageArea, lossFraction, replaceRetained")
    result = {}
    for key, (low, high, step) in DOMAIN.items():
        value = values[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
        if value < low or value > high:
            raise ValueError(f"{key} must be within [{low}, {high}]")
        steps = (value - low) / step
        if not math.isclose(steps, round(steps), rel_tol=0, abs_tol=1e-9):
            raise ValueError(f"{key} must use increments of {step}")
        result[key] = float(value)
    if type(values["replaceRetained"]) is not bool:
        raise ValueError("replaceRetained must be a boolean")
    result["replaceRetained"] = values["replaceRetained"]
    return result


def calculate(values: dict | None = None) -> dict:
    """Return raw values; formatting must never alter conservation calculations."""
    x = validate(dict(DEFAULTS) if values is None else values)
    c = CONSTANTS
    cash_area = c["area"] - x["forageArea"]
    harvest = c["forageYield"] * x["forageArea"]
    demand = c["feedPerAnimal"] * x["herd"]
    consumed = min(harvest, demand)
    imported = max(demand - harvest, 0)
    exported = max(harvest - demand, 0)
    harvest_n = harvest * c["feedNConcentration"]
    feed_n = demand * c["feedNConcentration"]
    import_n = imported * c["feedNConcentration"]
    export_n = exported * c["feedNConcentration"]
    animal_n = c["animalProductNPerAnimal"] * x["herd"]
    cash_n = c["cashProductNPerHa"] * cash_area
    excreted = feed_n - animal_n
    chain_loss = excreted * x["lossFraction"]
    to_soil = excreted - chain_loss
    base_mineral = (c["forageMineralNPerHa"] * x["forageArea"]
                    + c["cashMineralNPerHa"] * cash_area)
    retained = (c["baselineLossFraction"] - x["lossFraction"]) * excreted
    mineral = base_mineral - (retained if x["replaceRetained"] else 0)
    if mineral < 0:
        raise ValueError("Adjusted mineral N cannot be negative")
    deposition = c["depositionNPerHa"] * c["area"]
    residual = mineral + deposition + to_soil - harvest_n - cash_n
    external_input = mineral + deposition + import_n
    external_output = animal_n + cash_n + export_n
    surplus = external_input - external_output
    flags = {"feedImportExceeded": imported > c["feedImportCap"] + 1e-9,
             "soilSupplyDeficit": residual < -1e-9}
    return {
        "inputs": x, "cashArea": cash_area, "forageHarvest": harvest,
        "feedDemand": demand, "feedConsumed": consumed, "feedImported": imported,
        "feedExported": exported, "forageHarvestNitrogen": harvest_n,
        "feedNitrogenConsumed": consumed * c["feedNConcentration"], "feedNitrogenImported": import_n,
        "feedNitrogenExported": export_n, "cashProductNitrogen": cash_n,
        "animalProductNitrogen": animal_n, "manureExcretedNitrogen": excreted,
        "chainLoss": chain_loss, "manureToSoil": to_soil,
        "baseMineralNitrogen": base_mineral, "retainedNitrogen": retained,
        "mineralNitrogen": mineral, "depositionNitrogen": deposition,
        "soilResidual": residual, "farmInputs": external_input,
        "farmOutputs": external_output, "farmSurplus": surplus,
        "checkError": surplus - chain_loss - residual,
        "flags": flags, "feasible": not any(flags.values())}


def self_test() -> None:
    """Externally specified examples, not a recomputation of each code line."""
    examples = [
        ({**DEFAULTS}, (168, 552, 720, 4, 0, True)),
        ({**DEFAULTS, "lossFraction": 0.1}, (84, 636, 720, 4, 0, True)),
        ({**DEFAULTS, "lossFraction": 0.1, "replaceRetained": True},
         (84, 552, 636, 4, 0, True)),
        ({**DEFAULTS, "herd": 4}, (84, 216, 300, 0, 16, True)),
        ({**DEFAULTS, "herd": 0}, (0, -120, -120, 0, 36, False)),
        ({**DEFAULTS, "herd": 12}, (252, 888, 1140, 24, 0, False)),
    ]
    for inputs, expected in examples:
        result = calculate(inputs)
        keys = ("chainLoss", "soilResidual", "farmSurplus", "feedImported", "feedExported")
        for key, value in zip(keys, expected[:5]):
            assert math.isclose(result[key], value, abs_tol=1e-9), (key, result[key], value)
        assert result["feasible"] is expected[5]
        assert abs(result["checkError"]) < 1e-9
    for key, value in [("herd", ""), ("herd", True), ("herd", -1),
                       ("herd", 1.1), ("herd", float("nan")),
                       ("forageArea", 10.5), ("lossFraction", 0.03),
                       ("replaceRetained", 1)]:
        try:
            calculate({**DEFAULTS, key: value})
        except ValueError:
            continue
        raise AssertionError(f"Invalid input accepted: {key}={value!r}")
    print("PASS: six independently specified ledgers and eight invalid-input cases")


def read_input(path: str) -> dict:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(DEFAULTS):
            raise ValueError("CSV header must be herd,forageArea,lossFraction,replaceRetained")
        rows = list(reader)
    if len(rows) != 1:
        raise ValueError("Input CSV must contain exactly one synthetic configuration")
    row = rows[0]
    if set(row) != set(DEFAULTS) or any(value is None for value in row.values()):
        raise ValueError("CSV data row must contain exactly four columns")
    if row["replaceRetained"] not in ("true", "false"):
        raise ValueError("CSV replaceRetained must be true or false")
    return {**{key: float(row[key]) for key in DOMAIN},
            "replaceRetained": row["replaceRetained"] == "true"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--herd", type=float, default=8)
    parser.add_argument("--forage-area", type=float, default=6)
    parser.add_argument("--loss-fraction", type=float, default=0.2)
    parser.add_argument("--replace-retained", action="store_true")
    parser.add_argument("--input", help="Read one synthetic input CSV instead of individual flags")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.test:
        self_test()
        return
    try:
        values = read_input(args.input) if args.input else {
            "herd": args.herd, "forageArea": args.forage_area,
            "lossFraction": args.loss_fraction, "replaceRetained": args.replace_retained}
        r = calculate(values)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2, allow_nan=False))
        return
    print("Synthetic annual ledger: fixed production targets; not an agronomic recommendation")
    print(f"Forage harvest / demand / imported / exported: {r['forageHarvest']:.2f} / "
          f"{r['feedDemand']:.2f} / {r['feedImported']:.2f} / {r['feedExported']:.2f} Mg DM/year")
    print("All following N quantities are kg N/year for the entire 10 ha farm:")
    for key in ("mineralNitrogen", "manureExcretedNitrogen", "chainLoss", "manureToSoil",
                "soilResidual", "farmInputs", "farmOutputs", "farmSurplus", "checkError"):
        print(f"  {key}: {r[key]:.2f}")
    print("Limited teaching constraints:", "pass" if r["feasible"] else "NOT satisfied", r["flags"])
    print("Zero stock change, feed waste, fixation, bedding and imported manure; residual is not measured leaching.")


if __name__ == "__main__":
    main()
