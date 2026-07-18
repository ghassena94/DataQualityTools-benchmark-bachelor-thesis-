# Known Issues — Tool Installation & Runtime Status

This documents which of REIN's 19 error detectors and 11 repair methods actually
run to completion in this repo's Docker setup, based on directly invoking each
method (not just checking that imports succeed) against the `beers` dataset in
the `rein` container.

Last verified: 2026-07-18.

## Fixed in this pass

### katara — FIXED ✅

Two separate bugs, both fixed:

1. **Missing knowledge base path.** The KATARA knowledge base (2018
   `*.rel.txt` relation files) was downloaded to the repo root
   (`./knowledge-base/`), but `rein/detectors.py`'s `katara()` hardcodes
   `cleaners/katara/knowledge-base/`. Fixed with a symlink:
   ```
   cleaners/katara/knowledge-base -> ../../knowledge-base
   ```

2. **Type error on numeric columns.** `cleaners/katara/katara.py`'s
   `domain_spec_col_type()` calls `value.lower()` on every cell, assuming
   all columns are strings. Numeric columns in `beers` (e.g. `ounces`,
   `abv`, `ibu`) crashed with `AttributeError: 'int' object has no
   attribute 'lower'`. Fixed in `rein/detectors.py`'s `katara()` wrapper
   by casting `dirtydf.astype(str)` before calling `run_KATARA`.

**Result:** produces real detections (11,588 on `beers`).

### holoclean — PARTIALLY FIXED ⚠️ (env/DB bugs resolved; one library bug remains, deferred)

Three bugs found and fixed:

1. **Hardcoded `localhost` DB host.** `cleaners/holoclean/holoclean.py`
   defaults `db_host` to `'localhost'`. From inside the `rein` app
   container, Postgres lives in a separate `db` container/service, so
   this connection always failed
   (`psycopg2.OperationalError: connection to server at "localhost" ...
   Connection refused`). HoloClean already reads a `DB_HOST` env var if
   set, and its `db_user`/`db_pwd`/`db_name` defaults
   (`holocleanuser`/`abcd1234`/`holo`) already matched what
   `init-db.sql` provisions. Fixed by adding
   `DB_HOST: db` to the `rein` service's `environment:` block in
   `docker-compose.yml`.

2. **Missing `constraints/` directory.** `rein/detectors.py`'s
   `holoclean()` tries to write
   `datasets/<name>/constraints/_all_constraints.txt`, but never creates
   the `constraints/` directory first. `open(..., 'w+')` raised
   `FileNotFoundError`, which was silently swallowed by a bare `except`,
   so the file was never created — `hc.load_dcs()` then crashed trying to
   read that same missing file. Fixed by adding
   `os.makedirs(dir, exist_ok=True)` before the write, and changing the
   bare `except:` to `except Exception as e:` with the error logged (so
   future failures aren't silently swallowed).

3. **Crash on zero constraints.**
   `cleaners/holoclean/detect/violationdetector.py`'s
   `detect_noisy_cells()` builds a list of per-constraint violation
   dataframes and calls `pd.concat(errors)`. When a dataset has zero
   denial constraints (true for `beers` — see below), `errors` is an
   empty list and `pd.concat([])` raises
   `ValueError: No objects to concatenate`. Fixed by returning
   `pd.DataFrame(columns=['_tid_', 'attribute'])` when `errors` is empty.

**Remaining open issue (not fixed — see decision below):**

File: `cleaners/holoclean/detect/detect.py`,
`DetectEngine.detect_errors()`. After all three fixes above, holoclean
successfully connects to Postgres, loads the dataset (2410 rows / 28920
cells), and loads an empty constraints file. It then fails inside
`detect_errors()`, which has two more spots assuming at least one error
will always be found:

- `errors_df['_cid_'] = errors_df.apply(lambda x: ..., axis=1)` — on an
  empty (0-row) `errors_df`, `.apply(..., axis=1)` returns an empty
  `DataFrame` instead of a `Series` in this pandas version, so assigning
  it into a single new column raises
  `ValueError: Wrong number of items passed 2, placement implies 1`.
- `store_detected_errors()` explicitly does
  `if errors_df.empty: raise Exception("ERROR: Detected errors dataframe
  is empty.")` — "zero violations found" is treated as a hard failure,
  not a valid (if uninteresting) result.

**Root cause:** `beers` (and likely most datasets in this repo) has no
denial constraints (DCs) defined. `rein/auxiliaries/detectors_dictionary.py`
notes as a required signal for `DetectMethod.holoclean`: *"Denial
Constraints"* — none exist for `beers`. Running HoloClean's
violation detector with zero DCs is exactly what triggers both crashes
above; this is a structural assumption in the vendored HoloClean library
itself (it was never written to handle "no errors found" as a valid
outcome), not a Docker/environment problem.

**Two ways to actually finish this** (deferred — not done, per decision
to keep studying the benchmark before investing further fix time):

- **Patch `detect.py`** to treat zero detected errors as a valid
  outcome (guard the `.apply()` call; remove/soften the hard `raise` in
  `store_detected_errors`). Estimated ~30–45 min. Makes holoclean *run*
  on any dataset, but produces trivial (0-detection) results wherever DCs
  are missing — doesn't make holoclean *useful* there.
- **Author real denial constraints** for each dataset that's supposed to
  use holoclean (per `detectors_dictionary.py`, that covers the
  `missing_values`, `pattern_violation`, `rule_violation`, and `typos`
  error-type categories — i.e. most datasets, including `beers`). This is
  the "correct" fix per the README's own extension instructions
  (`Adding a dataset` section), but it's a data-authoring task requiring
  domain understanding of each dataset's columns, not a code fix.

## Other detectors/repair methods (from the broader audit, not re-verified after the fixes above)

Based on directly invoking each method against `beers` before the katara/holoclean
fixes were made. Config-only failures (my probe script didn't always pass the
same config keys `benchmark.py`'s real pipeline supplies) are marked *inconclusive*.

### Detectors (19 total)

| Method | Status | Notes |
|---|---|---|
| `raha` | ✅ working | real precision/recall/F1 |
| `fahes` | ✅ working | C++ lib compiles and runs; real metrics |
| `nadeef` | ✅ working | REIN's own Python reimplementation, not the Java tool |
| `max_entropy` | ✅ working | |
| `min_k` | ✅ working | |
| `mvdetector` | ✅ working | |
| `duplicatesdetector` | ✅ working | |
| `katara` | ✅ **fixed above** | |
| `holoclean` | ⚠️ **partially fixed above** | DC-less datasets still crash |
| `zeroer` | ⚠️ dependencies work, unconfigured | py_entitymatching/xgboost run fine, but `beers` has no blocking function configured, so it brute-forces ~5.8M candidate pairs and never finishes in practical time (eventually OOM-killed after 20+ min in testing) |
| `ed2` | ❌ broken | `cleaners/ed2/model/ml/datasets/` (the `SpecificDataset` module) doesn't exist anywhere in the vendored source tree — incomplete checkout |
| `dboost` / `metadata_driven` | ❌ broken | `cleaners/dBoost/dboost/utils/tupleops.py` is a 5-line stub missing `defaultif_masked`, `deepapply_masked`, `pair_ids`, `make_mask_abc` that `analyzers/statistical.py` imports — vendored dBoost source incomplete |
| `openrefine` | ❌ broken (for `beers`) | needs a per-dataset `datasets/beers/clusters` file that was never generated |
| `picket` | ❌ broken | blew up to >21GB RAM and got OOM-killed before producing a result |
| `outlierdetector`, `mislabeldetector`, `activeclean`, `cleanlab` | ❓ inconclusive | probe passed wrong/incomplete config keys; likely fine via the real `detect_errors.py` pipeline |

### Repair methods (11 total)

| Method | Status | Notes |
|---|---|---|
| `cleanWithGroundTruth` | ✅ working | |
| `duplicatesCleaner` | ✅ working | |
| `dcHoloCleaner` | ⚠️ blocked by holoclean issue above | shares the same root cause |
| `baran` | ❌ broken | crashes partway through (after sampling/labeling a tuple) with `TypeError: 'numpy.int64' object is not iterable` — looks like an old-numpy assumption in the vendored raha/baran code |
| `boostClean` / `CPClean` | ❌ broken on multi-class data | `AttributeError: 'Models' object has no attribute 'shape'`, preceded by `"Invalid dataset: more than two classes"` — the vendored CPClean code appears to only support binary classification; `beers`' label (`brewery_name`) has ~700 classes |
| `standardImputer`, `mlImputer`, `activecleanCleaner`, `cleanlab` (repair) | ❓ inconclusive | probe passed wrong/incomplete config keys (`method`, `sampling_budget`, `model`); likely fine via the real `repair_errors.py` pipeline |

## How to reproduce these tests

Each method was invoked directly (bypassing `benchmark.py`'s config-supplying
logic, so some "failures" above are probe artifacts rather than real bugs — see
inconclusive rows) via a small script instantiating `rein.detectors.Detectors`
/ `rein.cleaners.Cleaners` directly and calling each method with the `beers`
dataset. To get a fully accurate picture for methods marked inconclusive, run
them through the real pipeline instead:

```shell
docker compose run --rm rein \
    python3 scripts/detect_errors.py --dataset_name beers --detect_method <method> --n_iterations 1

docker compose run --rm rein \
    python3 scripts/repair_errors.py --dataset_name beers --repair_method <method> --n_iterations 1
```
