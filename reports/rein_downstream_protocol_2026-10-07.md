# How REIN tested downstream impact: protocol, hidden steps and training counts

Date: 7 Oct 2026.

Sources:
- the paper `REIN.pdf`, which is arXiv 2302.04702v1. Its text is word-for-word the EDBT 2023 version (pp. 499–511); there is no extended version.
- REIN's original code, commit `b389550`. Line numbers below are from this commit unless they are marked HEAD.

How the report was checked:
- Five agents extracted facts and six independent verifiers checked them.
- One verifier ran REIN's original `run_models` inside the container on scratch copies, counting every `fit`.
- The Figure 7 spokes and scatter markers were counted from the PDF (images and vector data).
- The repo was not modified.

**Provenance.** The training code is the same in three places:
- the upstream tip `b8a0727` (2024-07-24), byte for byte;
- `b389550`;
- your HEAD, which adds one logging argument in `train_model.py` and one unused `preprocess(return_index)` option.

Everything below therefore also holds for your fork.

---

## 0. Short answer

| Question | Paper says | Code does |
|---|---|---|
| Unit of work | one "experiment" per (data version, model, repetition): (ε+1)·h·s per dataset (p.2) | one `train_and_test` call per (version, model, run). Each call trains **2 models**: one on the version's train split (gives S1, S2) and one on the clean train split (gives S3, S4) |
| Data versions | ε = m detectors × k repair methods, + 1 dirty (p.2); ε never given | dirty.csv + every `repaired.csv` on disk. Ground truth is **not** a version; its model is retrained inside every call |
| Models | 12 C, 11 R, 6 clustering, 2 AutoML (Table 2); "33" in the conclusion | `train_model.py` without `--ml_models` runs all of `models_dictionary`: 14 C, 13 R, 6 clustering |
| Hyperparameters | not given | default: `fixed_params`, which are mostly sklearn defaults. Tuning searches **1–3 hyperparameters** in 17 models; the other 12 are never tuned |
| Tuning | Optuna, "Bayesian-based informed search"; not for AutoML (p.4) | off by default. When on: **5 random trials × 5-fold CV on the clean train split**, and the winner is refit on both data sets. The README's example command switches tuning **on** by accident |
| Seeds | "repeated ten times with different random seeds that control the train-test split", means reported (p.5) | 10 runs. Each run draws a fresh seed from OS entropy (`randint(1000)`), which is never stored and differs per version and model. The optional early stop leaves 7 runs trained and 6 stored |
| Split | not given | 80/20, shuffled, not stratified. Done after dropping every row with a NaN, separately for the clean data and for the version |
| Trainings per call | — | **62** without tuning (2 + 60 hidden CV fits); **27** with tuning (5×5 + 2); **6** for clustering |

Whether the paper's figures were made with tuning on cannot be decided (§3.4). The published code also cannot have produced several of the figures as shipped (§6).

---

## 1. The pipeline, step by step (what happens in the background)

The three phases are separate scripts. They pass data only through files on disk; with `--store_postgres` they pass it through the database instead.

**Step 1 – Data.** Each dataset has `clean.csv` (ground truth) and `dirty.csv`. Table 4 lists 14 datasets; 13 have an ML task (5 classification, 5 regression, 3 clustering).
- Each dataset has **one** dirty version. Error rates are varied only in the detection-robustness experiment, never downstream.
- The code dictionary (`datasets_dictionary.py`) defines the label column, the task, the excluded columns and a fixed k for clustering.

**Step 2 – Detection** (`scripts/detect_errors.py`).
- Every detector writes `<ds>/<detector>/detections.csv`.
- There are 10 runs by default, but the file is overwritten each time, so **only the last run reaches repair**.

**Step 3 – Repair** (`scripts/repair_errors.py`, `benchmark.py:724-831`).
- Every detector folder is paired with **every** repair configuration of the dataset: the union over all of the dataset's error types. The per-detector filter is commented out (`:758`, `:761`).
- Each pair writes `<ds>/<detector>/<repair-config>/repaired.csv`. There are 10 runs; the file is overwritten, so the last run is kept.
- **Repair works on the whole file, train and test rows together, before any split.** Mean/mode statistics and missForest/DataWig models therefore see the future test rows, and the label column too.
- ML-oriented methods (ActiveClean, BoostClean, CPClean, cleanlab) write no file. They train their own model in this phase (S5, see §4.6).

**Step 4 – Versions to train on** (`train_model.py` → `run_models`, `benchmark.py:533-540`).
- The list is `dirty.csv` + every `repaired.csv` that `os.walk` finds, including stale files from earlier runs.
- Versions with fewer than 50 rows (counted before dropna) are skipped.

**Step 5 – One run (one call)** (`benchmark.py:581-639`, `models.py`):
1. A new `Models()` object calls `np.random.seed()` (OS entropy) and then draws `split_seed = randint(1000)` (`models.py:45-46`).
2. It loads `clean.csv` and the version and **drops every row that has any NaN** (`:431-433`).
   - So "dirty" (D0) is in effect dirty data with listwise deletion. Dirty rows kept: breast_cancer 452/699, beers 1,325/2,410, soilmoisture 477/679.
   - The clean beers file itself keeps only 1,403/2,410 rows.
3. Excluded columns are dropped, if the dataset defines any.
4. The clean data and the version are split **separately**, 80/20, with the same seed and no stratification (`:324-328`, `:453-455`). Clustering has no split.
   - The rows match only when both frames have the same length after dropna.
   - Measured: a repaired version with all 699 rows had identical test rows (Jaccard 1.0). Dirty breast_cancer and dirty nasa shared only 5–16 % of their test rows with the clean split.
5. Featurization: each frame gets its own ColumnTransformer (StandardScaler on numbers, one-hot on text), fit on its own train split (`:471-495`).
   - If the two frames produce a different number of features, **S2 and S3 are skipped and stored as 0, 0, 0** (`:497-501`).
   - One stray string turns a numeric column into text. Dirty nasa gives 489 features against 5 in the clean data, and dirty breast_cancer 752 against 21. So their S2/S3 are 0.
6. Labels: a `LabelEncoder` is refit separately on each of the four label arrays (`:506-510`). The class codes can therefore disagree between train and test (see §6).
7. Two models are trained, tuned or untuned (§3.4). Then S1–S4 are predicted and scored, and one row is appended to `datasets/<ds>/results/model_results.csv`.

**Step 6 – Repeat.** 10 runs (`--n_iterations 10`). The optional early stop (`:627-629`) is described in §3.5.

**Step 7 – A/B test** (`:643-648`).
- `wilcoxon(S1 of each run, S4 of each run)` per (version, model), written to `abtesting.csv` together with Pearson r under the name "effect_size".
- Only S1 against S4 is tested. There is no correction for multiple tests.
- If every difference is zero, scipy raises an error, which is swallowed, and no row is written.

**Step 8 – Figures.** The plotting and averaging code is not in the repo.

### Scenarios

| | train on | test on | in the code |
|---|---|---|---|
| S1 | version | version | version model, version test split |
| S2 | version | clean | version model, clean test split; 0 if feature widths differ |
| S3 | clean | version | clean model, version test split; 0 if feature widths differ |
| S4 | clean | clean | clean model, clean test split. Recomputed in **every** call on that call's split |
| S5 | repaired | dirty | only inside BoostClean/CPClean (repair phase); never in `run_models` |

- Two fitted models serve all four scenarios.
- **Clustering:** each scenario calls `fit_predict`, which refits (`:188-191`). So S2 is the S4 procedure and S3 the S1 procedure, differing only by random init.

---

## 2. Which and how many data versions

**Paper (p.2):** ε = m × k repaired versions per dataset; there are (ε+1)·h·s experiments, where +1 is the dirty version. ε is never stated for any dataset.

**Code maximum** (default dictionaries; every detector and repair succeeds; `constraints/` present):
- m = detector folders, with outlierdetector counted as 3 (IF, IQR, SD) and FAHES as 1.
- k = file-writing repair configurations:
  - standardImputer: 7 (delete, plus mean/median/mode for numbers × mode/"dummy" for text)
  - mlImputer: 7
  - one each: GT repair, Baran, HoloClean, duplicatesCleaner, OpenRefine

| dataset | task | m × k | versions (ε+1) |
|---|---|---|---|
| beers | C (551 classes) | 12 × 17 | 205 |
| citation | C | 11 × 11 | 122 (111 after the cleanlab bug, see note) |
| adult | C | 13 × 17 | 222 |
| breast_cancer | C | 16 × 17 | 273 |
| smartfactory | C | 10 × 16 | 161 |
| nasa | R | 13 × 17 | 222 |
| bike | R | 15 × 17 | 256 |
| soilmoisture | R | 13 × 17 | 222 |
| print3d | R | 13 × 19 | 248 (229 after the cleanlab bug) |
| mercedes | R | 13 × 17 | 222 |
| soccer | R in the code ("–" in the paper) | 16 × 17 | 273 |
| water / har | UC | 13 × 17 | 222 each |
| power | UC | 10 × 16 | 161 |
| **total** | | | **3,031** (3,001 corrected) |

Note: the cleanlab detector writes to `cleanlab-forest_clf/` (`detectors.py:1861`), but repair looks in `cleanlab/`. Its detections are therefore never repaired.

**What the paper actually shows (Figure 7, p.11)** is far fewer versions. The radar chart shows one model's versions; the scatter shows one marker per (version, model) pair. Both were counted from the PDF.

| dataset | radar model: versions | scatter: (version, model) pairs |
|---|---|---|
| Beers | MLP: 18 | 471 (RF, XGB, GNB 109 each; KNN 108; Logit, MLP 18 each) |
| Adult | SVC: 31 | 256 |
| Breast Cancer | XGB: 28 | 285 |
| Citation | Ridge: 25 | 219 |
| Smart Factory | RF: 61 | no scatter (61) |
| Nasa | DT: 149 | 872 (867–872) |
| Soil Moisture | KNN / RANSAC / BayesRidge: 39 | 429 |
| Water | Birch: 75 | 397 |
| Power | KMeans: 54 | 140 |
| HAR | no radar | 93 |
| **total** | | **3,223 pairs** |

- The number of versions differs by model. On Beers, MLP has 18 and RF has 109; on Power, KMeans has 54 and Birch has 2.
- So "radar versions × models" is not a valid estimate.
- Bikes, 3D Printer and Mercedes have no downstream results.

---

## 3. Models, hyperparameters, tuning, seeds

### 3.1 How a model is trained
- scikit-learn 0.24.2 and xgboost 1.3.3.
- Without tuning, the model is the constructor with `fixed_params`. No `random_state` is passed, except AffinityPropagation, which gets `random_state=None`.
- Every call trains a fresh model on the version and a fresh model on the clean data.

### 3.2 Hyperparameters per model (`models_dictionary.py`, `hyperopt_functions.py`)

The search space that is actually used is the Optuna code in `hyperopt_functions.py`. The `hyperparams` grids in `models_dictionary` only switch tuning on or off (`models.py:777`) and feed a GridSearch helper that is never called (`:253-293`, call commented out at `:792`).

| model | fixed_params (used without tuning) | tuned by Optuna | # |
|---|---|---|---|
| RF clf | {} (100 trees) | criterion {gini, entropy}, max_depth 2–32 (log), n_estimators 100–500 | 3 |
| Logit | max_iter 5000, multi_class auto | C 0.1–100, penalty {none, l2} | 2 |
| SVC | cache_size 7000 | C 0.1–100, kernel (4 options), degree 3–6 | 3 |
| SGD | max_iter 1000, tol 1e-3 | penalty {l1, l2, elasticnet} | 1 |
| KNN clf | {} | metric (3), n_neighbors 1–100, weights (2) | 3 |
| DT clf | {} | criterion (2), max_features {sqrt, auto, log2} | 2 |
| AdaBoost clf | n_estimators 200 | n_estimators 50–200 (log), learning_rate 0.1–1 | 2 |
| XGB clf | eval_metric logloss | max_depth 1–100, gamma 0.1–5 | 2 |
| Ridge clf | {} | alpha 1e-4–1 | 1 |
| MLP clf | {} | alpha 1e-4–1, activation (4), learning_rate (3) | 3 |
| GaussianNB, MultinomialNB | {} | — | 0 |
| DT reg | {} | max_depth 2–150 (log) | 1 |
| RF reg | {} | criterion {mse, mae}, max_depth 2–32, n_estimators 100–500 | 3 |
| AdaBoost reg | {} | loss (3), n_estimators 50–200, learning_rate 0.1–1 | 3 |
| SVR | {} | kernel (4), C 0.1–100 | 2 |
| MLP reg | max_iter 1000 | activation (4), learning_rate (3) | 2 |
| Ridge reg | {} | alpha 1e-4–1 | 1 |
| KNN reg | {} | metric (3), n_neighbors 1–100, weights (2) | 3 |
| Linear, BayesRidge, XGB reg, RANSAC (min_samples 10) | as listed | — | 0 |
| GMM | n_components 2 (ignores the dataset's k) | none: no Optuna branch | 0 |
| KMeans, Agglomerative, Birch | n_clusters = dataset k (power 2, water 4, har 2) | none | 0 |
| OPTICS | min_samples 5 | none | 0 |
| AffinityPropagation | damping 0.9, max_iter 1000 | none | 0 |
| Auto-sklearn | 180 s per fit | — (KeyError if tuning is on) | — |
| TPOT | 5 generations × 50 population, cv 5 | — (KeyError if tuning is on) | — |

In total, **17 models are tunable** (10 classifiers with 22 hyperparameters, 7 regressors with 15). The other 12 models and AutoML are never tuned.

### 3.3 The paper's "silhouette to find k"
- k is hard-coded in the dictionary.
- The silhouette k-search (`datasets.py:171-208`, k = 2–14) is an offline helper that only draws a plot, and its call is commented out.

### 3.4 Tuning: what happens when it is on (`models.py:777-789`)
1. Optuna searches on the **clean train split only** (80 % of the clean rows left after dropna).
2. `create_study(direction="maximize")` is called without a sampler and without a seed. Optuna 2.7.0's TPE sampler draws its first 10 trials at random, so **5 trials = an unseeded random search, not Bayesian**.
3. Each trial runs `cross_val_score(cv=5)` with the default score: accuracy for classifiers (StratifiedKFold), R² for regressors (KFold). The folds are not shuffled.
4. The winning settings are refit **once on the clean train split and once on the version's train split**, so the version's model gets settings chosen on clean data.
   - The refit **drops `fixed_params`**: Logit falls back to max_iter 100, MLP reg to 200, and XGB loses eval_metric.
5. The search is redone in **every call**, i.e. per version × run × model. The clean model is therefore re-tuned hundreds of times per dataset.
6. Side effects:
   - clustering models get bare constructors (KMeans with 8 clusters; GMM with 1 component, which crashes);
   - AutoML raises a KeyError and stores nothing;
   - the `_opt` suffix in the results follows the flag, not whether tuning really ran.

**Was tuning on for the paper?** It cannot be decided.

| Points to "on" | Points to "off" |
|---|---|
| The paper says Optuna was used for every model except AutoML. | Tuning is off by default (`train_model.py:26`, `run_models`). |
| The README example `--hyperopt False --early_termination False` turns both **on**, because argparse `type=bool` turns any non-empty string into True. | With the published code, GMM (Figs. 7p/r/t) and TPOT (Fig. 7e) can only produce results with tuning **off**. |

No `_opt` result files exist anywhere.

### 3.5 Seeds and repetitions
- There are **10 runs**: `range(iterations)` with `--n_iterations 10`.
- Every run of every version and model draws its **own** split seed, `np.random.seed()` + `randint(1000)`.
  - Measured: 10 different seeds per version, and different seeds across versions for the same run number.
  - The seeds are never stored. Only 1,000 values are possible, so 10 draws repeat a seed with about 4.4 % probability.
  - Models get no seed. The global reseed also overrides DataWig's import-time seed of 42.
  - So nothing is reproducible, and run *i* of version A is **not** paired with run *i* of version B.
- **Early termination** (`--early_termination`, or the README command by accident):
  - From run index 6 on, the loop stops if |mean(S4) − S4| < 0.5, and it stops *before* storing that run.
  - For F1 this almost always fires: **7 runs trained, 6 rows stored, Wilcoxon over 7**.
  - For regression S4 is the RMSE in target units, so it fires less often.
- Wilcoxon: scipy 1.7.1 uses the exact test for n ≤ 25 when no difference is zero. The smallest possible two-sided p is 0.0625 at n = 5, 0.031 at n = 6 and 0.016 at n = 7.

---

## 4. Training counts, in the style of your plan

**1. What one training is.** One `fit` of one model on one set of training rows. REIN's "experiment" (the unit of the paper's formula) is one call `train_and_test` = one (data version, model, run). One call contains **2 trainings that produce results**:

```
model A on the version's train split  -> S1, S2
model B on the clean train split      -> S3, S4
= 2 result trainings per call
```

**2. Where 62 comes from (tuning off, the code default; classification and regression).** After fitting A and B, REIN also cross-validates each of them with `RepeatedKFold(10 folds × 3 repeats)`. The scores are MAE, even for classifiers; they are only written to the log, never stored, and nothing is chosen with them (`models.py:814-821`).

```
per model:  1 setting × (10 folds × 3 repeats) = 30, + 1 real fit = 31
per call:   2 models × 31 = 62 trainings   (2 of them produce results)
```

This is numerically your "31", but here nothing is selected.

**3. Where 27 comes from (tuning on, a tunable model).**

```
5 settings × 5 folds          = 25 trainings  (all on the clean train split)
+ winner refit on clean split = 1
+ winner refit on version     = 1
= 27 trainings per call   (the 60 hidden CV fits are skipped)
```

Compared with your `10 × 3 + 1 = 31`, REIN uses:
- 5 settings instead of 10;
- 5 folds instead of 3;
- **two** final fits instead of one;
- a search on clean data, not on the version;
- a new search in every call.

Turning tuning on makes REIN train **less** (27 < 62).

**4. Clustering: 6 per call**, tuned or not.
```
2 fits (thrown away) + 4 fit_predict (one per scenario) = 6, all rows, no split
```

**5. Per data version and model (10 runs).**

```
10 calls = 20 result trainings
tuning off: 10 × 62 = 620    tuning on: 10 × 27 = 270    clustering: 10 × 6 = 60
early stop (7 calls, 6 stored): 434 / 189 / 42
```

**6. Per data version, all models of the task (10 runs).**

```
classification (12 models)  off: 12 × 620 = 7,440
                            on:  10 tunable × 27 + 2 untunable (GNB, MNB) × 62 = 394 per run × 10 = 3,940
regression (11 models)      off: 11 × 620 = 6,820
                            on:  7 × 27 + 4 × 62 = 437 per run × 10 = 4,370
clustering (6 models)       6 × 60 = 360
```

With `run_all_models` (+2 AutoML), tuning off gives 8,680 (C) and 8,060 (R). In those, each AutoML "fit" is itself a full search, 180 s for auto-sklearn. With tuning on, AutoML adds 0 fits, because of the KeyError.

**7. Per dataset.**

```
calls             = (ε+1) × h × 10
result trainings  = 2 × calls
example (Fig. 7b, Beers MLP): 18 versions × 1 model × 10 = 180 calls = 360 result trainings
example (code maximum, beers): 205 versions × 14 models × 10 = 28,700 calls
                               = 57,400 result trainings = 1,779,400 fits off / 807,700 on
```

**8. The whole paper.** The paper states no total. Two derived readings:

```
(a) What Figure 7 shows: 3,223 (version, model) pairs
    × 10 runs                         = 32,230 calls
    × 2                               = 64,460 result trainings
    clf/reg 2,593 pairs × 620 + clustering 630 pairs × 60
                                      = 1,645,460 fits if untuned
    (about 0.74 M if every clf/reg model shown had been tuned: 2,593 × 270 + 37,800)

(b) Code maximum (default dictionaries, all 14 datasets, run_all_models):
    C 983 × 14 × 10 + R 1,443 × 13 × 10 + UC 605 × 6 × 10
                                      = 137,620 + 187,590 + 36,300 = 361,510 calls
    × 2                               = 723,020 result trainings
    325,210 × 62 + 36,300 × 6         = 20,380,820 fits, tuning off
    983 × 3,940 + 1,443 × 4,370 + 605 × 360
                                      = 10,396,730 fits, tuning on
```

Reading (b) is an upper bound the authors clearly did not run; reading (a) is the closest to what they report.

**9. Trainings the formula does not count** (all in the repair phase, each repeated 10× with only the last run kept):
- **missForest:** up to 10 rounds of one random forest per column with NaN.
- **DataWig:** one neural model per column, up to 100 epochs.
- **Baran:** labels 20 tuples **from the ground truth** and trains AdaBoost (100 trees) per error column.
- **HoloClean:** one model (10 epochs).
- **BoostClean / CPClean:** each has its own `seed(1)` split (60/20/20) and KNN with k = 3. They build 3–10 candidate repairs, each fitting an imputer plus a KNN.
- **ActiveClean:** an SGD model plus one error classifier per 50-row batch.
- **cleanlab:** 5-fold CV + 1 fit per scenario.

---

## 5. Things that silently change the downstream numbers

1. **Cleaning before the split.** Repairs are fit on all rows, label included. mlImputer uses the label as an input to impute the other columns.
2. **Labels are repaired like any cell.** Mean imputation writes 2.6981 into breast_cancer's class column (classes 2/4). This creates a third class or, if every class cell is flagged, a constant label; a constant label drops the version.
3. **dropna on every row with a NaN** removes up to 45 % of rows (beers). Any repair that leaves a blank deletes that row.
4. **Delete shrinks the test set.** Flagged rows leave the test split too, so S1 is scored only on rows the detector judged clean, and the clean and version splits no longer hold the same rows.
5. **S2/S3 = 0** whenever the version has a stray string in a numeric column (dirty nasa, dirty breast_cancer).
6. **LabelEncoder refit per array.** Train and test class codes can disagree.
7. **Metric details:**
   - F1 is binary (positive = the larger label code) unless the **version's** test labels have more than 2 classes; then micro-F1 (= accuracy) is used, also for S4.
   - Regression values are stored as `rmse, mae, r2` under the header `rmse, r2, mae`.
8. **Leaky features are not excluded:**
   - bike: `cnt = casual + registered` in every row (linear regression S4: RMSE 0, R² 1);
   - beers: `brewery_id` maps 1:1 to the label;
   - HAR: the label `gt` is used as a clustering feature;
   - breast_cancer: the row index and ID are used as features.
9. **Models that silently produce nothing** (each fails, the version loop breaks, and no row is written):
   - MultinomialNB on any standard-scaled feature;
   - GaussianNB on sparse one-hot output;
   - GMM, AutoML and clustering when tuning is on.
10. **ML-oriented cleaners (Fig. 6):**
    - in `b389550` their results are **never stored**: `store_results` is called without `ml_task`, and the TypeError is swallowed (`benchmark.py:823`, `:828-831`);
    - they return [p, r, f1] under an f1, p, r header;
    - ActiveClean's S2, S3 and S5 are hard-coded 0.
11. **Logging.** Seeds, the hidden-CV MAE and Optuna's winners go only to logs or stdout. The results CSV has no run index, and re-runs append to it.

---

## 6. Paper vs. code: the published code did not make the published figures

- **Beers:** with the published `models.py`, the per-array LabelEncoder garbles the 551 class codes. Measured: RF gets micro-F1 0.000–0.004 in S1–S4, on clean and on dirty data. Fig. 7a/7b report S4 ≈ 0.58–0.73.
- **One S4 per model:** in every scatter, all points of a model share one S4 value, and the radar S4 rings are perfect circles. The code recomputes S4 in every call on a new random split, so the figures used a pooled or single S4.
- **Versions the shipped code cannot create:** KATARA versions on Adult, Smart Factory and Nasa; N/O/V detectors on Power, which match the *commented-out* error types; Impute on Citation.
- **GaussianNB on Beers** (109 versions in Fig. 7a) fails on sparse input with the shipped code.
- **Fig. 6** (ActiveClean, BoostClean, CPClean) cannot come from `b389550`, which never stores those results.
- **Smaller mismatches:**
  - "Bayesian" Optuna is actually 5 random trials;
  - "different random seeds" are unrecorded entropy seeds;
  - "silhouette to find k" is a commented-out plot;
  - the paper's prose says "S3 and S4" where its Table 3 implies S3 and S2;
  - p.5 says p ≥ α "supports Ha", which is inverted.

**Conclusion:** the paper's downstream results were produced with an unpublished code or dictionary state. The protocol can be reconstructed from the code. The exact runs behind the figures cannot.

---

## 7. What cannot be known from paper and code

- whether classification and regression were tuned in the paper runs;
- whether early termination was on (7 or 10 runs);
- ε per dataset as run;
- the seeds;
- how S4 was pooled for the figures;
- why Bikes, 3D Printer and Mercedes have no downstream results;
- the AutoML budgets used.

---

## 8. Relation to your Block D numbers

| | REIN | your plan |
|---|---|---|
| Search | 5 random settings × 5 folds on **clean** data + 2 refits = 27, redone in every call | 10 settings × 3 folds on the version + 1 refit = 31, if you tuned |
| Default path | 62 trainings per call (60 hidden CV fits) | 1 training per (version, model, split) |
| Splits | unpaired (new entropy seed per version and run) | 10 paired seeds, one split shared by all versions |
| Clean reference | retrained in every call | trained once per split (S4 reference) |
