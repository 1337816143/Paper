# Annual whole-farm teaching panel

All source is original synthetic teaching material. No numerical coefficient is
attributed to FarmDESIGN, FarmM3, Groot 2012 or Qu 2025. Article interpretation and
the source ledger belong to the host guides. This component reads no source PDFs,
private notes, local storage, remote data or credentials.

## Files and integration

Load `src/annual-balance-model.js` before `src/annual-balance-walkthrough.js`, and
include `src/annual-balance-walkthrough.css`. All assets are local and must also be
included in the site's single-file/offline build and service-worker cache.

Mount only in the two new annual-balance guide containers. The host owns routing,
source paragraphs, notes, history scroll positions and release installation:

```js
const controller = window.PaperAnnualBalance.mount(container);
// Include this alongside existing guards before an automatic application update:
if (window.PaperAnnualBalance.isBusy()) postponeUpdate();
```

`mount` is idempotent for a live container. A controller exposes `getState()`,
`getExportData()`, `reset()`, `isBusy()` and idempotent `destroy()`. `getState()` is
a detached snapshot, not a mutation API. `getExportData()` rejects an invalid
current draft. There is no autoplay; `pendingTimer` is always false and temporary
download cleanup is separately reported as `pendingDownloads`.

Busy means any of: advanced stage, changed inputs, invalid draft, opened complete
ledger, input focus, selected panel text, print operation or pending download.
Reset restores exactly 8 equivalent animals, 6 ha forage, chain loss 0.20,
replacement off, first stage and closed ledger. Persistent input elements retain
focus while results update. Input keys use `data-annual-field`, stage buttons use
`data-annual-stage`, and buttons use explicit attributes rather than `dataset.step`.

The panel remembers inputs (including invalid raw text), last valid inputs, stage
and ledger expansion in a page-memory map. Only an opaque `paperAnnualEntry` key
is merged into `history.state`; existing fields, including host scroll position,
are preserved. Native Back returns to that entry; new entries and reloads start
at defaults. There is no promise of persistence across reloads or devices. Hash
and popstate callbacks destroy only when `mountedHash` changed or the container
is detached, so a fresh host remount survives a paired hashchange. MutationObserver
also handles DOM removal and clears all listeners, observers and object URLs.

## Calculation and downloads

The UMD model exposes `calculate`, frozen `defaults`, `domain`, `constants` and
`units`. `calculate` accepts exactly four own keys:

```json
{"herd":8,"forageArea":6,"lossFraction":0.2,"replaceRetained":false}
```

Numeric inputs must be finite number primitives in the reviewed grid; the last
input must be a boolean primitive. It rejects unknown/missing fields, empty/string
inputs, off-step values and out-of-domain values. The UI separately parses only
explicit numeric strings, never blank/whitespace/hex as a number. Validation never
clamps a value. A negative adjusted mineral input is defensively rejected; it is
not reachable in the reviewed grid, which the arithmetic test proves nonnegative.

All result N fields use kg N/year. The five DM flows use Mg DM/year; `cashArea`
uses ha. `feedNitrogenConsumed` includes only on-farm consumption. Imported feed
N is added separately at the animal boundary. Whole-harvest N is subtracted from
soil, with surplus forage exported through the farm gate. Negative soil residual
is retained as an infeasible supply deficit, never an environmental improvement.
Flags use absolute tolerance 1e-9; raw result precision is not rounded.

Downloads are three distinct artifacts:

- `annual-balance-inputs.csv`: exactly the four input columns and one row, with
  lowercase `true`/`false`; compatible with the parent's Python `--input` CLI
- `annual-balance-results.json`: original inputs, fixed constants, units, full
  raw calculation, flags and explicit synthetic/source limitations
- `annual-balance-ledger.csv`: UTF-8 long-format input/constants/result/flags/
  caveats ledger with units; it is not the Python command's input format

The browser's print flow opens the complete ledger, lets the original SVG and
tables fit the print page, and then restores the reader's prior expansion.

## Verification

Run from the integrated repository root:

```sh
node tests/annual-balance/math.test.cjs
node tests/annual-balance/dom.test.cjs
python tests/annual-balance/browser_test.py
```

`math.test.cjs` uses eight independently hand-calculated fixtures, twenty invalid
inputs, exact feed-cap and soil-deficit boundary cases, and all 4,410 reviewed
configurations. Its independent reduced soil equation and separate animal,
manure, harvest and farm balances check more than a copy of one implementation.
The parent additionally owns Python/JavaScript raw-field parity across that grid.

`dom.test.cjs` imports `dom-harness.cjs`, a deliberately minimal DOM simulation.
Eleven tests exercise events, invalid drafts, persistent control identity, guard
states, memory history restoration, printing, downloads and cleanup. It does not
provide real browser, layout, pixels, mobile or screen-reader acceptance.

`browser_test.py` requires Python Playwright **1.55.0** and an installed compatible
Chromium (`python -m playwright install --with-deps chromium` in CI). It uses an
intercepted local fixture, actual native Back/Forward, downloaded bytes, input
focus and keyboard keys, light/dark contrast, 320/375px overflow, SVG text bounds,
offline loaded/file modes, printed PDF and screenshots. The host's full-app
service-worker/private-note/source-byte integration is the parent's separate
`scripts/test_annual_balance_integration.py`.

Browser artifacts go to `test-results/annual-balance` or `ANNUAL_QA_DIR`:
`browser-result.json`, desktop/default/replacement/invalid/deficit screenshots,
light/dark mobile screenshots, `print-ledger.png`, and `current-ledger.pdf`.
`PW_EXECUTABLE_PATH` optionally selects a supported Chromium binary. A launch
failure records `blocked`; a partial run records `failed`, never `passed`.

At isolated handoff on 2026-10-05: JavaScript syntax, arithmetic and eleven
DOM-simulated tests passed; browser script compiled. Actual browser execution
and screenshot inspection are deliberately pending parent CI because this
local execution environment's Chromium socket is known to be blocked.
