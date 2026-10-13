# Block D spec: `scripts/blockd_driver.py` and `scripts/blockd_analysis.py`

## 1. Run convention
- The driver follows `robustness_driver.py`. `--out` is required (`robustness_driver.py:200`). Inputs are copied to scratch before use (`:232-242`). The exit code is non-zero on failure (`:289`).
- Run it with `docker compose run --rm -T rein python3 scripts/blockd_driver.py --out reports/block_d/<run> ...`, following `reports/robustness/run_all.sh:12`.
- It never imports `rein.benchmark`. Importing datawig resets the NumPy seed to 42, so every random draw uses its own RNG object.

## 2. CLI (driver)
| arg | default |
|---|---|
| `--datasets` | `breast_cancer nasa` (extension: `bike adult`) |
| `--flags_dir` (required) | `<dir>/<ds>/{ge_dirty_profiled,ge_clean_profiled,ge_hand_written,holoclean,raha}.csv` + `expected.json` |
| `--data_root` | `/rein/datasets` |
| `--out` (required) | Refuses any path under `rein-datasets/`, `results/` or `detection_logs/` |
| `--seeds` | `0-9` |
| `--models` | `linear rf xgb` |
| `--jobs` | 1. Runs seeds in parallel processes; models always use `n_jobs=1` |
| `--dry_run` | Builds every version and runs checks 2 and 3. No training. Prints the version table |
| `--check` | Dry run plus check 1: trains only perfect+GT and S4, for all seeds and models |
| `--allow_flag_mismatch` | For development only. Recorded in the manifest |

## 3. Inputs
- The driver copies `clean.csv`, `dirty.csv`, `actual_errors.csv` and the five flag files to `<out>/inputs/<ds>/`. It records each file's sha256 and reads only these copies.
- Flag and error files have no header. Rows are `row,col[,value]`: 0-based positions that match the column order of `dirty.csv` (identical to `clean.csv` in all four datasets).
- An empty file is an empty set. `adult/greatExpectations/detections.csv` is 0 bytes and makes `read_csv` raise `EmptyDataError`.
- `expected.json` holds the Table 3 TP/FP/detection counts (`results/runs_log.csv`):

| ds | GE dirty-prof. | GE clean-prof. | GE hand-written | HoloClean | Raha |
|---|---|---|---|---|---|
| bc | 247/13/260 | 278/13/291 | 438/22/460 | 416/5275/5691 | 317/78/395 |
| nasa | 30/0/30 | 384/0/384 | 680/0/680 | 556/5709/6265 | 710/1864/2574 |
| bike | 0/0/0 | 0/0/0 | 24247/0/24247 | 25134/173845/198979 | 30861/15138/45999 |
| adult | 0/0/0 | 0/0/0 | 0/0/0 | 1677/663530/665207 | 865/5081/5946 |

## 4. Feature schema
The schema is fixed once from `clean.csv`.
- **Features:** every column except the label and the excluded columns.
  - bc excludes the unnamed index (`Unnamed: 0`, renamed `""` in `tuning_example.py:40`) and `Sample code number`.
  - bike excludes `instant`, `dteday`, `casual` and `registered` (`casual + registered = cnt`).
- **Column types:**
  - A column is numeric if at least 90 % of its clean values parse. bc `Bare Nuclei` has 16 `?` values in the clean data, so a strict all-values rule would wrongly make it categorical.
  - Otherwise the column is categorical: the eight adult string columns.
- **Featurization** is fitted on the kept training rows of each version:
  - numeric: coerce, then fill NaN with the training mean (the same statistic as impute);
  - linear model only: `StandardScaler`;
  - categorical: `OneHotEncoder(handle_unknown='ignore')`;
  - `ColumnTransformer(sparse_threshold=0)`, so the output is dense.
- **Labels** are encoded as 1 = minority class: bc `class=='4'` (malignant); adult `income=='0'` (>50K; the clean data has 11,208 of these vs 34,014 `1`). Regression labels are float.
- An unflagged label that does not parse means abort. The pilot silently mapped it to 0 or to the mean (`tuning_example.py:152-154`).

## 5. Data versions (27 per dataset)
- **Flag sets (7):** the 5 configurations, `perfect` (= `actual_errors`) and `always_positive` (every cell).
- **Versions:** 7 flag sets × 3 policies (GT repair, delete, impute) = 21, plus 5 random-deletion controls, plus 1 floor (`no_detection`, the dirty data as is).
- **Random control:** for configuration *c* in seed *s*, let *k* be the number of training rows that *c* deletes. Delete *k* random training rows using `np.random.default_rng([s, c_idx])`. Scored in S2 only.

## 6. Split, policies, scenarios
- **Split:** `train_test_split(arange(n), test_size=0.2, random_state=seed, stratify=y_clean)` for classification; not stratified for regression (`tuning_example.py:121-122`). The split is shared by all versions. Rows stay sorted by row id.
- **How each policy acts on the training split.** Each policy is applied the same way to the test rows for S1/S3. False flags never touch the S2 test set.
  - **GT repair:** each flagged cell gets its clean value. A false flag changes nothing.
  - **Delete:** every row with at least one flag is removed.
  - **Impute:**
    - A flagged numeric feature cell gets the mean of the unflagged, parsable cells in the kept training rows; a flagged categorical cell gets their mode.
    - A column with no unflagged training value becomes constant (0.0 or `"__none__"`; `tuning_example.py:62-63`).
    - A row with a flagged label is dropped; labels are never imputed (`:64-65`).
    - Deliberate change: the pilot took its statistics over all training rows (`:59`).
- **Scenarios** (`rein/models.py:93-96, 105`):
  - S1 = version model on the version's test rows, with the version's labels;
  - **S2 = version model on the full clean test split** (the ranking score);
  - S3 = clean model on the version's test rows;
  - S4 = clean model on the clean test split.
  - The pilot filled the test set with the clean training mean (`tuning_example.py:123`). The driver uses the featurizer of each version instead.
- **Degenerate:** fewer than 50 kept training rows, or only one class. No model is trained, `degenerate=1` is set and the score is empty. If S1/S3 has an empty or one-class test set, that score is NaN and `test_degenerate=1`.

## 7. Models and scores
- **Models:**
  - linear: `LogisticRegression(max_iter=5000)` or `Ridge()`;
  - `RandomForest*`;
  - `XGB*(use_label_encoder=False, eval_metric='logloss', verbosity=0)` (xgboost 1.3.3).
  - Defaults throughout, `random_state=0` and `n_jobs=1`, with no tuning. Convergence warnings are counted.
- **Scores:**
  - classification: minority-class F1, plus precision and recall;
  - regression: RMSE and R².
  - The analysis orients scores so that higher is better (it uses −RMSE).

## 8. Output
**`<out>/results.csv`** has one row per dataset × version × policy × model × seed × scenario, with these columns:
`dataset, task, version, configuration, policy, model, seed, scenario, score, f1|rmse, r2, precision, recall, rows_kept, test_rows, cells_changed, errors_left_in_features, flagged_label_cells, degenerate, test_degenerate, train_hash, fit_s, timestamp`

Column notes:
- `cells_changed`: schema cells the policy altered in training.
- `errors_left_in_features`: training cells in schema columns whose value differs from the clean value after featurization. `3.0` vs `3` does not count.
- `train_hash`: sha256 of the featurized training matrix plus labels.

**`<out>/manifest.json`** records:
- git HEAD and `git status --porcelain` (git 2.25 is in the image);
- Python version, sklearn 0.24.2, xgboost 1.3.3, scipy 1.7.1, numpy 1.21.2, pandas 1.3.3;
- the platform (x86_64 under Rosetta);
- the CLI arguments;
- the sha256 of every input;
- expected vs recomputed TP/FP/detections;
- wall time per dataset.

## 9. Checks (any failure aborts)
1. **Perfect + GT repair equals S4 exactly** for every seed and model: identical `train_hash` and S2 = S4. The same must hold for always_positive + GT repair.
2. **An empty flag set equals the floor** under every policy: a synthetic empty set gives the floor's hash. Configurations with zero flags inherit this: bike GE dirty- and clean-profiled, and all three adult GE tiers.
3. **Flag files match Table 3:** TP/FP/detections recomputed against `actual_errors` must equal `expected.json`, with no duplicate or out-of-range cells.
   - The files on disk fail today:
     - Raha: bc 407 vs 395, nasa 2595 vs 2574, bike 46001 vs 45999, adult 5514 vs 5946;
     - adult HoloClean: 341,890 vs 665,207;
     - GE: only the last tier is on disk.
   - So all flags must be regenerated first.

## 10. Analysis script (`blockd_analysis.py --results ... --flags_dir ... --out ...`)
- **Mean S2:** mean ± sd of S2 per dataset × policy × model × version, plus the number of degenerate versions.
- **Pairwise verdicts:** for each of the 10 configuration pairs, take the oriented per-seed differences.
  - Identical `train_hash` on all seeds means tie.
  - Otherwise drop zero differences. If `n_nonzero ≤ 5`, the pair is a tie. Otherwise use `wilcoxon(nz, mode='exact')`: p < 0.05 gives a direction, else tie.
  - Compared with the reference, each pair is concordant, discordant or tied.
- **Pooled share of concordant pairs per policy,** across datasets × models.
  - Exact permutation test: permute the reference scores within each dataset (one permutation shared by all models, 5! = 120).
  - Convolve the per-dataset count distributions; p is one-sided.
- **Kendall τ-b** per dataset × policy × model, on mean S2 vs reference. Descriptive only.
  - Report its maximum `(n0 − |T_ref ∪ T_down|)/√((n0−n_ref)(n0−n_down))`, where n0 = 10 pairs, n_ref and n_down are the tied pairs in each ranking and T_ref ∪ T_down is the set of pairs tied in either.
  - With no downstream ties this gives bike 0.95 and adult 0.84.
- **Share of gap closed:** `(S2 − floor)/(S4 − floor)`, reported only where S4 beats the floor by the pair rule.
- **Three reference rankings:**
  1. Table 3 cell F1, recomputed from the flags;
  2. Table 7 row F1, rebuilt from the flags (a row is flagged if any of its cells is);
  3. model-visible F1: the truth is restricted to actual errors in schema columns that change after featurization.
- **Degenerate versions:** reported twice, once ranked last and once left out.

## 11. Runtime
Single fits measured in the container (seconds; linear / RF / XGB):

| ds | train rows | fit time |
|---|---|---|
| bc | 559 | 0.0 / 0.1 / 0.1 |
| nasa | 1202 | 0.0 / 0.2 / 0.1 |
| bike | 13903 | 0.0 / 2.9 / 0.6 |
| adult | 36177 | 0.6 / 15.9 / 2.2 |

- At 270 version-seeds × 3 models, the serial upper bounds are: bc ≈ 1 min, nasa ≈ 1.5 min, bike ≈ 16 min, adult ≈ 85 min.
- With `--jobs 5` on 10 cores, adult takes about 20 min.
- Building the versions must be vectorized (index the mask with numpy). The pilot's `iat` loop (`tuning_example.py:56-58`) is too slow for 665k flags.

## 12. Pitfalls to test for
- **Label flags:**
  - HoloClean flags every bc `class` cell (699).
  - It also flags 17,366 of 17,379 bike `cnt` cells and 934 nasa target cells. nasa and bike targets have no errors, so these are all false positives.
  - So bc and bike HoloClean are degenerate under impute.
- **Degenerate under delete:** bc HoloClean (all 699 rows touched), nasa Raha (all 1,503 rows) and bike HoloClean (all 17,379 rows).
- **adult:** every flagged row has a flagged label, so delete and impute should give identical hashes. Test this.
- **adult:** after delete, about 1.4k rows remain under HoloClean. Check for one class.
- **SciPy 1.7.1:** `wilcoxon` silently falls back to the normal approximation when there are zeros, which is anti-conservative.
- **XGBoost on sparse input** treats absent entries as missing, so the input must be dense.
- **Orientation:** RMSE must be oriented (lower is better), and F1 uses the encoded minority class.
- **Stratify on clean labels,** not dirty ones.
- **Excluded columns** (bc 47 + 60 errors, bike instant/dteday/casual/registered) must not count in `cells_changed` or `errors_left`.
- **RF row order:** keep row-id order so that identical data gives an identical model.
- **No-flag configurations:** bike GE dirty- and clean-profiled and adult GE give ties in the reference itself.

## 13. Open decisions for the user
1. **Reference-tied pairs:** leave them out of the concordance share (proposed) or count them.
2. **Impute statistics:** taken over kept rows (proposed) or over all training rows (as in the pilot).
3. **Model seed:** fixed `random_state=0` (proposed, as in the pilot) or seed = split seed.
