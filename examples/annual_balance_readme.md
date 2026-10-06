# One synthetic farm, three boundaries

This is an original teaching program, not FarmDESIGN, FarmM3, author data, or a fertiliser recommendation. It requires Python 3 and only its standard library. The website computes the same ledger in JavaScript. All parameter values are invented; the structural questions are linked to Groot et al. (2012) and Qu et al. (2025).

## Run and inspect

From the downloaded examples directory:

```sh
python annual_balance.py
python annual_balance.py --loss-fraction 0.1
python annual_balance.py --loss-fraction 0.1 --replace-retained
python annual_balance.py --input annual_balance_synthetic.csv --json
python annual_balance.py --test
```

The first three commands describe the same farm. They change the chain-loss fraction first, then explicitly replace mineral N with the additional retained manure N. They produce:

| kg N/year, entire farm | Default | Retain more N | Also replace mineral N |
|---|---:|---:|---:|
| Mineral N input | 920 | 920 | 836 |
| Manure-chain N loss | 168 | 84 | 84 |
| Manure N returned to soil | 672 | 756 | 756 |
| Soil N residual | 552 | 636 | 552 |
| External N input | 1120 | 1120 | 1036 |
| Product N output | 400 | 400 | 400 |
| Farm-gate N surplus | 720 | 720 | 636 |

The final column assumes unchanged harvest and animal products. It does **not** demonstrate that real crops retain their yield after the fertiliser reduction. There is no available-N, yield-response, soil, weather or seasonal mechanism here.

## Units and the fixed teaching inputs

- Total area:10ha. Forage area varies; cash-crop area is10 minus forage area
- Target forage yield:6Mg dry matter/(ha·year). 1Mg=1000kg; dry matter is not fresh weight
- Feed requirement:5Mg dry matter/(equivalent animal·year)
- Common feed N concentration:25kg N/Mg dry matter, for both own and imported feed
- Animal-product N:20kg N/(equivalent animal·year)
- Cash-crop product N:60kg N/(ha·year)
- Mineral N before the optional replacement:100kg N/(forage ha·year),80kg N/(cash-crop ha·year)
- Deposition:10kg N/(ha·year), over10ha
- Imported-feed cap:10Mg dry matter/year
- Reference manure-chain loss fraction:0.20, dimensionless

These are annual accounting coefficients, not feeding standards, measured emission factors or source-paper parameters. Zero feed waste, fixation, bedding, manure imports and stock accumulation are explicit simplifications. The anonymous equivalent animals are not an age-structured cattle herd.

## Trace the calculation

Forage harvested =6×forage area. Feed demand=5×animal count. Own forage consumed is the smaller of harvest and demand. Imports fill a shortage. Any harvest exceeding demand is exported; it never disappears into an unreported stock.

With the default inputs, harvest=6×6=36Mg DM/year and demand=5×8=40. Imports=4. Animal feed N=(36+4)×25=1000kg N/year. Animal products remove8×20=160, leaving840 in excretion. A loss fraction0.20 sends168 to the aggregate chain-loss account and672 to soil.

Soil N residual = mineral N + deposition N + returned manure N − **all harvested** forage N − cash-crop product N. Subtract all harvested forage, including the portion exported rather than fed on the farm. This yields920+100+672−900−240=552.

Farm external input = mineral N + deposition N + purchased-feed N. Farm product output = animal-product N + cash-crop-product N + exported-forage N. Own feed and returned manure are internal transfers and cancel when the boundary expands to the whole farm. In the default example,1120−400=720=168+552.

The soil residual has not been separated into measured leaching, denitrification, runoff or omitted terms. Under the zero-stock-change assumption, the positive balance is assigned to unresolved loss pathways. “720” is a farm-gate surplus, not calibrated environmental pollution. Negative soil residual is flagged as a supply deficit or an incompatible production target, never an environmental benefit.

## The finite interface domain

The interface permits animal count0–20 in steps of1, forage area0–10ha in steps of0.5, loss fraction0–0.20 in steps of0.05, and replacement off/on:4,410 combinations. These ranges make the teaching calculation inspectable; they are not validated agricultural operating limits.

Input must be a finite number on its declared grid. Blank strings, booleans used as numbers, unknown fields and invalid grid values are rejected. The optional replacement cannot produce negative mineral input. Feasibility checks only cover imported-feed capacity and the nonnegative soil supply residual after the validated input bounds; they omit numerous real farm constraints.

The input CSV is exactly one record with four columns:

```csv
herd,forageArea,lossFraction,replaceRetained
8,6,0.2,false
```

The website's “input CSV” is accepted by `--input`. Its complete result JSON/CSV are readable output records, not another input format. Raw numeric outputs are compared before display rounding; the diagram normally displays two decimal places. The model conserves N to an absolute tolerance of1e-9kg/year.

## Boundary cases worth reading

With4 animals,6ha forage and0.20 chain loss, exported forage=16Mg DM/year=400kg N/year. Chain loss=84, soil residual=216, farm surplus=300. Ignoring forage exports would overstate the farm surplus by400.

With0 animals and6ha forage, all36Mg DM are exported. Animal products, excretion and chain loss are zero, while soil residual is−120kg N/year. This is a supply deficit under the fixed production target, not negative pollution.

With12 animals and6ha forage,24Mg DM/year must be imported, exceeding the10Mg cap. A closed N ledger does not make that configuration feasible.

## Original method versus this example

Groot et al. (2012), DOI10.1016/j.agsy.2012.03.012, §2.2 and Fig.1–2, provides annual whole-farm resource balances; its actual model also represents nutrition, organic matter, labour, economics and other resources. Qu et al. (2025), DOI10.1016/j.agsy.2024.104170, §2.2–2.6 and Figs.1–4, connects a detailed manure-management chain to the farm model. It compares source-specific configurations and objectives. Neither paper supplies this toy dataset.

The two website guides provide exact source pages and separate original findings, teaching assumptions and proposed research extensions. Passing the program tests verifies the stated synthetic calculation, not the validity of a real Hainan farm prediction.
