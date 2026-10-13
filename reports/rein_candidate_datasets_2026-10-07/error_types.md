# Error-type gap analysis (7 Oct 2026, freeze 15 Oct)

Scope: which NEW error type(s) to add so the comparison GE (3 tiers) / HoloClean / Raha learns something it cannot learn from the nine current datasets. Read-only on the repo; nothing was run in docker. GE and HoloClean were *replayed* in a scratch simulator whose output matches the stored benchmark results exactly (section 3.2); Raha was not run, its rows are inference from its strategy code.

## 0. Bottom line

1. **Add numeric disguised missing values (sentinels) first**, as a scratch variant of nasa (`nasa_dmv`). REIN's Table 4 names "implicit MVs" for 5 of 14 datasets (one of them, Mercedes, is in our benchmark). None of our nine datasets has a numeric one. REIN's own `implicit_mv` injector can't produce one (it writes strings such as "Afghanistan" into nasa's `chord_length`). This type splits GE exactly at its built-in missing-token list. String `?`: all three tiers F1 1.00. Numeric sentinel: both profiled tiers 0.00, hand-written 0.56 to 1.00 depending on the sentinel. An in-range "mode" sentinel is a built-in control that every single-column method has to miss. Effort is about 1 day.
2. **Optionally add inconsistent representation of categorical values** (case and abbreviation variants) as a scratch variant of adult (`adult_rep`). REIN and CleanML list "inconsistencies" as a top-level error type, and none of our nine datasets has one. It is the only candidate that reverses the GE tier order: clean_profiled 0.94, hand_written 0.00, dirty_profiled 0.00 (measured). One confound: the adult hand-written suite was written for label flips. Effort is about 1 more day.
3. **Don't add** the following:
   - Duplicates: they add rows, Raha can't run (REIN paper), and new evaluation code would be needed.
   - Cross-column inconsistency: GE can't see it by construction, HoloClean is saturated, and Raha's RVD saturates. bike and beers already cover it partly.
   - Scale, sign flip and column swap: they behave like the existing outliers.
   - Broken characters: partly present already, and every character-based detector catches them.
4. **HoloClean can't tell any new type apart.** Its FDX-derived DCs already flag 22.6 to 98.0 % of the cells and 100 % of the rows of the *clean* data, on all six datasets that have DCs. On the other three it has no DCs. Any injected type therefore gets HoloClean recall of about 0.7 to 1.0 with precision close to the error rate. Measured F1 is 0.003 to 0.03 for every new type. Only GE tiers versus Raha can separate the types.

---

## 1. What exists today

### 1.1 Observed error types in the nine datasets (audited list from the shared context; not re-derived)

| type \ dataset | adult | beers | bike | breast_cancer | har | mercedes | nasa | smartfactory | soilmoisture |
|---|---|---|---|---|---|---|---|---|---|
| explicit MV (blank) | | | | x | x | x | (typo side-effect) | x | x |
| implicit MV, string token | | x (`''`→`N/A` ibu) | | | | | | | |
| implicit MV, numeric sentinel | | | | | | | | | |
| outliers (additive Gaussian, 4σ) | | | x | | x | x | | | x |
| typos | | | | (string noise) | | | x (buggy injector) | | |
| pattern / format violation | | x (ounces "12.0 oz", abv "%") | | | | | | | |
| FD / rule violation | | x (city+state merge) | x (block rewrites mnth/season/holiday/workingday) | | | | | | |
| in-domain value swap | | | | x | | | | | |
| broken / non-ASCII characters | | | | x (23 cells, side effect, see 1.2) | | | | | |
| mislabels | x (1701) | | | x (15) | | | | | |
| duplicates, column swap, unit/scale, sign flip, categorical representation inconsistency, numeric DMV | — | — | — | — | — | — | — | — | — |

### 1.2 What REIN's tooling can inject (verified in code)

Entry point: `scripts/create_dirty.py --dataset_name <ds> --error_type <t ...> --error_rate 0.1 --outlier_degree 3 [--muted_attribs ...] [--store_postgres]`. `--error_type` takes the `ErrorType` values in `rein/auxiliaries/configurations.py:92`: `cell_swapping`, `implicit_mv`, `explicit_mv`, `gaussian_noise`, `typo_keyboard`, `outliers`. The call path is `Datasets.inject_errors` (`rein/datasets.py:721`) → `__inject_outlier` (outliers), or `__generate_errors` → BigDaMa error-generator strategies (`tools/error-generator/error_generator/strategies/`).

**Warning:** `datasets_path = 'datasets'`, and create_dirty writes `datasets/<ds>/dirty.csv`. In docker that is the frozen dataset's own dirty file. Inject only into scratch copies, the way `scripts/robustness_driver.py` does.

| ErrorType / strategy | what it really writes (verified) | known bugs / quirks |
|---|---|---|
| `outliers` → `Datasets.__inject_outlier` | `x + N(0, degree·σ_col)` on a random `rate` fraction of the numeric non-muted cells | The docstring's "always ≥ threshold σ away" is false. At degree 4, 54.7 % of the perturbations land within 3σ of the original value (analytic: P(\|Z\|<0.75)). Integer columns become floats. |
| `explicit_mv` → `Explicit_Missing_Value` | `""` | none |
| `implicit_mv` → `Implicit_Missing_Value` | It fuzzy-matches the **column name** (difflib ratio > 0.3) against 13 keys from other datasets and writes that key's value. Otherwise it writes `"N/A"`. Measured per column: **nasa** frequency→`Some college`, angle→`20010101`, chord_length and velocity→`Afghanistan`, thickness→`?`, SPL→`N/A`. **bike** instant→`Alabama`, season→`111111111`, workingday and casual→`?`. **har** x/y/z→`N/A`. **mercedes** 377×`N/A`, 1×`-1`. **soilmoisture** 125×`N/A`. **adult** age→`20010101`, fnlwgt→`Afghanistan`, educational_num→`Some college`. | The docstring says median/mode replacement, but that code is commented out. On numeric columns this gives type-violating strings, not realistic numeric DMVs. `?` and `N/A` are already in GE's `MISSING_TOKENS`. |
| `gaussian_noise` → `Gaussian_Noise` | `__generate_errors` runs on `dirtyDF.astype(str)`, so the string branch always applies: it inserts `chr(sum of code points)` at a random position, or reverses the string when the noise rounds to 0. Examples: `4`→`44`, `10`→`a10`/`1a0`, ids `290`→`2\x9b90`, `1016277`→`101627Ũ7`. Measured in breast_cancer: 136 inserted-character cells, 23 non-ASCII cells (id columns), 7 with letters, and 9 other cells (mostly reversed strings). | The numeric branch (chainer, absolute σ≈1.42) is unreachable through create_dirty. This injector is the source of breast_cancer's "digit doubling". |
| `cell_swapping` → `Random_Active_Domain` | value of the same column from another random row | It never checks that the value differs. No-op probability is Σp² per column (breast_cancer: Mitoses 0.69, class 0.55, Normal Nucleoli 0.42), so the realised rate is below nominal. `col_rand` is unused. |
| `typo_keyboard` → `Typo_Keyboard` | Each character is deleted, doubled, or (for letters) replaced by a keyboard neighbour. | `[z]*0` bug: no character is ever kept. P(5-digit string unchanged) = 0.0 over 10 000 trials. A digit string becomes `''` with probability 0.5^len, so some typos turn into explicit MVs. Samples: `0.3048`→`0044`, `1250`→`''`. |
| rate semantics (create_dirty + inject_errors) | `rate / len(error_list)`, where `error_list = [outliers?, [generator funcs]]` | The generator list always counts as one entry, even when it is empty. `--error_type outliers` alone injects rate/2. k generator types each get the full share, so k× the rate. Outlier rate is a fraction of numeric *cells*; generator rate is a fraction of *rows* (one random column per row). Muted columns are re-joined at the end, which changes column order (robustness_driver restores it). |
| `missing_values` → `Datasets.__inject_mv` (MCAR/MAR) | NaN mask | Unreachable from create_dirty (no `ErrorType` member). It returns the frame **without the label columns**. |
| API only, not wired into create_dirty | `White_Noise` (relative N(0,1); dead-code bug in the int branch), `Typo_Butterfingers` (letters only, p=0.6 each), `Similar_Based_Active_Domain` (closest string in the column), `Word2vec_Nearest_Neighbor` (needs a 681 MB fastText download) | — |
| `tools/error-generator/accuracy_drop_proj` | Adversarial "change features until a trained sklearn model loses accuracy" strategies (Iris/Abalone/Digits/EEG loaders). Research prototype. | Not wired into REIN. |
| BART | **Not in the repo.** `configurations.py` only defines string constants (`missing_values`, `pattern_violation`, `rule_violation`, `outliers`, `mislabels`, `duplicates`, `typos`, `inconsistency`). The only BART code is ED2's XML generator (`cleaners/ed2/model/ml/data_generator/generate_bart_config.py`). In BART's own source (GitHub dbunibas/BART): DC-violation errors (`vioGenQueries`), random errors with `TypoActiveDomain/AddString/AppendString/Random/RemoveString/SwitchValue`, and `outlierErrors`. A path search found **no duplicate generator class**. | Java + PostgreSQL, about a day to set up. Not an option before the freeze. |
| duplicates in REIN | Detection only (`duplicatesdetector`, key collision on `keys`) and repair only (`duplicatesCleaner`, `drop_duplicates`) | No injector. |

**Correction to the shared context:** in the detection path HoloClean runs **only `ViolationDetector`** (`rein/detectors.py:1153`). `NullDetector` is imported but unused there. HoloClean therefore sees blanks or sentinels only through DC violations.

---

## 2. Literature taxonomy versus coverage

Sources:
- [A] Abedjan et al., "Detecting Data Errors: Where are we and what needs to be done?", PVLDB 9(12), 2016. Four error types: outliers, duplicates, rule violations, pattern violations.
- [R] Rahm & Do, "Data Cleaning: Problems and Current Approaches", IEEE Data Eng. Bull. 23(4), 2000. Single- and multi-source, schema- and instance-level problems: missing/dummy values, misspellings, cryptic values/abbreviations, embedded and misfielded values, violated attribute dependencies, uniqueness violations, duplicates, contradicting records, inconsistent representations or units across sources.
- [B] Arocena et al., "Messing up with BART", PVLDB 9(2), 2015. Verified in its source as above.
- [J] Schelter, Rukat, Biessmann, "JENGA", EDBT 2021. Verified in its source: `MissingValues` (MCAR/MAR/MNAR), `SwappedValues` (two columns within a row), `CategoricalShift`, `GaussianNoise`, `Scaling` (×10/100/1000), `BrokenCharacters` (vowels→accented).
- [C] Li et al., "CleanML", ICDE 2021. Verified in `schema_error_type.py`: missing_values, outliers, mislabel, inconsistency, duplicates.
- [REIN] Abdelaal et al., EDBT 2023: abstract and Table 4. Also FAHES (Qahtan et al., KDD 2018), REIN ref. [44], for disguised MVs.

| error type | in literature | injectable with REIN tooling | present in our 9 | missing REIN dataset that has it naturally |
|---|---|---|---|---|
| explicit MV | R, J, C, REIN | yes (`explicit_mv`) | 5 datasets | power (full-row `?`, see last row) |
| implicit MV, string token (`?`, `N/A`) | R, FAHES, REIN | partly (`implicit_mv`, column-name lookup) | beers only | **water**: 591 `?` cells in 147 of 596 rows. **power**: 25 979 raw lines with `?`. Both measured. |
| implicit MV, numeric sentinel/default (0, -1, 9999, mode) | R ("dummy values"), FAHES, REIN Table 4 | **no** (realistic numeric values only by accident: `-1` in 2 columns) | **none** | per Table 4: print3d, mercedes, water, power, soccer. print3d's raw Kaggle file has no blanks and no duplicates (measured, 50×12; its 10 `fan_speed=0` values are plausible settings). REIN notes say its errors were "generated manually". |
| outliers / noise | A, B, J, C, REIN | yes | bike, har, mercedes, soilmoisture | water, soccer (Table 4) |
| typos | R, B, REIN | yes (buggy) | nasa | power (Table 4) |
| pattern / format violation | A, REIN | indirectly | beers | — |
| FD / rule / DC violation (cross-column) | A, R, B, REIN | no (BART absent) | beers, bike | soccer (Table 4) |
| inconsistent representation (case, abbreviation, synonyms) | R, C ("inconsistency"), REIN (abstract, OpenRefine) | **no** | **none** | none of the five per Table 4 |
| in-domain value swap | B (TypoActiveDomain), REIN | yes (`cell_swapping`) | breast_cancer | — |
| column/attribute swap (misfielded) | R, J | no | none | — |
| unit / scale | R (units across sources), J | no | none | — |
| sign flip | (not a named class in A/R/J/C) | no | none | — |
| encoding / broken characters | J | side effect of `gaussian_noise` | breast_cancer (23 cells) | — |
| duplicates (tuple / entity) | A, R, C, REIN | no injector | **none** | **citation**: REIN-prepared dirty 5005 rows vs clean 3997, 772 exact-duplicate rows (measured). **print3d** per Table 4. |
| mislabels | C, REIN | no injector | adult, breast_cancer | **citation** |

---

## 3. Which tool should catch what

### 3.1 How each configuration sees a cell (verified in code)

- **GE dirty_profiled / clean_profiled** (`rein/auxiliaries/expectations_profiler.py`). Each column gets exactly one of the following, on top of a `not_in_set` rule against `MISSING_TOKENS = ['', 'N/A', 'n/a', 'NA', 'NULL', 'null', '-', '?']`:
  - `^-?\d+(\.\d+)?$` if every non-token value parses as a float;
  - otherwise, a value set if the column has ≤ 20 distinct values.

  Numeric columns never get ranges or value sets. dirty_profiled learns the value set *including* the errors.
- **GE hand_written** (`expectations_dictionary_local.py`): single-column regexes (86), `unique` (7), `not_be_in_set`/`not_match_regex` (3). Ranges are written as regexes. There are **no multi-column expectations**, so cross-column errors are invisible by construction.
- **HoloClean**: `ViolationDetector` only, over FDX-derived two-tuple DCs `EQ(lhs…)&IQ(rhs)`. Semantics: if an LHS group holds more than one RHS value, every row of the group is flagged on every DC column. Exact duplicates can never violate such a DC. On **clean** data the current DCs already flag:

  | dataset | DCs | clean cells flagged | rows touched |
  |---|---|---|---|
  | adult | 14 | 98.0 % | 100 % |
  | nasa | 4 | 83.3 % | 100 % |
  | bike | 14 | 70.9 % | 100 % |
  | breast_cancer | 8 | 70.0 % | 100 % |
  | smartfactory | 18 | 42.4 % | 100 % |
  | beers | 3 | 22.6 % | 100 % |
  | har, mercedes, soilmoisture | 0 | — | — |
- **Raha** (raha==1.25; strategy code read from GitHub master, `raha/detection.py`):
  - **OD**: dBoost, histogram 5×5 configurations and gaussian 1.0–3.0σ. Flags rare or far values.
  - **PVD**: one strategy per (column, character); flags cells that *contain* that character.
  - **RVD**: every ordered column pair; flags both cells of every row whose LHS value maps to more than one RHS value.
  - **KBVD**: KATARA knowledge base.

  Binary features feed per-column clustering and label propagation from 20 labelled tuples, then a GBC. Consequence: PVD is a pure function of the cell string, and dBoost's histogram and gaussian models score field values. **Two cells with the same string in the same column therefore get (near-)identical OD/PVD features.** Only RVD (row context) can separate them, and RVD saturates once every LHS group contains at least one error.

### 3.2 Measured replay: GE (three tiers) and the HoloClean violation detector

The replay is `SCRATCH/error_types_sim/sim.py`. It re-implements GE's legacy `PandasDataset` checks and the ViolationDetector, and imports the repo's profiler and hand-written suites read-only. **Validation:** on the shipped dirty files it reproduces the stored `detection_results.csv` exactly, both #detections and F1, for nasa (30/384/680/6265), bike (0/0/24247/198979), breast_cancer (260/291/460/5691) and beers (1199/4302/4429/5821).

Setup: injection into a copy of clean.csv; label muted; one cell per selected row. nasa: 5 % of rows, 5 seeds. adult/bike: 2 % of rows, 3 seeds. Values are mean cell-level F1 (recall in brackets where useful). On clean data before injection, GE flags 0 cells in all three tiers on nasa, adult and bike.

| new type (host) | GE dirty_prof | GE clean_prof | GE hand | HoloClean | Raha (inference, not run) |
|---|---|---|---|---|---|
| DMV `-1`, written in clean style (nasa) | 0 | 0 | **1.000** | 0.016 (R .79) | high: PVD `-` (no `-` in nasa), OD far |
| DMV `9999`, clean style (nasa) | 0 | 0 | **0.880** (R .79; frequency regex `\d{3,5}` accepts 9999.0) | 0.016 | high: OD far, new digits for PVD |
| DMV `0`, clean style (nasa) | 0 | 0 | **0.563** (R .39; `0.0`/`0.0000` pass angle, chord and thickness regexes) | 0.014 | medium: far only in velocity/frequency |
| DMV = column mode, in-range default (nasa) | 0 | 0 | **0** | 0.015 | **low by construction**: string identical to legitimate cells |
| DMV `?` string token (nasa) | **1.000** | **1.000** | **1.000** | 0.016 | high (PVD `?`) |
| scale ×1000 / ×100 (nasa) | 0 / 0 | 0 / 0 | 0.981 / 0.884 | 0.013 | high (OD), same mechanism as the existing outliers |
| scale ×0.001 (nasa) | 0.491 (only because `2.66e-06` breaks the number regex) | 0.491 | 0.836 | 0.013 | medium |
| sign flip (nasa) | 0 | 0 | 1.000 | 0.014 | high (PVD `-`) |
| column swap, random pair (nasa) | 0 | 0 | 0.868 | 0.019 | medium–high (OD) |
| column swap chord↔thickness, overlapping format (nasa) | 0 | 0 | **0** | 0.030 | medium–low |
| cross-column: educational_num ≠ education (adult, exact bijection in clean) | 0 | 0 | 0 | 0.003 (R 1.0) | low: RVD fires for every row once each group is polluted |
| cross-column: cnt ≠ casual+registered (bike, exact in clean; registered changed) | 0 | 0 | 0 | 0.003 | low |
| representation: case variant (adult categoricals) | **0** | **0.938** (R .88; native_country has 41 values > 20) | **0** | 0.003 | medium–high: dBoost histogram (rare value), PVD case letters |
| representation: abbreviation `Abc.` (adult) | **0** | **0.938** | **0** | 0.003 | high (PVD `.`; no `.` in adult categoricals) |
| broken char U+FFFD (adult) | 0 | 0.934 | 1.000 | 0.003 | high (PVD) |
| column swap age↔hours_per_week, overlapping ranges (adult) | 0 | 0 | 0.047 | 0.005 | low |
| exact duplicates +5 % rows, **row-level** (nasa / beers) | 0 / 0.09\* | 0 / 0.09\* | 0 / **0.57** (beers `id` unique flags both copies, P .40) | 0.091 / 0.091 (flags every row; 0 new violations) | not runnable (shape) |

\* Only because duplicated rows with a blank `ibu` hit `MISSING_TOKENS` (the known blank false positives).

### 3.3 Verdict per type: does it discriminate?

- **Numeric DMV.** Strong within GE. The string vs numeric split happens at `MISSING_TOKENS`. Hand-written recall depends on how wide each regex is (9999 slips through frequency; `0.0` slips through chord/thickness). The mode variant is an honest "everyone fails" control: FAHES-type knowledge is needed. Raha should be high on out-of-range sentinels and low on mode sentinels, so there is also a Raha-internal split. This is new evidence for RQ2 (what human input buys), not just a repeat of the outlier result, because of the token boundary and the control.
- **Representation inconsistency.** Strongest discrimination. It is the only type where clean_profiled beats hand_written; in all nine existing datasets hand ≥ clean ≥ dirty. Confound: the adult hand-written suite uses permissive character-class regexes because adult's real errors are label flips. Keep the suite frozen to stay fair, and say so in the text.
- **Cross-column** (valid values, broken dependency). GE is 0 by design. HoloClean is saturated. Raha's RVD saturates at realistic rates. Prediction: everyone fails, which adds little, and bike and beers already cover it partly. It would only become interesting with hand-specified exact FDs or GE multi-column expectations, which is a design change.
- **Scale, sign flip, disjoint column swap.** Same pattern as the existing outliers (profiled 0, hand high, Raha OD high). Redundant.
- **Overlapping column swap.** Everyone is at or near 0, so it is just another "all fail" case.
- **Broken characters.** Every character-based rule catches them, and they are already partly present in breast_cancer.
- **Duplicates.** Literature-central, but two of three tools are blind or unrunnable by construction (see section 4).

---

## 4. Cell-level evaluation constraint

GT is `Datasets.get_actual_errors`: dirty and clean are compared cell by cell with `.iat` (same shape, same row and column order). Raha also builds its own labels from a positional string diff.

- **Fits (same shape):** numeric/string DMVs, scale, sign flip, column swap (2 cells per row), cross-column, representation, broken characters, mislabels. Two protocol requirements:
  - write injected values in the clean column's number style, as `write_like_clean` in `robustness_driver.py` already does;
  - skip cells where the injected value equals the clean value numerically.

  Otherwise Raha's string-diff labels and REIN's isclose GT disagree. Example: `0` vs `0.0` counts as an error for Raha but not for REIN.
- **Doesn't fit:** duplicates, which add rows. Measured on REIN's own prepared citation: clean 3997 rows vs dirty 5005 rows. REIN's paper states that Raha, ED2 and Meta do not work with duplicates for exactly this reason: dirty and GT end up with different lengths.
- **Row-level option for duplicates:**
  - GT = the indices of the extra copies (REIN's key-collision convention: first occurrence clean, later copies dirty), stored in a separate file instead of being diffed.
  - A tool "detects" a row if any of its cells is flagged.
  - Report row P/R/F1, or count a duplicate group as found if any member is flagged. Otherwise uniqueness rules that flag both copies (`duplicated(keep=False)`) are capped at P = 0.5.
  - Raha would need labels from that file instead of its positional oracle.
  - A shape-preserving surrogate exists: overwrite row i with a copy of row j. That is semantically a row replacement, though, not a duplicate.
  - Estimated cost: 2 to 3 days, which doesn't fit before 15 Oct next to Block D.

---

## 5. Recommendation and cheapest path

Path (b), controlled injection into a scratch copy, is cheaper than path (a), taking a REIN dataset. The REIN datasets that have DMVs naturally (water, power) only carry the `?` token, which every GE tier already catches (F1 1.00). Their numeric sentinels are not documented anywhere. citation's duplicates break the shape.

**Implementation for both types:**
- Copy `scripts/robustness_driver.py` to a new driver and replace only `inject()`.
- Keep everything else unchanged: the scratch directory under `datasets/`, `register()` (reuses the base dataset's hand-written suite and constraints directory, so the base DCs are reused), `run_detectors`, the output CSV, the sha256 of the dirty file, and Raha averaged over 6 runs as in the robustness protocol.
- Do not edit the hand-written suites after seeing the injected data.

**R1: `nasa_dmv` (numeric disguised MVs)**
- Source: nasa clean.csv (1503×6). Label `sound_pressure_level` muted.
- Rate: 5 % of the cells of each non-label column (375 cells, 4.2 %, close to REIN's nasa error rate 0.08). Per-column injection guarantees each column has dirty cells for Raha's 20 labels.
- Two variants, 3 seeds each:
  - (i) sentinel 9999 (optionally also -1);
  - (ii) the column's mode written into cells whose clean value differs (the control).
- Values are written in the clean column's style. Skip cells that already equal the sentinel.
- GT: `get_actual_errors` on the scratch copy. Assert that it equals the injection log and a plain string diff.
- Expected results:
  - GE as measured in 3.2: dirty/clean 0, hand 0.88 for 9999 and 0 for the mode variant;
  - HoloClean about 0.02 (saturated);
  - Raha to be measured.
- Time: implementation and checks about 4 h. Runs under 1 h (nasa: GE and HoloClean take seconds, Raha takes minutes per run). Analysis and write-up about 0.5 day. **About 1 day.**

**R2: `adult_rep` (representation inconsistency)**
- Source: adult clean.csv. Label `income` muted.
- Columns: the 8 categoricals (7 of them have ≤ 20 values).
- Rate: 2–5 % of rows, one cell per row, half case variants and half abbreviations (or a small curated synonym map, e.g. Male→M, United-States→USA, Never-married→Single).
- Expected results:
  - GE dirty 0, clean 0.94, hand 0 (measured);
  - HoloClean about 0.003;
  - Raha to be measured.
- Raha on adult takes about 10 min per run and about 16 GB, so 6 runs take about 1 h. Clustering works on adult's complete cache.
- **About 1 day.**

If only one fits next to the Block D gates (11 and 15 Oct), do R1. It is smaller, faster, has no authoring confound and closes a gap REIN itself declares.

---

## 6. Side findings (out of scope; for the parked flags)

- The stored adult HoloClean result is `rein-datasets/adult/holoclean/detections.csv` (341 890 cells, run 17 Sep 12:26). It is **exactly** the output of DC9 + DC10 alone of the current 14-DC `adult_dcs.txt`, which was written 17 Sep 12:27. The full file flags 665 207 cells (98 %). The stored row therefore used 2 of the 14 DCs.
- The shared context says HoloClean uses a null detector. The detection path does not use one (`rein/detectors.py:1153`).

## Files

- Report: `SCRATCH/agent_reports/error_types.md`
- Replay: `SCRATCH/error_types_sim/sim.py`, `sim2.py`
- Results: `sim_results.csv`, `sim_summary.txt`, `sim2_output.txt`
- Raha strategy source used for the inference: `SCRATCH/error_types_sim/raha_detection_master.py`

(SCRATCH = `/private/tmp/claude-503/-Users-ghassen-aicha-caronsale-de-Desktop-BA-rein-benchmark/32983ad7-d979-40ea-a9e4-4217ca518e50/scratchpad`.) Nothing was written to the repo or to the download folder.
