# Block D: implementation requirements for `blockd_driver.py` and `blockd_analysis.py`

**Date:** 13 Oct 2026. **Status:** implemented 13 Oct in `scripts/blockd_driver.py`, `scripts/blockd_analysis.py`, `scripts/tests/test_blockd.py` (review log §17).

**What governs what:**
- The final plan v2.1, `reports/block_d_final_plan_2026-10-09.md`, governs. It is cited as "plan §n Lk" (section n, line k of that file).
- Where the plan is silent, the server plan `reports/server_plan_2026-10-13.md` applies ("srv Lk").
- The old spec `reports/block_d_driver_spec_2026-10-06.md` ("spec §n Lk") is used only where the plan does not differ. §16 lists where the documents conflict.

**Code cited** (paths under `reports/block_d_final_plan_2026-10-09/checks/` unless a full path is given):
- `decisions/mini_driver.py` ("mini Lk");
- `measure_fixes.py` ("MF Lk"), `implied_predictions.py` ("IP Lk"), `reference_rankings.py` ("RR Lk");
- `addendum_raha_run1/` ("addendum");
- `scripts/blockd_freeze_flags.py` ("freeze Lk").

**How to read the list:**
- Every requirement R*n* is meant to be testable. It names what must hold and, where possible, the number or output that shows it.
- "A*n*" points to the ambiguity table (§15), which gives the reading chosen and the reason for it.

**Never, while implementing or testing:**
- edit plan §9, `checks/expected_pair_verdicts.csv` (frozen in c61ee72), `reports/block_d/flags/`, `rein-datasets/` or `reports/block_d/backup_*`;
- write to `results/`;
- train on the real datasets outside the user's own step-by-step runs. Synthetic self-tests, `--dry_run` and import checks are allowed.

---

## 0. Starting point: what `mini_driver.py` already does

| Part | mini_driver (D2–D8 decision runs) | What the driver must do |
|---|---|---|
| Loading | `dtype=str, keep_default_na=False` (mini L36–37) | keep |
| Flag sets | replays GE and HoloClean; reads Raha from the **disk file**, not run 1 (mini L48–52) | read the **frozen** files and check them (R18–R23) |
| Model-column restriction, item merge | mini L47, L53–58 | keep; name items and pairs exactly as IP L64–69, L116 do |
| Numeric rule | `'90'` / `'all'` option (mini L42–44) | fixed at ≥ 90 % (D4) |
| Split | mini L63–66 | keep |
| Policies | floor / gt / delete / impute, D2 kept-row statistics, mode, `'0.0'` / `'__none__'` (mini L68–103) | keep the semantics; use masks instead of Python loops (R46); add test-row policies for S1/S3 (R45) |
| Featurization | mean/median fill, clean test filled with the version's statistic, one-hot (mini L105–115) | keep |
| `train_hash` | rounded X, but unrounded y, no shape, 16 hex digits (mini L118–120) | change (R54) |
| Models | mini L123–128 | keep, `random_state=0` (D3) |
| Scoring | S2 only; a degenerate version returns `None`; a NaN label is treated as degenerate (mini L131–147) | add floor, S1, S3, S4, precision/recall, R², all §11 columns; **an unparsable label aborts** (R28) |
| Pair rule | exact sign-flip test on midranks; direction from the median of d (mini L150–170) | keep the test; direction = sign of T (A14); integer arithmetic (R83) |
| Missing | — | always-positive, D6 version, random control, checks 1–4, MANIFEST check, CLI, outputs, environment record, `--jobs`, dry run, the whole analysis |

---

## 1. General rules and code style

- **R1.** Two files: `scripts/blockd_driver.py` and `scripts/blockd_analysis.py`.
  - Each opens with a docstring header like freeze L1–17: purpose, inputs, outputs, and the run command in the rein container from `/rein`.
  - Then `import sys; sys.dont_write_bytecode = True` (freeze L17–18).
  - Plain module-level functions; dataset constants in module-level dicts, so the self-tests can substitute a synthetic dataset. No new classes are needed.
- **R2.** Dependencies: only the image's packages and the standard library. The image has Python 3.8.10, numpy 1.21.2, pandas 1.3.3, scikit-learn 0.24.2, scipy 1.7.1, xgboost 1.3.3 and threadpoolctl 3.1.0 (`requirements.txt`; import check 13 Oct). Nothing new is installed.
- **R3.** Reuse the replay helpers and constants (`CFG`, `TABLE3`, `CONFIGS`, `ge`, `holo`, `prof`, `hw`, `read_cells`, `tp_fp`, `isnum`) by executing only the part of `measure_fixes.py` before `report = {}` (freeze L26–28, mini L22–25).
  - Never execute the rest of MF: it writes `measure_fixes.json` (MF L275).
  - Never execute IP: it rewrites the frozen `expected_pair_verdicts.csv` in place (IP L125; srv §8 item 10).
- **R4.** Never import `rein.benchmark`, `rein.models`, datawig or REIN's training code (spec §1 L6; plan §10 item 2).
  - Importing datawig resets NumPy's global seed to 42.
  - No code uses the global NumPy or `random` state. Every random draw uses an explicit seed: the split's `random_state`, the models' `random_state=0`, and the control's `default_rng`.
- **R5.** Container paths: the repo is at `/rein` and the datasets at `/rein/datasets` (srv L545).
- **R6.** The exit code is 0 only on success. Any failed check or exception exits non-zero, and the last stdout line is `DONE <mode> …` or `FAIL <check> …`.

## 2. Driver CLI

- **R7.** Arguments:

| Argument | Rule | Ref |
|---|---|---|
| `--datasets` | `nargs='+'` from {breast_cancer, nasa, bike, adult}; default `breast_cancer nasa` | spec §2 L11; srv L442–447 |
| `--flags_dir` | required; read-only; holds `<ds>/<config>.csv` and `MANIFEST.csv` | srv L442–444 |
| `--data_root` | default `/rein/datasets` | spec §2 L13 |
| `--out` | required; see R8 | spec §2 L14; srv L395 |
| `--policies` | `nargs='+'` from {gt, delete, impute}; default all three. The floor and S4 always run; controls run only when `delete` is selected. Checks build the versions they need regardless. | task; plan §4 |
| `--fill` | `mean` (default) or `median`; it sets both the featurization fill and the impute statistic | plan §8.8 L216; D5 L325 |
| `--seeds` | default `0-9`; takes ranges (`0-9`) and lists (`0 1 2`) | spec §2 L15 |
| `--jobs` | int, default 1; parallel over (dataset, seed); production uses 1 | spec §2 L17; srv L53 |
| `--dry_run` | no fitting; see §12 | plan L17; srv L235 |
| `--check` | dry run plus the training part of check 2; see R58 | spec §2 L19; srv L443 |

`--dry_run` and `--check` are mutually exclusive.

- **R8.** `--out` must resolve to a directory inside `/rein/reports/block_d/runs/` that does not exist yet or is empty; otherwise refuse (A20). This also rules out `results/`, `rein-datasets/`, `reports/block_d/flags/` and the backup.
- **R9.** `manifest.json` records `sys.argv` and the parsed arguments.

## 3. Environment, determinism and the environment record

- **R10.** At start-up, in every mode, abort unless `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` are `'1'` and `PYTHONHASHSEED` is `'0'` (srv L49–51).
  - After importing numpy, scipy.linalg, sklearn and xgboost, `threadpoolctl.threadpool_info()` must report `num_threads == 1` for every pool; otherwise abort.
  - Measured 13 Oct with these settings in the Mac container: 4 pools (2 OpenBLAS, 2 OpenMP), all with 1 thread.
- **R11.** `REIN_IMAGE_ID` is required for full and `--check` runs (abort without it) and recorded when present in a dry run (A19). `OPENBLAS_CORETYPE` is optional and recorded.
  - **Measured 13 Oct:** the two OpenBLAS libraries in the Mac container report different architectures (`Nehalem` and `Atom`). Under srv L129–132, P0 step 4 therefore writes no `openblas_coretype.txt`, and the `OPENBLAS_CORETYPE` part of `$BD` must be dropped (srv L393). This is a flag for the user, not a driver rule.
- **R12.** `manifest.json` → `environment` records (srv L54, L129–131, L236; spec §8 L94–99):
  - `socket.gethostname()`, `platform.machine()` and `platform.platform()`;
  - the versions of Python, numpy, pandas, sklearn, scipy, xgboost and threadpoolctl;
  - the full `threadpool_info()`;
  - numpy's `__cpu_features__` (from `numpy.core._multiarray_umath`; 12 of 46 true under emulation, 13 Oct);
  - `len(os.sched_getaffinity(0))`, and `os.cpu_count()` labelled unreliable (sitecustomize fixes it at 10);
  - the five variables of R10–R11 and `REIN_IMAGE_ID`;
  - `git rev-parse HEAD` and `git status --porcelain` (git 2.25.1 is in the image);
  - the result of `git diff --quiet c61ee72 -- reports/block_d_final_plan_2026-10-09/checks/expected_pair_verdicts.csv`. A non-empty diff aborts; if git cannot run, the driver warns and records `unknown`.
- **R13. Determinism.**
  - The same inputs and arguments give byte-identical `results.csv` apart from `fit_s` and `timestamp`, for any `--jobs` value and on either machine (V4d, srv L44).
  - Rows are sorted by a canonical key before they are written.
  - No iteration over an unordered set may affect any output: cells are sorted as (row, col).
  - Worker processes use the `multiprocessing` `'spawn'` context, because forking after OpenMP has started can deadlock.
- **R14. Random control draw:** exactly `rng = np.random.default_rng([seed, c_idx])` and then `rng.choice(train_ids_sorted, size=k, replace=False)` (plan §4 L109).
- **R15.** Floats are written with `repr()`, so that they round-trip exactly; `results.csv` is never rounded. V4d compares the text.

## 4. Inputs and their validation (check 1)

- **R16. Input copies** (spec §3 L23; srv L237):
  - Copy `dirty.csv`, `clean.csv`, `actual_errors.csv` and the five `<config>.csv` files of each dataset into `<out>/inputs/<ds>/`, and `MANIFEST.csv` once into `<out>/inputs/`.
  - Record the sha256 of each copy, and read only the copies.
  - Record the sha256 of these without copying them: `rein-datasets/<ds>/constraints/<ds>_dcs.txt`, `rein/auxiliaries/expectations_profiler.py`, `rein/auxiliaries/expectations_dictionary_local.py` (the replay inputs), `checks/measure_fixes.py`, the frozen `checks/expected_pair_verdicts.csv` (plan §11 L289), and the addendum's `expected_pair_verdicts_raha_run1.csv` and `measure_fixes.json`.
  - Separately from the scripts: add `/reports/block_d/runs/*/inputs/` to `.gitignore` before the first committed run (srv L237).
- **R17.** CSVs are read with `dtype=str, keep_default_na=False`. Assert that `clean.csv` and `dirty.csv` have the same columns in the same order and the same shape (MF L131).
- **R18. Flag files** have no header. Only columns 0 (row) and 1 (column) are used, as integers; a third column is ignored. A 0-byte file is the empty set: catch `EmptyDataError` (MF L104–109; spec §3 L24–25).
- **R19. Check 1a, MANIFEST** (plan §7 L166–167; srv L41):
  - For every requested dataset × each of the 5 configurations there is exactly one row in `MANIFEST.csv`.
  - The sha256 of the copied file equals the MANIFEST `sha256`.
  - The MANIFEST `detections/tp/fp` equal `TABLE3` (MF L40–45), and both equal `tp_fp(cells, actual_errors)` recomputed from the file.
  - Otherwise print `CHECK 1 FAIL <ds> <config> <what>` and abort.
- **R20. Check 1b:** no duplicate cell and no cell outside the n × d table (freeze L66–72).
- **R21. Check 1c, replay identity** (plan §7 L168–169; D8 L328):
  - The GE dirty-profiled, clean-profiled and hand-written sets and the HoloClean set are cell-identical to the replay (`replay()`, freeze L35–46), on all four datasets.
  - adult HoloClean too.
  - Raha has no replay, so its counts are the whole check.
- **R22. Expected Table 3 counts** (TP/FP/detections; MANIFEST rows 1–20):
  - bc 247/13/260, 278/13/291, 438/22/460, 416/5,275/5,691, 317/78/395;
  - nasa 30/0/30, 384/0/384, 680/0/680, 556/5,709/6,265, 710/1,864/2,574;
  - bike 0/0/0, 0/0/0, 24,247/0/24,247, 25,134/173,845/198,979, 30,861/15,138/45,999;
  - adult 0/0/0 ×3, 1,677/663,530/665,207, 865/5,081/5,946.
- **R23.** The Raha figures in plan L17 and §5 come from the disk file. The driver uses frozen run 1 and must not compare against the disk-file numbers (§16 C5).

## 5. Schema and featurization

- **R24. Model columns** = every column except `CFG[ds]['excl']`. The label is `CFG[ds]['label']` and the positive class `CFG[ds]['pos']` (MF L34–39).
  - Expected: bc 9 features + `class`; nasa 5 + `sound_pressure_level`; bike 12 + `cnt`; adult 14 + `income` (plan §2 L64–69).
  - Any other count aborts.
  - Excluded columns are never features, are never changed by any policy, and are never counted in `cells_changed` or `errors_left_*` (spec §12 L158).
- **R25. Numeric rule (D4, plan §2 L71, L324).** A feature column is numeric if at least 90 % of all rows of `clean.csv` pass `isnum`; otherwise it is categorical. The schema is fixed once per dataset from `clean.csv`.
  - Expected: bc 9 numeric (`Bare Nuclei` numeric), nasa 5, bike 12, adult 6 numeric + 8 categorical.
  - The dry run prints the schema.
- **R26. Parsing.** `isnum` as in MF L117–124: `''` and non-finite values do not parse. The parsed value is `float(text)`.
  - mini uses `pd.to_numeric` after the same filter. Checked 13 Oct: in all eight CSVs no value is accepted by `float()` but would be read differently (no underscores, padding, hex or `+`), so the two agree.
- **R27. One label encoder** (plan §10 item 2; memory note rein-labelencoder-bug):
  - One fixed map per dataset, applied identically to every array (clean, dirty, every version, train and test).
  - Classification: 1 if the text equals `pos` (bc `'4'`, adult `'0'`); 0 if it equals the other clean class (bc `'2'`, adult `'1'`); any other text is unparsable.
  - Regression: `float`.
  - No encoder is ever fitted per array.
  - Checked 13 Oct: the dirty and clean labels contain only {2, 4} (bc) and {0, 1} (adult).
- **R28. Unparsable labels abort** (plan §2 L77). Abort if a kept training row or a scored test row has an unparsable label after the policy. Never map it to 0 or to the mean, and never mark the version degenerate instead (unlike mini L135).
- **R29. Featurization** (plan §2 L72–76; mini L105–115). It is fitted on the kept training rows of each version:
  - **Numeric block,** in file order: parsed values, with NaN filled by the version's statistic. That is the mean, or the median under `--fill median`, of the parsed kept training values, or 0.0 if there are none.
  - **Categorical block,** in file order: `OneHotEncoder(handle_unknown='ignore', sparse=False)` fitted on the kept training text, with categories in sorted order (the default).
  - The matrix is dense float64: `[numeric | one-hot]`.
- **R30.** The version's fitted featurizer transforms all of its test matrices: S1 test rows and the S2 clean test split. A NaN in a numeric test cell gets the version's training statistic (mini L110). Unknown categories become all-zero. The clean model's featurizer transforms the S3 and S4 test rows.
- **R31.** `StandardScaler` is fitted on the training matrix and applied only for the linear model (mini L138–146).
- **R32.** Featurized width at seed 0 for the floor: bc 9, nasa 5, bike 12, adult 104 (`decisions/d7_fit_times_output.txt`). The dry run prints it; the self-test checks the layout.

## 6. Flag sets, items and versions

- **R33. Flag sets per dataset** (plan §3 L81–86):
  - the 5 frozen configurations;
  - `perfect` = `actual_errors.csv`;
  - `always_positive` = every cell of the n × d table.
  - Each set is restricted to the model columns before any use. Flags in excluded columns are counted (`excl_col_flags`), never applied.
- **R34. Items** (plan §3 L90–93, fix 3 L27; IP L64–69, L116):
  - Group `CONFIGS` by identical restricted sets, in `CONFIGS` order. An item's name is `'='.join(SHORT[c])`.
  - Pairs = `itertools.combinations(items)` in that order, so that pair keys match `expected_pair_verdicts.csv`.
  - Expected items/pairs: bc 5/10, nasa 5/10, bike 4/6 (`GE-dirty=GE-clean`), adult 3/3 (`GE-dirty=GE-clean=GE-hand`). Any other count aborts.
  - Perfect, always-positive, the floor, S4, the controls and the D6 version are never items.
- **R35. D6 diagnostic** (plan §3 L88; D6 L326; §16 L367): on **nasa only**, `raha_minus_format_only` = Raha's model-column flags minus its format-only FPs (definition: R36).
  - The dry run asserts 710 TP, 0 FP and ≠ perfect, or aborts.
  - It is trained under the selected policies with all scenarios and has no control.
  - It is reported beside the ranking, never ranked and never counted in a pair (A8).
- **R36. Format-only FP** (A1): a flagged model cell that is not in `actual_errors.csv` and whose dirty text differs from its clean text (`scripts/blockd_check_format_only.py` L30; `decisions/d6_format_only.py`).
  - The dry run also counts how many of them are not numerically equal (`math.isclose(rel_tol=1e-6)`). Expected 0; anything else is printed as a warning.
  - Expected with run 1 (model columns): nasa Raha 1,864, bike Raha 2,330 (addendum `measure_fixes.json`, `format_only_fp_schema`).
- **R37. Versions per dataset and seed** (plan §11 L291; spec §5 L52–53):
  - `floor` (no detection, the dirty data as shipped);
  - `clean` (S4);
  - 7 flag sets × the selected policies;
  - on nasa, the D6 version × the selected policies;
  - one control per configuration when delete is selected.
  - With all policies that makes 27 (+3 on nasa).
- **R38. Random control** (plan §4 L107–111; fix 4 L28):
  - k = the number of training rows that configuration c's delete version removes (model-column flags) in seed s.
  - c_idx = `CONFIGS.index(c)` (0–4; A7). Draw as in R14; the kept rows are the rest, sorted.
  - k = 0 must give a version hash-identical to the floor (part of check 3).
  - The control is degenerate if c's delete version is degenerate in that seed, or if the control itself fails the rule of R52.
  - It is scored in S2 only.
- **R39. Canonical version order,** used for sorting and for choosing the reuse representative: `clean`, `floor`; then for gt, delete and impute in turn: the configurations in `CONFIGS` order, `perfect`, `always_positive`, `raha_minus_format_only`; then the controls in `CONFIGS` order.

## 7. Policies (training split only; plan §4 L95–111)

- **R40. Floor:** all training rows, dirty values.
- **R41. Ground-truth repair:** each flagged model cell of a training row, label included, gets its clean text. All rows are kept.
- **R42. Delete:** drops each training row with at least one flagged model cell, feature or label.
- **R43. Impute:**
  - **Kept rows** = the training rows without a flagged label. Labels are never imputed (plan §4 L101; fix 6 L30).
  - **A flagged numeric feature cell of a kept row** gets the mean, or the median under `--fill median`, of the parsed values of the **unflagged parsable** cells of that column in the **kept** rows (D2 L322), or 0.0 if there are none.
  - **A flagged categorical cell** gets the mode of the unflagged cells' text in the kept rows. On a tie, pandas `mode()` order decides (the smallest value); with no unflagged cell, `'__none__'`.
  - **Unparsable flagged cells are imputed too** (mini L91–102); this is what makes floor equivalence hold (plan §4 L106).
  - **The statistic never comes from `clean.csv` or from the test rows** (plan §4 L104).
- **R44.** The imputed numeric value equals `float(statistic)` exactly. *(Corrected in review, 13 Oct.)* mini's values can differ in the last bits (≤ 7.5·10⁻¹⁵ relative, mean fill only, measured in review): mini writes `repr(statistic)` as text and re-parses it with `pd.to_numeric`, whose parser is not correctly rounded for 17-digit strings (synthetic check: 865 of 20,000 means off by one ulp; `float(repr(x)) == x` always). Acceptance step 3 (4 decimals) is unaffected.
- **R45. Test rows for S1/S3** (spec §6 L58; A16): the version's policy is applied to its test rows.
  - Ground-truth repair: flagged test cells get their clean text.
  - Delete: flagged test rows are dropped.
  - Impute: flagged test feature cells get the **training** statistic of R43, and test rows with a flagged label are dropped.
  - Floor: the dirty test rows.
  - Controls have no S1/S3.
- **R46. Building versions is vectorized:** each flag set becomes an n × d boolean mask once, with no per-cell Python loops over flags (spec §11 L144). adult HoloClean has 665,207 flags and always-positive 678,330.

## 8. Split, models, scenarios, scores, degenerate rule

- **R47. Split** (plan §6 L144–147; mini L63–66): `train_test_split(np.arange(n), test_size=0.2, random_state=seed, stratify=<encoded clean labels> if classification else None)`. Both index arrays are sorted and shared by every version.
  - n_train: bc 559, nasa 1,202, bike 13,903, adult 36,177.
- **R48. Models** (plan §6 L148–152; D3 L323; mini L123–128):
  - classification: `LogisticRegression(max_iter=5000)`, `RandomForestClassifier(random_state=0, n_jobs=1)`, `XGBClassifier(random_state=0, n_jobs=1, use_label_encoder=False, eval_metric='logloss', verbosity=0)`;
  - regression: `Ridge()`, `RandomForestRegressor(random_state=0, n_jobs=1)`, `XGBRegressor(random_state=0, n_jobs=1, verbosity=0)`.
  - Defaults otherwise, no tuning, dense input.
- **R49.** `ConvergenceWarning`s are counted per dataset × model and recorded in the manifest (spec §7 L79). Other warnings are suppressed.
- **R50. Scenarios** (plan §6 L153–158; A16):

| Scenario | Model | Test rows | Labels |
|---|---|---|---|
| S1 | the version's model | the version's test rows (R45) | the version's |
| S2 (ranks) | the version's model | the full clean test split | clean |
| S3 | the clean model | the version's test rows | the version's |
| S4 | the clean model | the clean test split | clean |

  - The floor is scored S1/S2/S3.
  - `clean` writes only S4.
  - Controls write only S2.
- **R51. Scores** (plan §6 L159–162):
  - Classification: F1, precision and recall with `pos_label=1, zero_division=0`; `score` = F1.
  - Regression: RMSE = `sqrt(mean_squared_error)` and R²; `score` = −RMSE.
- **R52. Degenerate** (plan §5 L117; spec §6 L72):
  - A version is degenerate if it keeps fewer than 50 training rows or, for classification, only one class.
  - Then no model is fitted, `degenerate=1`, and every metric and `train_hash` are empty (A12). Its rows are still written for every scenario.
  - S1/S3 are `test_degenerate=1`, with empty metrics, when their test set is empty, has one class (classification) or has fewer than 2 rows (regression).
- **R53. Degenerate cases expected** (plan §5 table L121–129, Raha now run 1):
  - HoloClean under delete on all four datasets;
  - bc and bike HoloClean under impute;
  - nasa Raha under delete;
  - always-positive under delete and impute everywhere.
  - The dry run prints the list. A mismatch with this list is reported, not an abort.

## 9. Hashing and training reuse

- **R54. `train_hash`** (plan §7 L179–181; A12): sha256 over
  - the matrix shape (two int64);
  - the training matrix, each value replaced by `float('%.12g' % v)` and −0.0 turned into 0.0, as C-order float64 bytes;
  - then the labels as float64, rounded the same way.
  - Written in full (64 hex). Excluded columns are never in the matrix.
- **R55. Reuse** (plan §0 L39, §11 L293; A15):
  - Per dataset × seed, build every version first and group the versions by `train_hash`.
  - Fit each model once per group, on the group's representative (the first version in R39 order).
  - Predict each member's own test matrices with that model. Models are reused, scores are not.
  - Members other than the representative get an empty `fit_s`; the manifest records the reuse map.
  - Reuse is switched off in `--check`.
- **R56.** Reuse expected, printed, not checked:
  - perfect + GT and always-positive + GT share `clean`'s hash;
  - zero-flag items share the floor's hash under every policy;
  - bc GE clean-profiled + impute is byte-identical to the floor;
  - bc and nasa GE dirty-profiled + impute share the floor's hash only if their rounded matrices agree;
  - **nasa GE clean-profiled + impute must not** share the floor's hash (fix 8 L32; §4 L106).

## 10. Checks (plan §7 L164–181; every mode)

- **R57. Order and failure** (plan §7 L164):
  - Order: check 1 (R19–R21) before any version is built; then the versions; then checks 3 and 4 and the hash part of check 2 for every seed; only then training.
  - On any failure: print `CHECK <n> FAIL <ds> [seed] <detail>`, write `manifest.json` with `status: failed`, and exit non-zero.
- **R58. Check 2,** perfect + GT and always-positive + GT equal S4 (plan §7 L170–173):
  - *In every mode:* their training matrices and labels are identical to `clean`'s **before rounding**, and their `train_hash` equals `clean`'s, for every seed.
  - *Training part, `--check` only:* perfect + GT, always-positive + GT and `clean` are fitted separately (no reuse) for every seed × model, and S2 equals S4 as an exact float.
- **R59. Check 3,** empty flag set = floor (plan §7 L174):
  - A synthetic empty set under gt, delete and impute gives the floor's matrix, identical before rounding, on every seed.
  - So does every zero-flag configuration (bike GE dirty/clean-profiled, adult GE ×3) and every control with k = 0.
- **R60. Check 4, delete** (plan §7 L175–176): perfect + delete keeps exactly n_train minus the training rows that have a model-column error. The expected value is recomputed directly from `actual_errors.csv`, for every seed.
- **R61. Check 4, impute** (plan §7 L177; A5): for perfect + impute,
  - the kept rows are exactly the training rows minus those with a label error;
  - the set of cells written is exactly the set of flagged feature cells in the kept rows;
  - every unflagged kept cell is text-identical to `dirty.csv`;
  - every written numeric cell equals its column's statistic of R43;
  - the number of parsable written cells is printed.
- **R62. Implementation cross-check, beyond the plan.** All these quantities are independent of the fill. The driver's numbers must equal the addendum `measure_fixes.json`; a mismatch aborts:
  - per seed: rows kept under delete and impute, for every configuration including perfect and always-positive (`per_seed.delete_schema`, `per_seed.impute`), and the label errors left under impute (`label_errors_left_impute`);
  - per configuration: `excl_col_flags`, `format_only_fp_schema`, `label_flags`, `rows_touched_schema_without_format_only` and `feature_tp_parsable`.

## 11. Outputs

- **R63. Files in `<out>`:**

| File | Written in |
|---|---|
| `results.csv` | full runs |
| `manifest.json` | every mode |
| `checks.txt` | every mode |
| `run.log` | every mode (copy of stdout) |
| `dryrun.txt` | every mode (review 13 Oct: full and `--check` runs write it too, so a full run's digests can be diffed against a dry run) |
| `inputs/` | every mode (R16) |

  - Each file is written to a temporary name and renamed when complete. Nothing is ever appended to an existing `results.csv`.
- **R64. `results.csv` columns, in this order** (plan §11 L287; A6):
  `dataset, task, fill, version, item, configuration, policy, model, seed, scenario, score, f1, rmse, r2, precision, recall, rows_kept, test_rows, cells_changed, excl_col_flags, format_only_fp, rows_touched_without_format_only, parsable_tp, parsable_fp, errors_left_in_features, label_errors_left, flagged_label_cells, degenerate, test_degenerate, train_hash, fit_s, timestamp`
- **R65. Column definitions.** Whole-dataset columns describe the flag set and are the same in every seed (A2). Per-seed columns describe the training data of one seed.

| Column | Definition |
|---|---|
| `task` | `classification` or `regression` |
| `fill` | `mean` or `median` (A6) |
| `version` | `floor`; `clean`; `<configuration>/<policy>`; `control/<configuration>` |
| `item` | the merged item name for the 5 configurations; otherwise `perfect`, `always_positive`, `raha_minus_format_only`, `floor`, `clean` |
| `configuration` | one of `CONFIGS`, `perfect`, `always_positive`, `raha_minus_format_only`, or `none` |
| `policy` | `gt`, `delete`, `impute`, `control` or `none` |
| `score` | oriented: F1, or −RMSE |
| `f1`, `precision`, `recall` / `rmse`, `r2` | raw metrics; the other task's columns stay empty |
| `rows_kept` | per seed: training rows after the policy |
| `test_rows` | rows scored in that scenario |
| `cells_changed` | per seed: model cells of the kept training rows whose value differs from `dirty.csv` under the value comparator (A3). The floor and controls have 0; `clean` counts its differences from the dirty data. |
| `excl_col_flags` | whole dataset: flags in excluded columns (MF L166) |
| `format_only_fp` | whole dataset: R36, model columns |
| `rows_touched_without_format_only` | whole dataset: rows with at least one model-column flag that is not format-only (bike Raha disk file 16,198 − 15,951 = 247, plan L26) |
| `parsable_tp`, `parsable_fp` | whole dataset, as in IP L89–90: flagged **feature** cells in / not in the model-visible truth A_mv whose dirty text passes `isnum` |
| `errors_left_in_features` | per seed: feature cells of the kept training rows whose value after the policy, **parsed and before the featurization fill**, differs from the clean value (plan L36; A4). The floor counts every visible feature error in its training rows. |
| `label_errors_left` | per seed: kept training rows whose label differs from the clean label (plan L35) |
| `flagged_label_cells` | whole dataset: flagged label cells (A18) |
| `degenerate`, `test_degenerate` | 0 or 1 (R52) |
| `train_hash` | R54; empty when degenerate |
| `fit_s` | fit time of this version's model; empty when reused |
| `timestamp` | UTC ISO time of the fit |

  The six flag-statistic columns (`excl_col_flags` … `flagged_label_cells`) are empty for `floor`, `clean` and the controls, which apply no flag set (A25).

  **Value comparator** (used by `cells_changed`, `errors_left_in_features`, `label_errors_left`):
  - numeric columns and regression labels: parse both values (NaN if unparsable); they are equal if both are NaN, or both are finite and `math.isclose(rel_tol=1e-6)`;
  - categorical columns and classification labels: the text (or the encoded label) is equal.

  **Model-visible truth A_mv** (references (c) and (d), `parsable_*`) is reproduced exactly as in RR L46–50 and IP L51–56: an error cell is model-visible if either side does not parse or the values are not close.

- **R66. Row count, asserted at the end of each dataset.** Per seed × model, with P = the number of selected policies:
  - 1 (S4) + 3 (floor) + 21·P (7 flag sets × 3 scenarios) + 3·P on nasa (D6) + 5 controls if delete is selected.
  - With P = 3: 72 rows (81 on nasa); the total is that × 3 models × the number of seeds.
- **R67. `manifest.json`** (plan §11 L289; spec §8 L94–101; srv L236):
  - `mode`, `status`, args, environment (R12), and the sha256 of every input (R16);
  - expected vs recomputed TP/FP/detections per configuration, the item map, the degenerate list (all seeds and partial), the reuse map;
  - the sha256 of the frozen and the addendum expected-verdict files;
  - convergence-warning counts, wall time per dataset, and the D6 counts.

## 12. Dry run: what it does and prints

- **R68.** `--dry_run` runs everything except fitting: inputs, check 1, all versions for every seed, featurization and `train_hash`, checks 3 and 4, the hash part of check 2, R62, the references and the expected verdicts. It writes `dryrun.txt` and `manifest.json`, but no `results.csv`.
- **R69. `dryrun.txt`** contains only data-derived text, so that the Mac and server files can be diffed directly (srv L235, L244; P3.2 L442). No timings, timestamps, absolute paths, hostnames, out-directory names, versions or environment values. Sections, per dataset:
  1. **Schema:** n, n_train, n_test; label and positive class; numeric, categorical and excluded columns; featurized width at seed 0.
  2. **Flag table** per configuration, plus perfect, always-positive and D6:
     - detections/TP/FP over all columns;
     - model-column flags;
     - `excl_col_flags`, `format_only_fp` (and the non-equal count of R36), `rows_touched_without_format_only`, `flagged_label_cells`, `parsable_tp/fp`;
     - the first 12 hex digits of the MANIFEST sha256, and check-1 PASS.
  3. **Items and pairs:** counts and merges (R34).
  4. **Version table** in the layout of plan §5 L121–129: per configuration × policy, rows kept min–max over the seeds and a D mark, split into all seeds and some seeds.
     - `= floor`: identical to the floor before rounding on every seed;
     - `≈ floor`: the same rounded hash on every seed, but different values before rounding.
  5. **Items left** after removing degenerate items, under delete and impute (plan §5 L135–140).
  6. **Degenerate list** (plan L17).
  7. **Raha figures** (plan L17): run-1 counts, rows kept per policy, format-only and label flags, and Raha's references (a)–(c).
  8. **References:** (a) published vs recomputed from the flags to 3 decimals (R87), (b) and (c), each with its order (RR output format).
  9. **Expected verdicts** (A17):
     - the mechanism score (d) per item × policy and the expected verdict per pair, recomputed from the frozen flags;
     - then `addendum match: 87/87` (an abort otherwise);
     - then `verdicts differing from c61ee72 file: N`, expected 0;
     - then the pooled C/D/U, which for four datasets must read GT 19/10/0, delete 16/4/9, impute 12/1/16.
  10. **Check lines:** `check 1/2(hash)/3/4 <ds> PASS`.
  11. **The digest:** `train_hash digest <ds> <sha256>` (R70).
- **R70. The digest** per dataset is the sha256 of the sorted lines `version|policy|seed|rows_kept|degenerate|train_hash` over every version and seed.
- **R71.** stdout = `dryrun.txt` plus timing lines.

## 13. Analysis script `blockd_analysis.py`

### 13.1 CLI and inputs

- **R72.** Usage:
  - `blockd_analysis.py RUN [RUN …] [--out DIR]` (srv P3.6 L446, P3.8 L448);
  - `blockd_analysis.py --compare RUN_A RUN_B` (srv L238, P3.5 L445);
  - `blockd_analysis.py --selftest`.
  - `--out` is optional and follows the R8 rule. Without it, the script only prints (P3.6 has no `--out`; A21).
- **R73.** Every RUN needs `manifest.json` with `mode: full` and `status: ok`, plus `results.csv`.
  - Runs are grouped by the manifest's `fill`. The `mean` group is required; the `median` group is optional and feeds §13.10.
  - Within a group, a duplicate key `(dataset, version, policy, model, seed, scenario)` is refused.
  - Runs whose git HEAD, `REIN_IMAGE_ID` or host fingerprint (architecture + numpy CPU features) differ are refused, so that machines are never mixed (A21). The hostname is only recorded: under `docker compose run` it is the container ID.
- **R74.** Flags and data for the references come from `<RUN>/inputs/`, with their sha256 checked against the manifest. If `inputs/` is missing, `--flags_dir` and `--data_root` are used with the same check.
- **R75.** An analysis is labelled "primary" only when the mean group holds all four datasets and all three policies. Otherwise it is labelled "interim" (milestone 1 = bc + nasa).
- **R76.** The analysis is a pure function of its inputs: no randomness (the permutations are enumerated exactly), and a stable output order.

### 13.2 Mean S2 (plan §8.1 L185)

- **R77.** Per fill × dataset × policy × model × {each item, floor, clean S4, perfect, always-positive, D6, each control}:
  - mean and sd (ddof = 1) of the oriented S2 over the scored seeds, the number of seeds scored, and the number of degenerate seeds;
  - the raw metric (F1 or RMSE) beside it.
  - An item's scores come from its first configuration. Members of an item must have identical per-seed scores, or the script aborts.

### 13.3 Pair rule (plan §8.2 L186–194)

- **R78.** Input: the 10 per-seed oriented S2 values, hashes and degenerate flags of items a and b.
- **R79. Degenerate handling** (plan §8.7 L215; A9):
  - **Ranked last:** degenerate on every seed for both items gives a tie; for one item only, the other item wins without a test. A degenerate seed of an otherwise non-degenerate item scores −∞ in that seed; d = 0 where both are −∞; −∞ ranks above every finite |d|.
  - **Left out:** a pair involving an item that is degenerate on every seed is dropped; seeds where either item is degenerate are dropped from d.
- **R80.** If the rounded `train_hash` is equal on every remaining seed, the verdict is a tie.
- **R81.** d_i = s_a,i − s_b,i. Set |d_i| < 1e-9 to 0, drop the zeros, and call n the number left. n ≤ 5 gives a tie.
- **R82. Exact sign-flip test on midranks:**
  - ranks of |d|, with midranks for ties; ties in |d| are detected after rounding |d| to 12 significant digits (A13);
  - T = Σ sign(d_i)·r_i;
  - p = (number of the 2ⁿ sign patterns s with |Σ s_i r_i| ≥ |T|) / 2ⁿ;
  - p < 0.05 gives the direction sign(T) (A14), otherwise a tie.
- **R83.** Ranks are doubled to integers, so the comparison is exact with no float tolerance. The verdict is invariant to swapping the pair (d → −d) and to permuting the seeds.
- **R84.** Self-test values (MF output, Fable):
  - d = [4,2,4,1,3,4,−3,2,1,−1] → p = 60/1024;
  - [2,3,−1,3,−2,1,1,1,2,5] → 64/1024;
  - [5,−1,−1,3,3,1,−2,4,2,3] → 50/1024;
  - the same p for −d in all three;
  - n = 5, all positive → 2/32 (so ≤ 5 → tie loses nothing);
  - n = 6 → 2/64.
- **R85.** Output per fill × dataset × policy × model × pair: the verdict in both degenerate modes, n, T, p, the mean difference, and whether the hash rule fired.

### 13.4 References (plan §8.3 L195–203; §0 L41–44)

- **R86.** The references are computed from the frozen flags (Raha run 1). For a merged item the value is the maximum over its members (IP L97), and the members must agree (A24).
- **R87. (a) Primary:** Table 3 cell F1 as published, hard-coded as in IP L26–31 (bc .554/.603/.803/.132/.618; nasa .079/.689/.964/.159/.430; bike 0/0/.829/.216/.769; adult 0/0/0/.005/.226). It must equal the F1 recomputed from the frozen flags over all columns, rounded to 3 decimals; otherwise abort. No reference ties may remain (D1 L321); a tie aborts.
- **R88. (b):** row F1 in the style of Table 7, over all columns: detected rows = rows with any flag; true rows = rows with any error (RR L55).
- **R89. (c):** model-visible cell F1: model-column flags against A_mv (RR L55).
- **R90. (d):** mechanism score per policy, exactly as IP L75–102:
  - GT: recall on A_mv.
  - Delete: −∞ if degenerate on every seed; `floor` if the set is empty; otherwise the row precision of the model-column flagged rows.
  - Impute: −∞ if degenerate on every seed; otherwise the parsable TPs minus the parsable FPs, plus (if labels are flagged) the label rows that hold an error minus those that do not; `floor` if that is 0 and no label is flagged.
  - Comparisons involving `floor`, and equal scores, are undetermined.
  - The recomputation must reproduce `addendum_raha_run1/expected_pair_verdicts_raha_run1.csv`: verdicts exactly, mechanism values to 5·10⁻⁴; otherwise abort (A17).
- **R91. bike hand-written vs Raha:** reported under (a) and (c) side by side. A discordance under (a) only is labelled "excluded-column artefact" (plan §0 L44, §8.3 L202).

### 13.5 Concordance and the primary test (plan §1 L52–56, §8.4 L204–209)

- **R92.** Each pair × model is classified against each reference as concordant (the downstream direction equals the reference's), discordant, tied (downstream tie) or reference-tied. Under (a), reference ties must not occur.
- **R93. Per policy, pooled over datasets × models:** C, D, T and the share C/(C+D+T). Ties count in the denominator (plan §1 L54). Beside it: the share among decided pairs, C/(C+D) (L55).
- **R94. The primary test** (one per policy, 3 tests; ranked-last mode; reference (a)):
  - statistic: the pooled number of concordant pairs;
  - null: per dataset, the reference values are permuted among the items, with one permutation shared by the three models; all k! permutations are enumerated (bc and nasa 120, bike 24, adult 6);
  - the per-dataset distributions of the concordant count are convolved;
  - one-sided p = P(X ≥ observed).
  - Holm correction over the 3 policies at α = 0.05: report the raw p, the adjusted p and the decision.
- **R95. Descriptive variants**, unadjusted and labelled descriptive:
  - (a) with degenerates left out: items under delete bc 4, nasa 3, bike 3, adult 2 (24/6/6/2 permutations); under impute 4/5/3/3;
  - (b) and (c) in both modes;
  - (d) gets shares only, no permutation.
- **R96.** Every discordant pair is listed per policy × model (plan §1 L56, §8.4 L209).
- **R97.** Every pair is joined with the frozen `expected_pair_verdicts.csv` (`expected`, read-only) on `(dataset, policy, pair)`, with 87 matches for four datasets. The frozen `expected` column must equal the addendum's, or the differences are printed.

### 13.6 Kendall τ-b (plan §8.5 L210)

- **R98.** Descriptive, per fill × dataset × policy × model × reference, computed from the pair verdicts (A10):
  - τ_b = (n_c − n_d) / √((n₀ − n_ref) (n₀ − n_down));
  - n₀ = the number of pairs; n_ref = reference-tied pairs; n_down = downstream-tied pairs;
  - empty when a denominator is 0.

### 13.7 Share of gap closed (plan §6 L162)

- **R99.** (mean S2 − mean floor) / (mean S4 − mean floor) per dataset × policy × model × item (and for perfect).
  - Reported only where S4 beats the floor by the pair rule (R78–R83) for that dataset × model.
  - A ratio of means (A11).

### 13.8 Random control (plan §8.6 L211–214; fix 4 L28)

- **R100. Scope:** each dataset × model × item whose delete version is non-degenerate on every seed and has 0 < k < n_train on every seed (otherwise "n/a").
  - The item's control is its first configuration's control (merged items on these data are all empty, so k = 0).
  - Compare delete(c) with control(c) by the pair rule and report "detector better / tie / worse than random deletion of the same number of rows".
- **R101.** Print the plan's two caveats beside the table:
  - a tie can mean that the deleted errors are harmless to the model; read it with the ground-truth repair result;
  - the control does not preserve the class balance of the deleted rows (bc, adult).

### 13.9 Degenerate treatments (plan §8.7 L215)

- **R102.** Every concordance number, test, τ and scorecard line is produced twice, ranked last and left out. The primary test uses ranked last.

### 13.10 Median sensitivity (plan §8.8 L216; D5 L325)

- **R103.** With a median group present, per dataset × policy × model:
  - the number of pair verdicts that change between mean and median (both degenerate modes);
  - C/D/T against (a) under both fills;
  - the list of changed pairs.
- **R104.** Fill-invariance, an informational check: on bike, every floor, GT and delete row must have the same `train_hash` and scores in both fills, because every dirty bike value parses (plan §11 L294). A violation is printed.

### 13.11 D6 diagnostic (plan §3 L88)

- **R105.** For nasa `raha_minus_format_only`, mean S2 per policy × model beside Raha and perfect, plus the pair rule against Raha.
  - Labelled diagnostic: excluded from every count, test, τ and scorecard (A8).

### 13.12 Prediction scorecard (plan §9 L236–259; read-only, A23)

- **R106.** Each prediction is printed with its measured quantity and HOLDS / REFUTED, in ranked-last mode against (a), pooled over the datasets present. "Decided" = C + D.

| # | Rule (my reading where the plan gives none; A23) |
|---|---|
| 1 | The GT share among decided pairs is strictly below both the delete and the impute share. Also list the 10 expected discordant GT pairs with what was observed. |
| 2 | The share among decided pairs is ≥ 0.70 under delete **and** under impute. |
| 3 | Against (d): for each policy, among pairs where (d) gives a direction and the downstream verdict is not a tie, the concordant share is ≥ 0.70. |
| 4 | Of the 16 impute pairs marked `undetermined` in the frozen file × 3 models (48 cases), more than half are ties. |
| 5 | The share of tied pairs (all policies and models) is higher on bc + adult than on nasa + bike, and more than half of the bc RF and XGB pairs are ties. |
| 6 | nasa, under GT and under impute: GE-hand and Raha are each not below any other item, for at least 2 of 3 models. Under impute, GE-hand > Raha for at least 2 of 3 models. RF perfect + impute vs floor is a tie by the pair rule. |
| 7 | nasa and bike: every item that is non-degenerate under delete and has (d) row precision ≥ 0.98 beats its control for at least 2 of 3 models. |
| 8 | bike GE-hand vs Raha: discordant with (a) and concordant with (c), under GT and under impute, for at least 2 of 3 models each. |

### 13.13 `--compare` for V4d (srv L44–48, L238, L255; P3.5 L445)

- **R107.** Both runs must have the same datasets, fill, seeds and policies (from their manifests) and the same set of keys `(dataset, version, configuration, policy, model, seed, scenario)`. Otherwise STOP.
- **R108.** Every column except `fit_s` and `timestamp` is compared as CSV text. Each differing cell falls into one category:
  - `train_hash`;
  - **data:** `item, task, fill, rows_kept, test_rows, cells_changed, excl_col_flags, format_only_fp, rows_touched_without_format_only, parsable_tp, parsable_fp, errors_left_in_features, label_errors_left, flagged_label_cells, degenerate, test_degenerate`;
  - **scores per model** (linear, rf, xgb): `score, f1, rmse, r2, precision, recall`.
- **R109. Verdict** (the V4 pass rule, srv L45–48):

| Verdict | When | Exit code |
|---|---|---|
| PASS | no difference | 0 |
| PASS WITH NOTE | only linear score cells differ, plus xgb score cells on bc and adult | 0 |
| STOP | anything else: `train_hash`, data, RF, XGBRegressor, missing rows | 1 |

  - Printed: counts per category × dataset, every differing cell (key, column, a, b), the pair verdicts that differ between the two runs, and a final line `V4d PASS|PASS WITH NOTE|STOP`.

### 13.14 Outputs with `--out`

- **R110.** Files:
  - `analysis.txt` (= stdout);
  - `mean_s2.csv` (R77);
  - `pair_verdicts.csv`: R85 plus the reference directions (a)–(d), the classification per reference, `expected` and `fill`;
  - `concordance.csv`: policy × reference × degenerate mode × fill: C, D, T, reference ties, both shares, permutation p, Holm p for the primary rows, the τ summary;
  - `controls.csv`, `sensitivity.csv`, `gap_closed.csv`, `predictions.csv`.

## 14. Tests

- **R111. `blockd_driver.py --selftest`** runs inside the container and writes only to a `tempfile` directory in the container, never into the repo. It builds a synthetic dataset with:
  - 200 rows: 3 numeric features, 1 categorical, 1 excluded column and a binary label;
  - errors that parse, errors that do not, a label error, a format-only FP and an unflagged `?` that is also `?` in the clean file;
  - its own flag files and MANIFEST.
  
  It asserts: R17–R21 (including a corrupted sha and a duplicate cell, each of which must abort), R24–R31, R38, R40–R45, R52, R54 (−0.0 and the shape matter), R55, checks 2–4, R66, the `--jobs 1` = `--jobs 2` identity of R13, and that an unflagged bad label aborts (R28).
- **R112. `blockd_analysis.py --selftest`** asserts:
  - R84;
  - verdict symmetry and seed-permutation invariance on 200 random vectors;
  - that the direction by sign(T) equals mini's median rule whenever p < 0.05 (on the same vectors);
  - the permutation support sizes 120/24/6/2, a probability sum of 1, and p = 1/120 for a fully concordant five-item dataset;
  - Holm on a fixed vector;
  - the τ-b formula;
  - `--compare`: a run against itself gives PASS; a perturbed linear score gives PASS WITH NOTE; a perturbed RF score or hash gives STOP;
  - R90 against the addendum CSV (flags only, no training).
- **R113. Acceptance runs (the user, step by step):**
  1. Mac `--dry_run` on four datasets: items 5/5/4/3, pooled 19/10/0, 16/4/9, 12/1/16, `addendum match 87/87`, D6 710/0.
  2. Mac `--check`: checks 1–4 PASS.
  3. Recommended: a Mac core run whose RF and XGB mean S2 for floor, GE ×3, HoloClean and perfect under all policies equals `decisions/d5_fill_statistic_{breast_cancer,nasa}.txt` (mean fill) at the printed 4 decimals. That would show that the driver equals the pipeline behind D2–D8. Raha is excluded, because d5 used the disk file. Linear may drift with the thread count (srv L153).
  4. `--compare` of the Mac core run with itself → PASS.

## 15. Ambiguities and the reading chosen

| # | Where | Ambiguity | Reading chosen | Why |
|---|---|---|---|---|
| A1 | plan L26 vs d6 / check script L30 | Format-only FP: "equal within relative 10⁻⁶" vs the code's "text differs, not in `actual_errors`" | The code's definition; the dry run counts violations of the 10⁻⁶ condition (expected 0) | Reproduces the committed numbers (1,864 / 2,330); D6's 710/0 depends on it |
| A2 | plan §11 L287 | Scope of the per-version columns | Flag-set properties (`excl_col_flags`, `format_only_fp`, `rows_touched_without_format_only`, `parsable_*`, `flagged_label_cells`) over the whole dataset; data properties per seed in the training split | The plan's own figures are whole-dataset (bike 247 = 16,198 − 15,951; nasa 1,864; bc 699 label flags), so the dry run can check them against the addendum |
| A3 | plan L287 ("cells changed") | Text vs value change | The value comparator of R65 | A format-only repair (800 → 800.0) changes nothing the model sees |
| A4 | plan L36 | Is an imputed error cell still an "error left"? | Yes, if its parsed value differs from clean (both-NaN = equal) | Literal "compares parsed values"; keeps bc `?`/`?` out, as the plan intends |
| A5 | plan §7 L177 | "changes exactly the flagged parsable feature cells", but unparsable flagged cells are imputed too (mini L96–102, required for floor equivalence) | Check the set of written cells = all flagged feature cells of kept rows; unflagged cells unchanged; report the parsable subset | The only reading consistent with plan §4 L106 and the measured floor equivalence |
| A6 | plan L287 `f1\|rmse` | One column or two | Two columns, `f1` and `rmse`, the other left empty; plus a `fill` column | A CSV needs fixed names; `fill` makes mean and median runs safe to concatenate |
| A7 | plan §4 L109 | `c_idx` and merged configurations | `c_idx = CONFIGS.index(c)` per configuration; the analysis uses the item's first configuration | Literal; every merged configuration on these data is empty (k = 0 → floor), so the choice cannot change a number |
| A8 | plan §3 L88 | D6 scope, scenarios, control | nasa only, all scenarios, no control; a diagnostic verdict against Raha, excluded from all counts | §3 names nasa only; bike stays count-only under D6 |
| A9 | plan §8.7 L215 | Versions degenerate on some seeds only | Per-seed handling (R79); an item counts as degenerate if it is degenerate on every seed | No partial case is expected (§5); the rule must still be defined |
| A10 | plan §8.5 L210 | τ-b on mean S2 or on pair verdicts | On pair verdicts | Mean S2 almost never ties, which would ignore the plan's tie rule |
| A11 | plan §6 L162 | Gap closed per seed or on means | Ratio of means | Per-seed ratios explode when S4 − floor is small |
| A12 | plan §7 L180 | Hash details | Shape included, −0.0 normalised, labels rounded, 64 hex; empty when degenerate | Avoids collisions and sign-of-zero splits; mini hashes y unrounded and truncates the digest |
| A13 | plan §8.2 L190 | "tied \|d\|" in floats | Ties detected after rounding \|d\| to 12 significant digits | Values that are equal in exact arithmetic can differ in the last bit; same precision as the hash |
| A14 | plan §8.2 L192 vs mini L170 | Direction of a significant pair | sign(T) | It is the plan's statistic; equals mini's median rule whenever p < 0.05 (self-test R112) |
| A15 | plan §11 L293 | What "training is skipped" reuses | The fitted model, not the scores; representative by R39; off in `--check` | Scores stay exact for each version's own S1/S2/S3 test matrices; check 2 must not pass by construction |
| A16 | spec §6 L58, L66–70 | S1/S3 test rows and labels | The policy is applied to the test rows with the training statistic; the version's labels in S1 and S3 | The plan never redefines S1/S3; "statistics never from the test rows" (L104) |
| A17 | plan L17, §12 L304; srv L235 | "Reprints the verdicts": recompute, or copy? | Recompute (d) and the expected verdicts from the frozen flags; abort unless they equal the addendum CSV; report the difference to the frozen file (expected 0) | Turns the reprint into a test of the implementation; the frozen file stays untouched |
| A18 | plan L287 | `flagged_label_cells` scope | Whole dataset | The plan's figures (699, 934, 17,366) are whole-dataset |
| A19 | srv L52, L236 | Is `REIN_IMAGE_ID` mandatory? | Mandatory for full and `--check` runs, optional for dry runs | Every production command sets it; dry runs must also work in a quick shell |
| A20 | spec §2 L14 vs srv L395 | Which `--out` paths are allowed | Only new or empty directories under `reports/block_d/runs/` | Stricter than the spec; matches the server rule and keeps runs from mixing |
| A21 | srv P3.6 L446, P3.8 L448 | Where analysis outputs go; mixing runs | `--out` optional (stdout only without it); refuse runs from different HEAD, image or host | P3.6 has no `--out`; mixing machines would break the provenance of the numbers |
| A22 | plan §8.4 L205 | Primary result with only the core datasets | Labelled "interim" unless all four datasets and three policies are present | The plan defines the primary test over four datasets (29 pairs per model) |
| A23 | plan §9 L238–259 | Mechanical rules for predictions 4, 5, 6 and 8 ("most", "near", "first", per model) | R106 table; "at least 2 of 3 models" taken from prediction 7 | Gives a mechanical HOLDS/REFUTED without editing §9 |
| A24 | IP L97 | Reference value of a merged item | Maximum over the members, asserted equal | Matches IP; on these data members are identical |
| A25 | R65 (review 13 Oct) | Flag-statistic columns of versions without a flag set | Empty for `floor`, `clean` and the controls | They apply no flag set; both machines write the same, so V4d is unaffected |
| A26 | R102 vs R106 (review 13 Oct) | Scorecard in both degenerate modes or ranked last only | Ranked last only | R106 is the specific rule and the plan's predictions are stated against ranked last; the left-out concordance and τ are still printed (R95, R102) |
| A27 | plan §9 prediction 6 (review 13 Oct) | "Not below any other item" for GE-hand and Raha, while "GE-hand > Raha under impute" | The GE-hand vs Raha pair is excluded from the "not below" test | The only reading under which both parts of prediction 6 can hold at once |
| A28 | plan §8.4, R94 (review 13 Oct) | Holm decision at the boundary | Exact fractions throughout; reject where the adjusted p < 0.05 (strict) | The same comparator as the pair rule (§8.2); an adjusted p of exactly 0.05 is reachable with these supports, and floats decided it by rounding |

## 16. Conflicts between the documents, and which wins

- **C1. Check numbering.** Spec §9: 1 = perfect + GT, 2 = empty set, 3 = Table 3. Plan §7: 1 = Table 3, 2 = perfect + GT, 3 = empty set, 4 = new. **The plan's numbering is used.**
- **C2. Expected counts.** Spec §2/§3 read them from `expected.json`. That file does not exist. **Use `MANIFEST.csv` plus `TABLE3` from MF** (R19).
- **C3. Pair test.** Spec §10 uses `wilcoxon(mode='exact')`. **Replaced** by the sign-flip test (plan fix 5 L29). The spec's maximum-τ formula is dropped (plan §10 item 8).
- **C4. adult.** Spec §12 says "delete = impute on adult" and "≈ 1.4k rows under HoloClean". **Wrong for HoloClean** (plan fix 7 L31): 0 rows under delete, 1,102–1,153 under impute.
- **C5. Raha figures.** Plan §5 and L17 hold disk-file numbers. Run 1 differs, for example bike delete 1,051–1,106 rows (not 921–976) and adult 31,383–31,455 (addendum `measure_fixes.json`). **The dry run prints the run-1 values; §5's Raha cells are not checks.**
- **C6. Platform.** Spec §8 hard-codes "x86_64 under Rosetta". **Replaced** by the recorded fingerprint (srv L236).
- **C7. Thread settings.** srv L393 already says to drop `OPENBLAS_CORETYPE` when P0 step 4 wrote no file. In the Mac container the two OpenBLAS libraries disagree (R11), so **that branch applies: `$BD` runs without `OPENBLAS_CORETYPE`.** For the user to confirm in P0 step 4.

## 17. Review log (13 Oct; two reviews of the scripts, conformance and correctness)

Each finding was checked against the plan and the code before it was applied. Every code fix has a test in `scripts/tests/test_blockd.py` (20 tests, all pass in the container).

| Finding | Result | Reason |
|---|---|---|
| Conf 1 / Corr 5: only `Abort` is caught; other exceptions leave no `FAIL` line, `manifest.json` or `run.log` (R6, R57) | Applied | Driver: `except Exception` writes `status: failed`, `failure`, the traceback in the manifest and on stderr, `checks.txt`, `run.log`, last line `FAIL unexpected …`. A missing `MANIFEST.csv` is now `CHECK 1 FAIL` (R19). Analysis: `FAIL analysis unexpected …`, exit 1. A failed `--out` stays as evidence; a retry uses a new `--out` (R8 unchanged). Tests `test_unexpected_failures_recorded`, `test_analysis_unexpected_failure` |
| Conf 2: `/reports/block_d/runs/*/inputs/` not in `.gitignore` (R16) | Not applied here | Not a script defect; it is server plan P3 step 1 (srv L237), for the user before the first committed run |
| Conf 3: R44's second clause is false | Applied (R44 text) | Confirmed: mini re-parses `repr()` with `pd.to_numeric`, which is off by one ulp for some 17-digit strings |
| Conf 4 / Corr 8: scorecard ranked last only (R102 vs R106); prediction 6 excludes the GE-hand/Raha pair | Applied (A26, A27) | Documentation only; the code already follows R106 |
| Conf 5 / Corr 2: Holm uses `adj <= 0.05` on floats | Applied | `holm()` now takes and returns Fractions and rejects on `< 1/20` (A28). Corr 2's example is wrong (raw 0.05 adjusts to 0.15); the reachable boundary is raw 1/60, 1/40, 1/20 → all adjusted to exactly 1/20, which floats rejected. Test in `test_permutation_support_and_holm_tau` |
| Conf 6: analysis reads the live verdict files without checking them | Applied | `load_runs` refuses a run whose `expected_verdict_files` sha256 differs from the files now on disk. Test in `test_driver_full_run_synthetic` |
| Conf 7: flag-statistic columns empty for controls | Applied (R65 note, A25) | Documentation only |
| Conf 8a: `dryrun.txt` written in every mode | Applied (R63, docstring) | Kept on purpose (a full run's digests can be diffed); the docs now say so |
| Conf 8b: `Abort`, `Refused`, `Out` are classes despite R1 | Rejected | R1 says no classes are *needed*; an exception type is the right tool, and `Out` is a small output collector |
| Conf 8c / Corr 4: left out with no common scored seed is labelled "same train_hash" | Applied | Now `tie`, `hash_rule 0`, reason `no common scored seed`; cannot occur on these data. Test in `test_degenerate_modes` |
| Corr 1: under delete 16 of 29 pairs per model are decided by the ranked-last rule alone (impute 7) | No code change | Verified (bc 4, nasa 7, bike 3, adult 2). The left-out variant is already computed (R95); whether the thesis prints it beside the primary is for the user |
| Corr 3: a pair tied on both sides is counted in n_ref but not n_down | Applied | Confirmed against the standard τ-b; only the descriptive (b)/(c)/(d) τ can change, (a) has no ties. New `tau_from()`; test in `test_permutation_support_and_holm_tau` |
| Corr 6: `--seeds 0 2` printed as `0-2` | Applied | New `seeds_text()` in the banner and `dryrun.txt` [4]; `0-9` unchanged. Test `test_seeds_text` |
| Corr 7: gap closed averages the item over scored seeds but floor and S4 over all seeds | Applied | New `gap_closed()` uses the item's scored seeds for all three means; identical when no seed is degenerate (the real data). Test `test_gap_closed_matched_seeds` |
| Corr 9: memory and time on adult | No change | Information; `--jobs 1` as prescribed |


- 13 Oct (after the final Fable check): remaining issue 1 fixed. `load_runs` compared `hostname`, which is the container ID under `docker compose run`, so a two-run analysis (mean + median) would always be refused. It now compares `provenance(env)` = git HEAD, `REIN_IMAGE_ID`, `host_fingerprint`; test `test_provenance_ignores_container_hostname` added. `.gitignore` now ignores `/reports/block_d/runs/*/inputs/`.
