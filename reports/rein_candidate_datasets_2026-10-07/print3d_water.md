# 3D Printer (`print3d`) and Water (`water`): source, profile, fit for the benchmark

Date: 7 Oct 2026. Nothing under REPO was changed. Profiling scripts are in `SCRATCH/print3d_water/` (`profile_print3d.py`, `profile_water.py`, `water_labels.py`, `water_more.py`, `implicit_tokens.py`).

**Verdict:** **print3d: exclude.** **water: exclude from the main tables.** Water could become a case study on real errors with no ground truth, but only if time is left after the Block D core gate (11 Oct).

---

## 1. Downloads (verified)

Folder `DL = "/Users/ghassen.aicha@caronsale.de/Desktop/BA/REIN DATASETS"`.

| File | URL | Bytes | sha256 |
|---|---|---|---|
| print3d/kaggle_api_3dprinter.zip | https://www.kaggle.com/api/v1/datasets/download/afumetto/3dprinter (no login; redirected to a signed GCS URL, Kaggle dataset id 52387, version 3) | 200,222 | 56638cf0816f1083ec08fe669e5fd49bd77cf901d440c5e8b19ee5be24cbefbc |
| print3d/kaggle_extracted/data.csv | (from the zip) | 2,408 | b98f601f714f2744dff18f5d1521288306b908b9da7fff3a42ae3d136a916e2d |
| print3d/kaggle_extracted/printer_dataset.py, 3dprinter.ipynb, 3dprinter.html | (from the zip) | 4,597 / 122,295 / 384,210 | 634eb415… / f20d87b4… / f3651ef3… |
| print3d/kaggle_metadata_afumetto_3dprinter.json | https://www.kaggle.com/api/v1/datasets/metadata/afumetto/3dprinter | 3,955 | 00cffc46558883b4b27e5e64680dbeb54d6635de5ecb79b4680a76ace34a9b4f |
| print3d/github_ahmetokudan/data.csv | https://raw.githubusercontent.com/ahmetokudan/3dprinterdeeplearning/06fdb01b6b8c484e938629b76bc2a39e6c2f41fb/data.csv (repo of the dataset author, created 2018-09-12) | 2,459 | 4a7680be5166da3ef1982a8dbcb2b49ee4c1f94a035cfd49d6a91684421c3930 |
| print3d/github_ahmetokudan/3dprinter.md | same commit, `3dprinter.md` | 11,421 | ee76259e4e77f7e8feae2b2d714fdc6d30798b1c5c59289befae574a1258694c |
| water/uci_water_treatment_plant.zip | https://archive.ics.uci.edu/static/public/106/water+treatment+plant.zip (REIN's https://bit.ly/3SBkduN redirects to UCI dataset 106) | 39,385 | 44e8cc2b294ce8d2d2c7c6a9bbb33dde463591c47add23f85e83ae67a94a0f31 |
| water/uci_extracted/water-treatment.data | (from the zip) | 92,549 | af2e632b370646ea9763b11aed54b30423f0c3b8a7fb1b7d23e1c922098a7a8a |
| water/uci_extracted/water-treatment.names | (from the zip) | 12,262 | bb932169a9680170fbba91b805e6fd5afd538af805cb29bbfdb3b1c308e962bb |
| water/uci_extracted/Index | (from the zip) | 138 | 1f8d321d7ad24afcead273628fc41bb69023804ff7e54273161bcfa30186f9ba |

Cross-checks (verified):
- The GitHub copy has the same content as the Kaggle `data.csv`. The only difference is formatting: GitHub uses `;` with CRLF line ends, Kaggle uses `,` with LF.
- The legacy UCI file (https://archive.ics.uci.edu/ml/machine-learning-databases/water-treatment/water-treatment.data) is byte-identical to the file in the zip (same sha256). It was saved to scratch only.

**Prepared REIN versions: none exist.**
- I searched the full git trees of mohamedyd/rein-benchmark, SAGED, AutoCure, ReClean, RTClean, DiffClean, D3Bench, DataLens, data_cleaning_with_latent_operators, XAI2Clean, DVBench, Haipipe, Data-quality-Dashboard, DiffSelect, GLLM and SEED for `print3d|3dprint|printer|water`. There were no hits apart from unrelated SEED Wikipedia tables and a `Watermark.py`.
- A GitHub code search for `tension_strenght` turned up no file named `dirty.csv` or `clean.csv`.
- Hugging Face has no mirror.
- So REIN's clean and dirty versions of print3d and water are **not public**. The print3d dirty file was "generated manually" (dictionary note) and cannot be reproduced.

---

## 2. 3D Printer: profile (verified, measured with pandas)

- **Shape and types.** 50 × 12: 10 numeric columns, 2 categorical (`infill_pattern`, `material`). This is **exactly REIN Table 4** (50 / 12 / 10 / 2).
- **Missing values.** No explicit MVs and no empty strings.
- **Disguised MVs.**
  - No negative values. No sentinels.
  - The only zeros are `fan_speed = 0`. That is 10 cells, and they are a real design level (0, 25, 50, 75, 100 %).
  - So a generic "0 = missing" rule would produce 10 false positives.
- **Duplicates.** No exact duplicates. Even the 9 setting columns are unique per row. The closest pair differs in 4 of 12 columns, so there are no near-duplicates either.
- **Robust outliers** (\|x − median\| / (1.4826 · MAD) > 3.5): **none in any column.**
- **It is a designed experiment.** Rows come in 5 blocks of 10, one block per layer height (0.02, 0.06, 0.1, 0.15, 0.2). Inside a block, position k fixes five columns:
  - `material`: positions 0–4 are ABS, 5–9 are PLA.
  - `nozzle_temperature`: ABS 220, 225, 230, 240, 250; PLA 200, 205, 210, 215, 220.
  - `bed_temperature`: 60–80.
  - `fan_speed`: 0–100.
  - `infill_pattern`: alternates.
  - `wall_thickness` (1–10) and `infill_density` (10–90) vary with no pattern.
- **Exact FDs:**
  - `layer_height → print_speed` (0.02→40, 0.06→60, 0.1→120, 0.15→60, 0.2→40).
  - `bed_temperature ↔ fan_speed`, a 1:1 mapping.
  - 18 two-column FDs on the design columns (plus 4 spurious ones with `elongation` on the LHS, where the LHS is 88 % unique), e.g. `(nozzle_temperature, material) → bed_temperature`, `(bed_temperature, material) → nozzle_temperature`, `(nozzle_temperature, bed_temperature) → material`.
  - Every FD holds on all 50 rows.
- **Label `tension_strenght`** (the misspelling is the source's): regression target, integer MPa, 4–37, mean 20.1, sd 8.9, 26 distinct values. Correlation with `elongation` is 0.84; with every setting column it is between −0.41 and 0.40.
- **Classes are balanced:** 25 ABS / 25 PLA, 25 grid / 25 honeycomb.

### Ground truth (print3d)

- **Verified:** with every check above (MVs, sentinels, duplicates, MAD outliers, design FDs, value grids), the raw file has **0 detectable real errors**. It is clean, measured lab data from Selçuk University (Ultimaker S5, Sincotec tensile tester).
- **Not checkable:** the three measured outputs (roughness, tension, elongation) have no redundancy, so measurement error in them cannot be tested.
- **Inference:** REIN used this file as `clean.csv`, since the shape matches Table 4 exactly. That is harmless here: no real errors would be counted as "clean".
- **Error rate:** 0.05 × 600 cells = **about 30 erroneous cells** in REIN's dirty file.

---

## 3. Water: profile (verified)

- **Shape.** The raw file has 527 data lines × 39 fields: a date token (`D-1/3/90`) plus 38 numeric attributes. There are also 69 blank lines.
  - REIN Table 4 says 527 × 38, all numeric. That matches **after dropping the date column**.
- **The `gt` column.**
  - The raw file has no `gt` and no `index` column.
  - The REIN dictionary entry `excluded_attribs: ['index','gt']` looks like a copy of har's entry (`['Index']`, `labels_cls: ['gt']`). This is an inference.
  - If REIN did add a `gt`, it would not be counted in Table 4's 38 columns.
- **Dates.**
  - 1990-01-01 to 1991-10-30: 668 calendar days, 527 present, 141 missing.
  - Almost no Saturdays (5 of 527 rows) and no September 1991.
  - The file is not sorted by date. There are no duplicate dates.
- **Explicit MVs.** 591 `?` cells = **2.95 % of 20,026 cells**, spread over **147 rows (27.9 %)** and **31 of 38 columns**.
  - Per-column counts match the `.names` table exactly. RD-DBO-P has the most, with 62.
  - There are no other non-numeric tokens.
- **The MVs are not random.** Recomputing each derived RD-* value from its two input columns (see below):
  - 40 of the RD-* `?` cells could have been computed.
  - 13 of those would have been negative.
  - So negative performance values were blanked, which makes the missingness MNAR.
- **Disguised MVs.**
  - No negatives and no sentinels.
  - The zeros (`SED-S` 172, `SED-D` 2) are real "below detection" values.
  - `RD-SED-G = 100` in 193 rows is also real.
  - The `.names` file says Q-E min = 10000, but the measured min is 10050. That is a documentation slip only.
- **Duplicates.** No exact duplicates. The most similar pair shares 10 of 38 values, so there are no near-duplicates.
- **Robust outliers.**
  - 496 cells have \|z\| > 3.5 and 246 cells have \|z\| > 5. The 246 sit in 115 rows.
  - The distributions are heavy-tailed: skew is 13.9 for SED-S, 11.5 for DBO-S and 6.7 for SS-E.
  - 78 of the 246 cells (15 rows) fall on the 18 days that experts labelled as abnormal (storms, secondary-settler problems, solids overload). Those values are **real process events, not errors**.
- **Cross-column rules (strong):**
  - The 9 `RD-*` columns are derived: `RD-X-P = (X-P − X-D)/X-P·100`, `RD-X-S = (X-D − X-S)/X-D·100`, `RD-X-G = (X-E − X-S)/X-E·100`.
  - These match on **every** row where they are present, within rounding. The 128 RD-SED-P deviations are all explained by ±0.05 rounding of SED, and the two RD-DQO-G deviations are integer rounding.
  - So there are **0 inconsistencies in the derived columns**.
  - The definitions of RD-DBO-P, RD-SS-P and RD-SED-P use P→D, not E→P. That was verified: E→P gives a median deviation of 47–96 points.
- **Physical rules:**
  - Chemistry requires BOD ≤ COD. It is violated in 4 rows for DBO-E > DQO-E and in 1 row for DBO-S > DQO-S (D-20/3/90: 14 > 9).
  - Conductivity should be conserved through the plant. COND-D/COND-E falls outside [0.5, 2] in 3 rows:
    - D-10/8/90: COND-D = 85 while E/P/S are 828/856/891, probably a dropped digit.
    - D-5/8/90: 292 vs 1350.
    - D-8/10/90: 810 vs 2130.
  - PH-S is 9.7 on D-10/2/91 while the upstream pH is 8.0/8.0/7.9.
  - Stage order is violated in two groups:
    - **DBO-P < DBO-D:** 7 rows, 3 of them by more than 15 %.
    - **SS-D < SS-S** (4 rows) and **DBO-D < DBO-S** (2 rows): all on 13–16 Mar 1990, which the experts labelled as secondary-settler-problem days. Those are real events.
- **Label.**
  - The `.names` file lists 13 classes by date. They were produced by the LINNEO+ conceptual-clustering algorithm, not by human labelling.
  - Reconstructed: 523 of 527 rows get a class. The 4 unlabelled rows are D-5/8 to D-8/8/91. No date conflicts.
  - The 4 large classes hold 509 rows (96.6 %): class 1 = 275, class 5 = 116, class 9 = 65, class 11 = 53.
  - 9 rare classes hold 14 rows.
  - The `.names` file's own class counts are wrong twice: class 4 says 1 day but lists 4; class 9 says 69 but only 65 of its dates are in the data.
  - REIN's `n_clusters: 4` matches the four large classes. Whether that was deliberate is unknown.

### Ground truth (water)

- **Verified:** the raw file is **real sensor data with its own errors**. There is no clean version anywhere. Measured:
  - 591 explicit MVs: 2.95 % of cells, 27.9 % of rows, MNAR in part.
  - About 9 rows with clear rule-breaking values (3 conductivity breaks, 5 BOD > COD, 1 pH jump), plus 3 large BOD stage inversions.
  - 168 extreme cells on "normal" days that are ambiguous.
  - The rest of the extreme values are real events.
- **If REIN used the raw file as `clean.csv`** (inference, since the shape matches Table 4):
  1. All real anomalies count as "clean", so a detector that finds the 85-µS conductivity or the BOD > COD rows is scored as a false positive.
  2. **`?` handling decides a lot.**
     - REIN reads `clean.csv` with pandas defaults (`rein/datasets.py:82`), so `?` stays a string. Every column that contains a `?` then becomes object dtype.
     - Verified: only **7 of 38 columns** (PH-E, COND-E, PH-P, SS-P, COND-P, PH-D, COND-D) stay numeric.
     - `__inject_outlier` uses `select_dtypes("number")` (`rein/datasets.py:595`), so injected outliers would land in only 18 % of the columns.
  3. **The GE profiler would flag the clean MVs.** It treats `?` as a missing token (`expectations_profiler.py`, `MISSING_TOKENS`), so both profiled tiers would flag all 591 clean `?` cells as false positives.
  4. **This caps precision.** At Table 4's rate of 0.14, about 2,804 cells would be injected (if the 0.14 counts injected cells only). A detector that also flags every real MV is held to precision ≤ 2804/(2804 + 591) ≈ **0.83**.

---

## 4. Fit for this benchmark

| | print3d | water |
|---|---|---|
| ML task | Regression on `tension_strenght`. Valid, but 50 rows → about 15 test rows per split, so RMSE over 10 seeds is noise-dominated | REIN: clustering. Block D has no clustering task (decided 6 Oct). The only label is the algorithm-induced 13-class list (4 classes cover 96.6 %); it is circular because it was clustered from the same features. A binary normal/abnormal label would have 14 positives (2.7 %) |
| Size and Raha | 20 labelled tuples = **40 % of rows**, and the evaluation includes the labelled cells, so Raha's score is mostly the oracle. About 30 error cells, so each true positive is worth 3.3 recall points | 20/527 = 3.8 % labelled. Fine. 527 × 38 is fast for every tool |
| GE | Hand-written suite is trivial: value-set regexes for layer_height, bed, fan, nozzle, speed, material, pattern. The profiler builds **no value sets on numeric columns**, so the profiled tiers only catch type violations and MV tokens | Hand-written: 38 `between` ranges plus regex. The physical rules (BOD ≤ COD, COND conservation, RD formulas) need **column-pair expectations, which the GE wrapper does not support**: it calls `method(column, **kwargs)` (`rein/detectors.py:635–700`) |
| HoloClean | Clear FDs exist (layer_height→print_speed, bed↔fan, 18 design FDs on column pairs), so FDX → DCs should work. FDX was not run here (rules forbid docker). But duplicates injected as copies of real rows satisfy every FD, so HoloClean cannot see them | No unary FD with LHS uniqueness < 0.9. The RD formulas hold as FDs on 7 of 9 columns, but the LHS pairs are 90–100 % unique, so `EQ` DCs can never fire. **Expect 0 usable DCs (same as soilmoisture); HoloClean = null detector only.** (Inference, FDX not run) |
| Error types not yet covered | **Duplicates** (from REIN's declaration). But `create_dirty.py` has no duplicate injector (ErrorType: swapping, implicit_mv, explicit_mv, noise, typos, outliers). Appended rows crash the oracle (`get_actual_errors` reads `groundTruthDF.iat[i]` by dirty row index), so duplicates must overwrite rows, which makes them multi-cell value swaps (already covered by breast_cancer). | Real-world errors beyond beers, but with **no ground truth**. **Numeric disguised MVs:** REIN's generator writes `20030101` in 5 columns (SED-E/P/D/S, SSV-D) and `-1` in RD-SS-P and RD-SS-G. The other 31 columns get `'N/A'`, which beers already covers. **Derived-column inconsistencies** (RD-*) would be new, but none of the three tools can express arithmetic constraints. |

**REIN's implicit-MV generator** (`tools/error-generator/.../implicit_missing_value.py`) picks a token by how similar the column name is to its dictionary keys. Verified with the exact code:
- On print3d it would write `Alabama` into nozzle_temperature, `...@gmail.com` into material, `Afghanistan` into roughness, `20010101` into bed_temperature and infill_pattern, `?` into wall_thickness, and `N/A` into 3 columns.
- Those are type violations, not realistic disguised MVs, and any number regex catches them.

---

## 5. Integration effort before the 15 Oct freeze (estimates)

**print3d: about 0.5–1 day of work, but most of it is designing and defending an error injection that REIN never published.**
1. `clean.csv` = Kaggle `data.csv`.
2. Write a dirty generator for about 30 cells (MVs, implicit MVs, duplicates as row overwrites).
   - Keep the column order: `create_dirty.py` mutes `labels_reg` and joins it back **at the end** (`rein/datasets.py:764–766`).
   - Otherwise Raha's positional diff breaks, the same defect as smartfactory.
3. Hand-written GE suite (about 12 rules, 30 min).
4. FDX + `fds_to_dcs` (minutes). Raha cache and 10 seeds (minutes).
- The results would be "our print3d", not REIN's.

**water: about 1–1.5 days.**
1. Choose a ground-truth policy:
   - (a) keep `?` → must become `''` so the columns stay numeric, and the 591 real MVs count as clean;
   - (b) drop the 147 rows with MVs → 380 rows;
   - (c) impute → this fabricates ground truth.
2. Drop the date column and inject errors (`create_dirty.py --error_type outliers implicit_mv --error_rate 0.14`). Check the outlier multiplier against the existing σ = 4.
3. Write a 38-range GE suite.
4. Run FDX; expect 0 DCs.
5. Raha cache.
6. No Block D.

---

## 6. Recommendation

**print3d: exclude.**
1. **Too small to measure anything.** 50 rows / 600 cells means about 30 error cells, so the F1 granularity is 3.3 points. Raha sees 40 % of the rows through its oracle.
2. **The dirty file cannot be reproduced.** REIN's version was made by hand and was never published. Any version we inject is our own design and not comparable with REIN.
3. **Duplicates, its one new error type, do not fit.** The same-shape cell-diff ground truth cannot hold extra rows, and once written as row overwrites they reduce to value swaps.
4. **Block D cannot use it.** A 50-row regression gives about 15 test rows, and the Block D dataset set is already fixed.
5. **No real errors to study.** The raw file has 0 detectable real errors.

At most, the thesis can mention it as a non-reproducible REIN dataset (a threat to validity or a C1 footnote).

**water: exclude from the main tables. Case study only if time is left after the Block D core gate (11 Oct).**
1. **It adds no new injected error type.** Outliers + MVs repeat har/mercedes/soilmoisture, and its implicit MVs are mostly `'N/A'`, which beers already has.
2. **HoloClean has nothing to work with.** It will almost certainly get 0 DCs.
3. **No Block D label.**
4. **The real errors have no ground truth, and the most likely REIN setup (raw file as `clean.csv`) scores real anomalies as false positives.** If `?` is left as a string, injection is also silently limited to 7 of 38 columns.

**Possible cheap case study:** run the five configurations on the **raw** water file and check, without computing F1, whether they flag:
- the 9 measured real-error rows;
- the 591 real MVs;
- the 18 expert-labelled abnormal days (real events that a good detector should *not* call errors).

That would give the thesis its only real-error evidence beyond beers.

---

## Verified vs inferred

- **Verified (measured or read in code):** all hashes and sizes; shapes; MV counts; dtypes; duplicates; MAD outliers; FDs; RD-formula consistency; BOD/COD and conductivity violations; class reconstruction; REIN's CSV reading and outlier dtype filter; GE profiler tokens; the GE wrapper being single-column only; the implicit-MV tokens; the missing duplicate injector; the oracle failing on extra rows.
- **Inferred:**
  - REIN used the Kaggle and UCI raw files as `clean.csv` (shape match).
  - The `gt`/`index` exclusion in the water entry was copied from har.
  - FDX outcomes (not run).
  - The precision cap of 0.83, which assumes 0.14 counts injected cells only.
  - The effort estimates.
