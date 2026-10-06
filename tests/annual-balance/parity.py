#!/usr/bin/env python3
"""Raw Python/JS comparison over the complete frozen teaching domain."""
import argparse
import copy
import importlib.util
import itertools
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("annual_balance", ROOT / "examples/annual_balance.py")
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def run(model_path):
    model.self_test()
    inputs = [{"herd": h, "forageArea": a / 2, "lossFraction": f / 20,
               "replaceRetained": replacement}
              for h, a, f, replacement in itertools.product(range(21), range(21), range(5), (False, True))]
    assert len(inputs) == 4410
    original_inputs = copy.deepcopy(inputs)
    code = "const fs=require('node:fs'),m=require(process.argv[1]);process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(x=>m.calculate(x))));"
    completed = subprocess.run(["node", "-e", code, str(model_path)], input=json.dumps(inputs),
                               text=True, capture_output=True, check=True)
    browser = json.loads(completed.stdout)
    assert len(browser) == len(inputs)
    max_error = 0.0
    feasible = 0
    for index, (x, js) in enumerate(zip(inputs, browser)):
        py = model.calculate(x)
        assert set(js) == set(py), (index, set(js) ^ set(py))
        for key, expected in py.items():
            if type(expected) in (float, int):
                actual = js[key]
                assert type(actual) in (float, int) and math.isfinite(actual)
                difference = abs(actual - expected)
                assert difference <= 1e-9, (index, key, actual, expected)
                max_error = max(max_error, difference)
            else:
                assert js[key] == expected, (index, key, js[key], expected)
        # Conservation at separate boundaries, including unused forage exports.
        assert abs(py["forageHarvest"] + py["feedImported"] - py["feedDemand"] - py["feedExported"]) < 1e-9
        assert abs(py["feedNitrogenConsumed"] + py["feedNitrogenImported"] - py["animalProductNitrogen"] - py["manureExcretedNitrogen"]) < 1e-9
        assert abs(py["manureExcretedNitrogen"] - py["chainLoss"] - py["manureToSoil"]) < 1e-9
        assert abs(py["farmInputs"] - py["farmOutputs"] - py["chainLoss"] - py["soilResidual"]) < 1e-9
        assert py["forageHarvestNitrogen"] == py["feedNitrogenConsumed"] + py["feedNitrogenExported"]
        if x["herd"] == 0:
            assert py["animalProductNitrogen"] == py["manureExcretedNitrogen"] == py["chainLoss"] == 0
        feasible += int(py["feasible"])
    assert inputs == original_inputs
    output = {"passed": True, "configurations": len(inputs), "numeric_absolute_tolerance": 1e-9,
              "maximum_raw_difference": max_error, "limited_constraints_passed": feasible,
              "scope": "Synthetic model parity and conservation, not author model reproduction or agronomic validation"}
    dest = ROOT / "test-results/annual-balance/parity.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=ROOT / "src/annual-balance-model.js")
    run(parser.parse_args().model.resolve())
