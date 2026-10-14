# Block D final plan: downstream impact (RQ3), version 2.1

**Date:** 9 Oct 2026.

**What it replaces:**
- the Block D plan doc (5 Oct);
- the driver spec (6 Oct, `reports/block_d_driver_spec_2026-10-06.md`).

**What it applies:**
- the eight fixes and eleven corrections of the pre-run review (`reports/block_d_plan_review_2026-10-09.md`);
- the independent check by Fable 5.1 (`reports/block_d_final_plan_2026-10-09/fable/fable_review.md`, verdict "ready after fixes"). Section 15 lists how each of its findings was handled.

**Where the numbers come from:**
- `reports/block_d_final_plan_2026-10-09/checks/`, run in the rein container (pandas 1.3.3, scikit-learn 0.24.2, SciPy 1.7.1), read-only on `rein-datasets/`.
- Fable re-derived every table with its own code, including the real GE library and its own HoloClean violation rule.
- The GE and HoloClean flag sets reproduce Table 3 exactly on all four datasets. On bc, nasa and bike they are also cell-identical to the files on disk. Nothing on adult is cell-verified: its GE file is empty and its HoloClean file is stale.
- **Raha numbers come from the `detections.csv` on disk, not run 1.** The disk counts are 407 / 2,595 / 46,001 / 5,514 against Table 3's 395 / 2,574 / 45,999 / 5,946. Step 2 regenerates run 1, and `--dry_run` reprints every Raha figure, the degenerate list and the expected pair verdicts. The prediction itself was frozen on 9 Oct (`c61ee72`); the run-1 verdicts are committed beside it as an addendum (§12).

---

## 0. What changed and why: the eight fixes with their measured effect

| # | Fix | Where | Before (v1) | After (v2.1) | Measured on the real data |
|---|---|---|---|---|---|
| 1 | Every policy and the random control use **only flags in model columns** (features + label) | spec §5, §6; plan "Cleaning strategies" | a flag in an identifier or leak column deletes the row | excluded-column flags are ignored and reported as `excl_col_flags` | Training rows kept under delete (per-seed range, all-column → model-column flags): bc GE hand-written 253–270 → **307–322**; bc perfect 195–208 → 234–250; bike Raha 374–401 → **921–976**; bike GE hand-written 3,044–3,106 → 3,574–3,649. On bc all 22 hand-written FPs are in the row-number column; under v1 each deleted a correct row. |
| 2 | Report **format-only false positives** separately | spec §8; plan risk table | "the model-visible ranking explains it" | `format_only_fp` (model columns) and `rows_touched_without_format_only` | **Definition:** a flagged model cell that the ground truth calls correct (equal within relative 10⁻⁶) but whose text differs, e.g. `800` vs `800.0`. Counts: nasa Raha **1,864 of 1,864 FPs** (frequency 1,365, angle 499); nasa HoloClean 500 (angle 499, target 1); bike Raha **2,330 of 3,636** model-column FPs (windspeed 2,049, hum 279, temp 1, atemp 1; the all-column 13,261 is mostly the excluded `dteday`); bc, adult 0. Raha flags **all 1,503 nasa frequency cells**: under delete every row goes (731 without these flags), and under impute the column becomes constant. On bike they cost 247 rows under delete. The model-visible truth equals the full truth on nasa (731 = 731), so that ranking changes nothing here. |
| 3 | **Merge identical flag sets** into one item | spec §10; plan "From scores to the answer" | 5 items on every dataset | items = distinct model-column flag sets: bc 5, nasa 5, **bike 4**, **adult 3** | Identical: bike GE dirty = clean-profiled (both empty); adult all three GE tiers (empty). Type I error of the pooled permutation test at nominal 0.05: **0.12–0.18 unmerged, 0.037–0.041 merged** (Fable, 4,000 replications, three nulls; the review had 0.116 → 0.037). No reference ties remain, which resolves open decision 1. |
| 4 | Give the **random-deletion control** a test | spec §10 | built, never analysed | paired test delete(c) vs control(c), §8.6 | Control = floor when k = 0; degenerate when c is degenerate (§5). |
| 5 | **Exact sign-flip test on midranks** instead of SciPy's exact Wilcoxon | spec §10; plan "Protocol: Ties" | `wilcoxon(nz, mode='exact')` | §8.2 | SciPy 1.7.1 truncates its statistic with `int(r_plus)`. Example: d = [4, 2, 4, 1, 3, 4, −3, 2, 1, −1] gives p(d) = 0.0645 but p(−d) = 0.0488, so **the verdict flips with the order of the pair**. In 1,538 random tied vectors, 649 differ and 34 verdicts flip (Fable). The sign-flip p is 0.0586 in both orders. |
| 6 | Under impute, **a flagged label costs the whole row** | plan policy table | "a correct value is overwritten" | "…or the whole row, if the flag is on the label" | Rows kept under impute: nasa HoloClean (934 target flags, all FPs) **444–465 of 1,202**; bike HoloClean (17,366 `cnt` flags) **7–13**, degenerate; bc HoloClean (all 699 `class` cells) 0. |
| 7 | **Complete the degenerate list** | spec §12; plan risk table | bc HoloClean, nasa Raha, bike HoloClean (delete) | §5, printed by `--dry_run`, committed with the prediction | Under delete, HoloClean is degenerate **on all four datasets**: nasa 26–34 rows; adult 0, because its 665,207 flags touch all 45,222 rows. bike HoloClean is also degenerate under impute (7–13). adult HoloClean under impute is near-degenerate: 1,102–1,153 rows, 144–164 of them minority class, and 81 % of their feature cells flagged. Spec §12's "delete = impute on adult" and "about 1.4k rows remain" hold for Raha and perfect, not for HoloClean. |
| 8 | **Impute can only gain on parsable errors**, and some impute versions equal the floor | prediction; spec §4 | not stated | §4 rule; hashing on rounded values | Unparsable feature errors are mean-filled by featurization in every version: bc 217 of 509, nasa 382 of 731, bike 0. **Same as the floor:** bc GE clean-profiled (byte-identical); bc GE dirty-profiled and nasa GE dirty-profiled (identical up to rounding of the fill mean, ≤ 6·10⁻¹⁰; scores identical). **Not the floor:** nasa GE clean-profiled. Its 2 parsable TPs are the thickness typos 2.25·10¹¹ and 2.21·10¹¹, which move the fill mean (full-column mean 3.17·10⁸ vs clean 0.011; medians 0.0052 / 0.0050). That changes 191–268 training cells per seed and XGB's S2 by up to 0.14 RMSE. nasa has **223 parsable typos more than 10 clean ranges outside the clean range**: hand-written and Raha flag all, HoloClean 185, clean-profiled 2, dirty-profiled 0. These cells largely decide nasa under impute and ground-truth repair. |

**Small additions:**
- `label_errors_left`: adult under impute keeps 657–685 flipped labels for Raha, 16–21 for HoloClean and 0 for perfect.
- `errors_left_in_features` compares parsed values before the mean fill. Otherwise bc's `?` cells, which are `?` in clean.csv too, count as errors.
- `parsable_tp` and `parsable_fp` columns.
- A fourth check (§7).
- Training is skipped when the rounded `train_hash` repeats.

**Primary reference: not restricted to model columns.**
- The review suggested restricting the Table 3/7 references to model columns. On bike that reverses hand-written GE and Raha: all columns 0.829 > 0.783, model columns Raha 0.913 > hand-written 0.825. 3,537 of bike's 34,274 errors, 2,648 of hand-written's flags and 13,513 of Raha's sit in columns the model never sees.
- RQ3 asks whether the *published* ranking survives, so Table 3 as published stays the primary reference (a).
- The bike hand-written/Raha pair is reported under (a) and (c) side by side. A discordance under (a) alone is labelled an excluded-column artefact, not a downstream finding. bc's analogue is harmless: the orders agree.

---

## 1. Research question and what counts as an answer

**RQ3:** Does the ranking by detection quality survive downstream model training, and how far does that depend on the repair policy that turns detections into training data?

- **When the ranking survives:** the items come out in the same order on S2 as on detection quality, counted pair by pair (concordant, discordant, tied).
- **Main result:** the share of concordant pairs per policy, pooled over datasets and models.
  - Denominator: all pairs, ties included.
  - Concordance among decided pairs is reported beside it.
- **The misalignment** the proposal's success criterion asks for is any discordant pair. It is shown pair by pair, descriptively.

## 2. Datasets and model columns

The four datasets and the four selection criteria are unchanged.
- **Core:** breast_cancer, nasa.
- **Extension:** bike, adult, after gate 1.

| Dataset | Task, label | n | n_train | Model columns | Excluded (never model input, never acted on) |
|---|---|---|---|---|---|
| breast_cancer | classification, `class` (1 = malignant, `4`) | 699 | 559 | 9 attributes + `class` | `Unnamed: 0` (row number), `Sample code number`: 107 of 631 errors |
| nasa | regression, `sound_pressure_level` | 1,503 | 1,202 | 5 + label | none |
| bike | regression, `cnt` | 17,379 | 13,903 | 12 + label | `instant`, `dteday`, `casual`, `registered` (sum to `cnt`): 3,537 of 34,274 errors |
| adult | classification, `income` (1 = >50K, `0`) | 45,222 | 36,177 | 14 + label | none |

- **Column types:** numeric if at least 90 % of the clean values parse. bc `Bare Nuclei` has 16 `?` in clean.csv. Otherwise categorical: the eight adult string columns.
- **Featurization,** fitted on the kept training rows of each version:
  - numeric: coerce, then fill NaN with the training mean (D5);
  - linear model only: `StandardScaler`;
  - categorical: `OneHotEncoder(handle_unknown='ignore')`;
  - dense output.
- An unflagged label that does not parse means abort.

## 3. Flag sets and items

**Flag sets (7 per dataset):**
- GE dirty-profiled, GE clean-profiled, GE hand-written, HoloClean, Raha run 1;
- `perfect` (= `actual_errors.csv`);
- `always_positive` (every cell).

**Restriction:** each set is restricted to the model columns before any use. Excluded-column flags are counted, not applied.

**Diagnostic version (D6 safeguard, triggered 11 Oct):** nasa `raha_minus_format_only` = Raha run 1 without its 1,864 format-only FPs (710 of 731 TPs, 0 FPs; the 21 misses are `thickness` typos). Trained under all three policies, reported beside the ranking, never ranked or counted in a pair.

**Items:**
- Configurations with identical restricted sets form one item (e.g. `GE profiled (dirty = clean)`), computed from the frozen files.
- Measured today: bike {dirty, clean}, adult {dirty, clean, hand-written}.
- Items and pairs: bc 5 / 10, nasa 5 / 10, bike 4 / 6, adult 3 / 3.

## 4. Repair policies (training split only; the S2 test set is never touched)

| Policy | What it does | Cost of a false flag | Order expected from the flags (mechanism, §8.3 d) |
|---|---|---|---|
| Ground-truth repair | clean value into each flagged model cell | nothing | recall on model-visible errors |
| Delete | drops each training row with ≥ 1 flagged model cell | a clean row | row precision: share of flagged rows that hold a model-visible error; degenerate last |
| Mean/mode impute | flagged numeric feature cell → mean of the unflagged parsable cells of the kept rows; flagged categorical cell → their mode | a correct value overwritten (a fully flagged column becomes constant); **a flagged label costs the row** (labels are never imputed) | net parsable repairs = parsable TPs fixed − parsable FPs overwritten, label rows as in delete; degenerate last |

**Rules:**
- Statistics never come from the ground truth or the test rows.
- A column with no unflagged training value becomes constant (0.0 or `"__none__"`).
- **Floor equivalence under impute.** A version equals the floor up to rounding of the fill mean when **every** flagged model cell, TP and FP alike, is unparsable and no label is flagged. Measured: bc GE dirty- and clean-profiled, nasa GE dirty-profiled. **nasa GE clean-profiled is not floor-equivalent** (fix 8).
- **Random control.** For configuration *c* in seed *s*:
  - *k* = training rows that *c* deletes (model-column flags);
  - delete *k* random training rows with `np.random.default_rng([s, c_idx])`;
  - scored in S2 only;
  - = floor when *k* = 0; degenerate when *c* is.

## 5. Expected versions: rows kept per seed and degenerate cases (measured)

How to read the table:
- Training rows kept, min–max over 10 seeds, model-column flags.
- **D** = degenerate (fewer than 50 rows or one class; no model trained).
- **≈ floor** = equal to the floor up to rounding of the fill mean (scores identical).
- Ground-truth repair keeps all rows everywhere.

| Configuration | bc delete | bc impute | nasa delete | nasa impute | bike delete | bike impute | adult delete | adult impute |
|---|---|---|---|---|---|---|---|---|
| GE dirty-profiled | 376–392 | ≈ floor | 1,174–1,183 | ≈ floor | = floor¹ | = floor¹ | = floor² | = floor² |
| GE clean-profiled | 372–390 | = floor (byte-identical) | 884–900 | 1,202, **not floor** (2 thickness typos move the fill mean) | ¹ | ¹ | ² | ² |
| GE hand-written | 307–322 | 559 | 647–672 | 1,202 | 3,574–3,649 | 13,903 | ² | ² |
| HoloClean | **0 D** | **0 D** | **26–34 D** | 444–465 | **0 D** | **7–13 D** | **0 D** | 1,102–1,153, near-degenerate³ |
| Raha (disk file) | 325–342 | 559 | **0 D** | 1,202 (frequency column constant) | 921–976 | 13,903 | 31,733–31,796 | 31,733–31,796 |
| perfect | 234–250 | 544–549 | 605–631 | 1,202 | 915–983 | 13,903 | 34,806–34,838 | 34,806–34,838 |
| always-positive | 0 D | 0 D | 0 D | 0 D | 0 D | 0 D | 0 D | 0 D |

¹ bike GE dirty = clean-profiled, both empty: one item. ² adult: all three GE tiers empty, one item. ³ 144–164 minority rows; 81 % of their feature cells flagged.

**Items left once degenerate versions are removed:**

| Dataset | Under delete | Under impute |
|---|---|---|
| bc | 4 | 4 |
| nasa | 3 | 5 |
| bike | 3 | 3 |
| adult | 2 | 3 |

## 6. Split, models, scenarios, scores (unchanged from spec §6–7)

- **Split:**
  - `train_test_split(arange(n), test_size=0.2, random_state=seed)`, seeds 0–9;
  - stratified by the **clean** class labels for classification;
  - shared by all versions; rows in row-id order.
- **Models:**
  - linear (`LogisticRegression(max_iter=5000)` / `Ridge()`), random forest, XGBoost 1.3.3;
  - defaults, `random_state=0`, `n_jobs=1`;
  - no tuning, justified by the 6 Oct pilot;
  - dense input.
- **Scenarios:**
  - S1 = version model on version test rows (appendix);
  - **S2 = version model on the full clean test split (ranks)**;
  - S3 = clean model on version test rows (appendix);
  - S4 = clean model on the clean test split (ceiling);
  - floor = dirty as shipped, scored like S2.
- **Scores:**
  - classification: minority-class F1, plus precision and recall;
  - regression: RMSE (oriented as −RMSE) and R²;
  - share of gap closed = (S2 − floor)/(S4 − floor), only where S4 beats the floor by the pair rule.

## 7. Checks (any failure aborts)

1. **Flags match Table 3:**
   - TP/FP/detections from the frozen files equal Table 3, with no duplicate or out-of-range cell.
   - On bc, nasa and bike the GE and HoloClean files must also be cell-identical to the replay (`checks/measure_fixes.py`).
   - On adult too (D8): the regenerated HoloClean file must be cell-identical to the replay. The benchmark passes HoloClean a DataFrame, so no string normalisation happens, and normalising would change no flag on adult anyway (`checks/decisions/d8_adult_holoclean.py`).
2. **Perfect + ground-truth repair = S4:**
   - the same rounded `train_hash` and S2 = S4 for every seed and model;
   - the same for always-positive.
   - The review measured a pass on 10/10 seeds on all four datasets.
3. **An empty flag set gives the floor** under every policy.
4. **A non-empty flag set does what the policy says:**
   - perfect + delete keeps exactly n_train minus the training rows with a model-column error;
   - perfect + impute changes exactly the flagged parsable feature cells and drops exactly the rows with a flagged label.

**Hashing:**
- `train_hash` = sha256 of the float feature matrix rounded to 12 significant digits, plus the label, excluded columns dropped.
- Without rounding, the floor-equivalent versions of §4 never share a hash with the floor.

## 8. Analysis

1. **Mean S2** per dataset × policy × model × item over 10 seeds, with degenerate counts.
2. **Pair verdict** per pair of items, on the 10 oriented per-seed differences d:
   - same rounded hash on all seeds → tie;
   - set |dᵢ| < 10⁻⁹ to 0 and drop zeros; ≤ 5 non-zero → tie;
   - otherwise the **exact sign-flip test on midranks**:
     - T = Σ sign(dᵢ)·rank(|dᵢ|), with midranks for tied |d|;
     - p = share of the 2ⁿ sign patterns s with |Σ sᵢ·rank(|dᵢ|)| ≥ |T|;
     - p < 0.05 → direction, else tie.
   - The test is invariant to the order of the pair.
   - **Caveat:** two 80 % training sets share about 64 % of their rows, so the 10 differences are not independent and the p-value is anti-conservative (Dietterich 1998; Nadeau & Bengio 2003). The pair verdict is a classification device, not a hypothesis test.
3. **References:**
   - **(a) primary:** Table 3 cell F1, all columns, as published.
   - **(b)** Table 7 row F1, rebuilt from the frozen flags.
   - **(c)** model-visible cell F1: model columns, truth = errors whose parsed value changes. On these datasets (c) equals model-column F1.
   - **(d) mechanism reference** per policy (§4): GT repair recall / delete row precision / impute net parsable repairs, computed from the frozen flags. It is used only to score the prediction.
   - Measured orders, Raha from the disk file:
     - bc and nasa: (a) = (c);
     - bike: (a) hand-written > Raha, (c) Raha > hand-written (excluded-column artefact);
     - (b) moves HoloClean up on bc and bike.
4. **Concordance and the primary test:**
   - **Primary test, one per policy (3 tests, Holm-corrected):** pooled number of concordant pairs against reference (a), degenerates ranked last, over datasets × models.
   - One-sided exact permutation test for "more concordant than chance". Reference scores are permuted among items within each dataset: bc and nasa 5! = 120, bike 4! = 24, adult 3! = 6 permutations. One permutation is shared by the models of a dataset, and the per-dataset distributions are convolved.
   - The "left out" variant has items bc 4 / nasa 3 / bike 3 / adult 2 under delete (24 / 6 / 6 / 2 permutations; type I error 0.025–0.036, low power).
   - **Everything else is descriptive:** references (b)–(d), the left-out variant, the pair verdicts and the control tests.
   - "Mostly discordant" cannot be certified by this one-sided test. Discordant pairs are reported individually.
5. **Kendall τ-b** per dataset × policy × model: descriptive.
6. **Random control:** for every dataset × model × configuration with 0 < k < n_train, compare delete(c) with control(c) by rule 8.2.
   - Report "detector better / tie / worse than random deletion of the same number of rows".
   - A tie does not mean "wrong rows" where the removed errors are harmless to the model (bc tree models): read ties together with the ground-truth-repair result.
   - The control does not preserve the class balance of the deleted rows (bc, adult). Note this when reading it.
7. **Degenerate versions:** analysis run twice, ranked last and left out.
8. **Median sensitivity (D5):** the whole run repeated with the median as fill statistic (featurization and impute). Reported descriptively: the number of pair verdicts that change, and concordance with (a) under both fills. Decision runs on 9 Oct (`checks/decisions/d5_*`) changed 22 of 144 verdicts and found two marker effects of the mean: nasa unparsable cells (help trees), bike `holiday` (misleads trees). Both go into threats to validity.

## 9. Prediction (committed to git before the first run, with `expected_pair_verdicts.csv`)

The prediction is stated against what §8 scores.

> **Disclosure (9 Oct).** This section was written before any model was trained. The design-decision runs for D2–D5 (`checks/decisions/`) then trained the core datasets with a minimal driver, which shows parts of the result. This section was frozen unchanged in git right after those runs, and it is not edited after them.

**How the expected verdicts were derived:**
- The expected verdict of every pair, dataset × policy, comes from the mechanism (d) applied to the frozen flags and compared with reference (a). The file is `checks/expected_pair_verdicts.csv`; recompute it after step 2 for Raha run 1.
- **Undetermined pairs:** a pair is undetermined when one item equals the floor or both have the same mechanism score. Training decides those.

**Expected pairs against the primary reference (a), pooled over the four datasets (29 pairs per model):**

| Policy | Concordant | Discordant | Undetermined | Concordant among decided |
|---|---|---|---|---|
| Ground-truth repair | 19 | 10 | 0 | **0.66** |
| Delete | 16 | 4 | 9 | 0.80 |
| Impute | 12 | 1 | 16 | 0.92 |

**Predictions** (each can be refuted by `results.csv`):

1. **The ranking survives worst under ground-truth repair, where false flags cost nothing.**
   - The 10 expected discordant pairs:
     - bc: HoloClean above all four others;
     - nasa: Raha above hand-written and clean-profiled, HoloClean above clean-profiled;
     - bike: Raha and HoloClean above hand-written;
     - adult: HoloClean above Raha.
   - All follow from recall exceeding the Table 3 order.
   - Refuted if, among decided pairs, the concordant share under ground-truth repair is not the lowest of the three policies.
2. **Delete and impute agree with Table 3 more, because Table 3's F1 punishes false flags as these policies do.**
   - Expected discordant pairs:
     - under delete: bc Raha below both profiled GE tiers; nasa dirty-profiled above the degenerate HoloClean and Raha;
     - under impute: bike Raha above hand-written.
   - Refuted if fewer than 70 % of the decided pairs under delete or under impute are concordant with (a).
3. **The mechanism holds.** Against reference (d), at least 70 % of the decided pairs are concordant under each policy.
4. **Many ties under impute.** Most undetermined impute pairs (16 of 29) end tied, because floor-equivalent items cannot differ from the floor.
5. **Task type:** the share of tied pairs is higher on classification (bc, adult) than on regression (nasa, bike); tree models on bc mostly tie.
6. **nasa:** under ground-truth repair and impute the order is set by the 223 far-out parsable typos.
   - Hand-written and Raha fix all of them, so they come first.
   - Raha's impute version loses its constant frequency column and drops below hand-written.
   - RF stays near the floor even for the perfect detector under impute (review: 2.260 vs floor 2.262, S4 1.771).
7. **Random control:** on nasa and bike, every non-degenerate configuration with row precision ≥ 0.98 under delete beats random deletion of the same number of rows for at least two of the three models.
8. **bike:** the hand-written/Raha pair is discordant with (a) under ground-truth repair and impute, and concordant with (c).

**Not predictions:** these facts are fixed by the flags and the checks, and are listed in §5 and §7:
- which versions are degenerate;
- which versions equal the floor;
- that perfect/always-positive + ground-truth repair reach S4.

## 10. Corrected statements about REIN (replace in the plan doc)

| # | Plan sentence now | Replace with |
|---|---|---|
| 1 | "Its default run does not tune at all (`hyperopt=False`)." | "REIN's paper says it tuned with Optuna. The code's default is off, but the README command (`--hyperopt False`) turns tuning on (`scripts/train_model.py:26`, `type=bool`), so which mode made the figures cannot be decided." |
| 2 | "REIN's training code is not used, because it misaligns the splits, is unseeded, writes S2 silently as 0 and imputes the label" | "REIN's training code is not used. It misaligns the splits (its `dropna` keeps 452/699 bc and 1,473/1,503 nasa rows), uses unrecorded entropy seeds, stores S2 as 0, encodes labels per array (beers F1 0.000–0.004, from the 7 Oct report), and scores binary F1 on the larger code. Label imputation happens in REIN's repair code (`cleaners.py` `standardImputer`)." |
| 3 | "In REIN's code, S2 equals S4 for clustering, because `fit_predict` refits…" | "…S2 repeats the S4 procedure for clustering, so it equals S4 only up to random initialisation." |
| 4 | "REIN trains models on three of them (Fig. 7)" | **Keep**, sharpened: "REIN trains models on three of them (Fig. 7c–f Adult and Breast Cancer, 7j–k Nasa). REIN's Adult is not the local one: error rate 0.58 from rule violations and outliers (Table 4) against 1,701 label flips here. REIN shows S2 only for Soil Moisture (Fig. 7n–o)." |
| 5 | "They also react differently to the same errors (REIN Fig. 7c, 7j)" | "Cleaning effects depend on the model (CleanML, Li et al. 2021)." Grinsztajn et al. stays only for "tree ensembles are the strongest standard learners". |
| 6 | "REIN's other models: they mostly repeat what these three show." | "REIN's other models are left out for scope. REIN p. 10 reports that some behave differently: Adult DT 0.17–0.99 vs Ridge 0.74–0.78; Breast Cancer DT 0.65–0.94 vs GNB 0.15–0.85." |
| 7 | "Without this, SciPy 1.7 silently switches to an approximation…" | "SciPy's exact Wilcoxon depends on the order of the pair when \|d\| values tie (§8.2), so an exact sign-flip test on midranks is used." |
| 8 | "give the highest τ-b it allows: 0.95 on bike, 0.84 on adult" | delete (identical flag sets are merged, §3) |
| 9 | "No S5 … a dirty test set scores the predictions against wrong labels." | "No S5: REIN uses it for cleaners that output a model (p. 4: 'S5 is mainly used with ML-oriented repair methods'); its dirty test set carries wrong labels on bc (15 flips) and adult (1,701), none on nasa and bike." |
| 10 | "REIN uses the ground truth only as an upper bound" | "REIN frames the ground truth as an upper bound (p. 4), but also applies ground-truth repair per detector (Figs. 4c, 7m)." |
| 11 | "…which would mean 85,000–100,000 for Block D." | "…about 104,000 for Block D (3,240 × 31 + 120 × 31 = 104,160)." |
| — | "stratified by class for classification" | "stratified by the clean class labels" |

## 11. Outputs

**`results.csv`:** one row per dataset × version × policy × model × seed × scenario. Columns:

`dataset, task, version, item, configuration, policy, model, seed, scenario, score, f1|rmse, r2, precision, recall, rows_kept, test_rows, cells_changed, excl_col_flags, format_only_fp, rows_touched_without_format_only, parsable_tp, parsable_fp, errors_left_in_features (parsed values, before the mean fill), label_errors_left, flagged_label_cells, degenerate, test_degenerate, train_hash (rounded), fit_s, timestamp`

**`manifest.json`:** as in spec §8, plus the item map, the degenerate list and the hash of `expected_pair_verdicts.csv`.

**Run size:**
- 27 versions per dataset, at most 3,240 trainings + 120 S4.
- Training is skipped when the rounded hash repeats: GT-repair perfect/always-positive = S4; zero-flag items = floor; floor-equivalent impute versions.
- The median sensitivity run (§8.8) doubles this; on bike only impute differs, since every dirty bike value parses.

## 12. Schedule (re-dated; steps 0 and 2–4 have not started; step 1 done 9 Oct)

Gate 1 moves to **Mon 12 Oct, noon** (D7). Building the driver and the analysis script is about two days of work, not one (Fable S10).

| Day | Steps | Output |
|---|---|---|
| Fri 9 Oct | this plan, the Fable check, decisions D2–D8 (tested with `checks/decisions/mini_driver.py`); **1 prediction committed** (`c61ee72`) | final plan, frozen prediction |
| Sat 10 Oct | 0 backups; 2 core flags (regenerate GE profiled and Raha run 1; cross-check with the replay); start 3: the driver, built on `mini_driver.py` | frozen core flags |
| Sun 11 Oct | 3: finish the driver (incl. `--fill median`, D5, and the D6 run-1 check), and write the analysis script against a synthetic `results.csv`; `--dry_run`; recompute `expected_pair_verdicts.csv` for Raha run 1 (flags only, same script) and commit it **beside** the frozen file as an addendum | scripts, addendum |
| Mon 12 Oct | 4 checks; 5 core runs (~3 min); 6 core analysis → **gate 1 at noon**; afternoon: 7 extension flags (adult Raha ~10 min, ~18 GB, run alone) | core answer |
| Tue–Wed 13–14 Oct | 8 extension runs + analysis + verification | four-dataset result |
| Thu 15 Oct | 9 freeze: restore backups, commit, tag | frozen results |

**Riskiest steps:**
- the driver itself (Sat–Sun);
- the exact reproduction of Raha run 1: check 1 aborts on any mismatch, and it needs the warm cache (bc, nasa ≈ 2 s; bike ≈ 150 s; adult ≈ 600 s and 18 GB, run alone).

**Fallbacks:**
- core late at the gate → bike and adult dropped;
- core not done by 15 Oct → data-only table, named as a deviation.

## 13. Decisions (all made with the user on 9 Oct, each tested in `checks/decisions/`)

| # | Decision | Proposal | Alternative | Why it matters |
|---|---|---|---|---|
| D1 | Reference-tied pairs | **resolved by the merge** | — | no reference ties remain |
| D2 | Impute statistics over… | **decided 9 Oct: the kept training rows** | all training rows (pilot) | They differ only where label flags drop rows. Measured (`checks/decisions/d2_impute_stats.py`, 10 seeds × 3 models): nasa HoloClean identical, because the dropped rows have every feature flagged too; bc perfect F1 differs by ≤ 0.011 on 1 (RF) and 5 (XGB) of 10 seeds; adult HoloClean differs on every seed, by up to 0.25 F1 (linear), and its fill means come from 34 vs 91 unflagged ages. |
| D3 | Model seed | **decided 9 Oct: fixed `random_state=0`** | = split seed | Not "keeps model noise out": both items of a pair share the seed either way, and RF noise is in every score either way. Measured (`checks/decisions/d3_model_seed.py`): linear and XGB ignore `random_state`; RF noise alone is 0.05 RMSE on nasa and 0.02 F1 on bc (floor, split 0); 2 of 45 core RF pair verdicts change (bc delete GE-hand vs Raha, nasa delete GE-clean vs GE-hand), both near-ties going from tie to a direction. |
| D4 | Numeric-column rule | **decided 9 Oct: ≥ 90 % of clean values parse** | every value parses | Only bc `Bare Nuclei` differs (a 1–10 count; 16 `?` = UCI's missing marker); any threshold in (0, 0.977] gives the same split on all four datasets. Strict makes it an 18-level one-hot. Measured (`checks/decisions/d4_numeric_rule.py`): 13 of 66 bc pair verdicts change, all from a direction to tie, 10 of them linear; floor XGB F1 0.938 → 0.923. |
| D5 | Fill statistic (featurization and impute) | **decided 9 Oct: mean**, REIN's mean/mode; plus a median sensitivity run reported as verdict changes (§8.8) | median as primary, a stated deviation | The earlier reason ("the polluted mean is a real cost of missing typos") is wrong. Measured (`checks/decisions/d5_*`): the mean fills values that never occur, and trees split on them as a marker. nasa: the polluted mean (thickness 4·10⁸) marks unparsable cells, which *helps* trees (floor RF 2.26 vs median 2.40 RMSE; a fill of 10¹² does the same). bike: impute fills `holiday` (0/1, flagged in 43 % of rows) with 0.048; the injector chose those rows non-randomly (mean cnt 162 vs 210), so the marker misleads trees (perfect impute RF 70 vs 51 RMSE; `holiday` alone explains it). Verdicts that change mean → median: nasa 8 of 69, bc 11 of 66, bike 3 of 9 (impute; the other bike policies are identical by construction); concordance with Table 3 about the same either way. |
| D6 | Format-only sensitivity version | **decided 9 Oct: count only** (`format_only_fp`, `rows_touched_without_format_only`), with the run-1 safeguard | run "Raha minus format-only FPs" | Measured (`checks/decisions/d6_format_only.py`, Raha disk file): nasa Raha minus its 1,864 format-only FPs **is** the perfect detector, so the perfect row already shows it (delete: 0 rows vs 605–631; impute RF RMSE 6.55 vs 2.26; GT repair identical). bike: removing the 2,330 format-only FPs keeps ~190 more training rows under delete, but S2 does not move (RF/XGB tie under every policy; linear differs by ≤ 2 RMSE in either direction). bc, adult: none. After step 2, `--dry_run` checks whether Raha run 1 minus format-only FPs still equals perfect on nasa (run 1: 710 of 731 TPs); if not, add it as one unranked diagnostic version on nasa. |
| D7 | Gate 1 | **decided 9 Oct: Mon 12 Oct, noon** | Sun 11 Oct evening (the 5 Oct date) | Compute is not the bottleneck (`checks/decisions/d7_fit_times.py`, one version × 3 models, n_jobs=1): bc and nasa 0.2 s, bike 4.2 s, adult 11 s. Whole runs including the median re-run: core under 2 min, bike ~15 min, adult ~20 min (+ adult Raha flags ~10 min, 18 GB, alone). The work is building and checking the driver and the analysis script. Already done on 9 Oct: the prediction commit (step 1, `c61ee72`) and a tested minimal driver (`checks/decisions/mini_driver.py`: versions, featurization, models, S2, pair rule) to build on. Mon noon still leaves 2.5 days for the extension, which needs under 1 h of compute. |
| D8 | Check 1 on adult HoloClean | **decided 9 Oct: cell identity required, as on the other datasets** (the earlier proposal was count identity) | count identity suffices | The earlier reason is wrong. HoloClean strips and lower-cases only when it reads a file (`cleaners/holoclean/dataset/table.py:58`); the benchmark passes a DataFrame (`rein/detectors.py:1148`), which is used unchanged. Even with normalisation nothing changes on adult: strip + lower alters every text cell but merges no two values, so the replay is cell-identical (`checks/decisions/d8_adult_holoclean.py`). No missing values (no SQL NULLs). The replay equals Table 3 (1,677 / 663,530 / 665,207). The disk file (17 Sep) is a strict subset with 341,890 cells (0 cells only on disk), so it is stale and must be regenerated in step 7. |

## 14. Evidence

- `checks/measure_fixes.py`, `measure_fixes_output.txt` and `measure_fixes.json`: replay check, per-configuration counts, rows kept per seed, degenerate list, Wilcoxon examples.
- `checks/reference_rankings.py` and `reference_rankings_output.txt`: reference orders (a)–(c).
- `checks/implied_predictions.py`, `implied_predictions_output.txt` and `expected_pair_verdicts.csv`: mechanism (d) and the expected verdict of every pair.
- `checks/decisions/`: the runs behind decisions D2–D8 (`mini_driver.py` plus one script and output per decision).
- `fable/fable_review.md` and its scripts: independent recomputation, impute-vs-floor magnitudes, giant typos, type I error simulation, Wilcoxon order study.
- `reports/block_d_plan_review_2026-10-09.md`: the review; gate 2 was measured there.
- Superseded: `reports/block_d_driver_spec_2026-10-06.md` and the 5 Oct plan doc (https://claude.ai/code/artifact/9a435b72-1b69-4930-8af7-5a5865b86a8e).

## 15. Fable review log

| Finding | Action |
|---|---|
| B1 prediction not scored by §8; old prediction 7 contradicted | **Accepted.** §9 is rewritten against (a). The new reference (d) and `expected_pair_verdicts.csv` cover it. Old prediction 7 is reversed: ground-truth repair is now expected to survive *worst*. Flag-determined facts moved out of §9. |
| M1 "= floor" wrong for nasa clean-profiled; hashes fragile | **Accepted.** Corrected in §0, §4 and §5; rounded hash; \|d\| < 10⁻⁹ = 0; complete floor rule; giant-typo mechanism added to §9.6. |
| M2 S5 replacement wrong | **Accepted.** §10 item 9. |
| M3 item 4 replacement wrong | **Accepted.** The original is kept and sharpened. |
| M4 bike format-only count, definition | **Accepted.** Model-column counts and a precise definition; D6 changed to "count only". |
| M5 multiplicity, dependence, tail | **Accepted.** §8.4 names 3 primary tests (Holm); the rest is descriptive; dependence caveat in §8.2. |
| S1 impute mechanism = parsable TPs − parsable FPs | **Accepted with one correction.** Fable says nasa Raha's format-only FPs cost nothing under impute. They do: Raha flags all 1,503 frequency cells, so the column becomes constant. Format-only FPs therefore count as losses in (d). |
| S2 misreported JSON | **Accepted.** 657–685 / 16–21. |
| S3 adult HoloClean near-degenerate | **Accepted.** §0, §5. |
| S4 bike reversal is an excluded-column artefact | **Accepted.** §0, §8.3, §9.8. |
| S5 control caveats | **Accepted.** §8.6. |
| S6, S7 citations | **Accepted.** §10 items 5, 6. |
| S8 adult cell identity | **Accepted** as decision D8. |
| S9 left-out permutation counts | **Accepted.** §8.4. |
| S10 schedule | **Accepted.** Gate 1 moved to Mon noon (D7); analysis script against synthetic data. |
| Minor (full-column mean, check-2 not a prediction, denominator, adult not cell-verified, beers figure source) | **Accepted.** |

## 16. Execution log

| Date | Step | Outcome |
|---|---|---|
| 11 Oct | 0 backup | `reports/block_d/backup_20261011/`: the GE, HoloClean and Raha flag files, `detection_results.csv`, `iou.csv`, `_all_constraints.txt` and the Raha caches of all four datasets, plus `results/runs_log.csv`: 1,480 files, 1.7 GB, checksums in `MANIFEST.sha256`; `INPUTS.sha256` fingerprints `dirty.csv`, `clean.csv`, `actual_errors.csv`. `reports/block_d/step9_restore.sh` checks (dry run) and restores (`--apply`). |
| 11 Oct | 2 core flags | All 10 core flag sets frozen read-only in `reports/block_d/flags/` (`MANIFEST.csv`) by `scripts/blockd_freeze_flags.py`. Every set equals Table 3; GE and HoloClean are also cell-identical to the replay. GE hand-written and HoloClean: the 18 Sep files. GE dirty- and clean-profiled: regenerated. Raha run 1: regenerated warm (bc 1.44 s, 317/78/395; nasa 1.74 s, 710/1,864/2,574). Afterwards the inputs were unchanged; the only cache files changed were Raha's `error-detection/detection.dataset`. |
| 11 Oct | D6 safeguard | `scripts/blockd_check_format_only.py nasa`: Raha run 1 minus its format-only FPs is not the perfect detector (710 of 731 TPs, 0 FPs), so the diagnostic version of §3 is added. |
| 11 Oct | addendum | `checks/addendum_raha_run1/run_addendum.py`: the flag-only checks repeated with Raha run 1 on bc and nasa (bike and adult keep the disk file until step 7). 16 mechanism scores change and **0 expected verdicts change**; the pooled expectations equal §9 (19/10/0, 16/4/9, 12/1/16). The frozen `checks/expected_pair_verdicts.csv` is untouched. |
| 13 Oct | schedule | The 15 Oct freeze is dropped (user). The §12 fallback "bike and adult dropped if the core is late" is void; gates 1 and 2 become milestones. Steps 3–9 now run on the 1 TB server, gated by the cross-machine check V4 (`reports/server_plan_2026-10-13.md`). §9 and `expected_pair_verdicts.csv` are unchanged. |
| 13 Oct | 7 extension flags | All 10 bike/adult flag sets frozen on the Mac by `scripts/blockd_freeze_flags.py`, each equal to Table 3. bike: GE hand-written 24,247/0 and HoloClean 25,134/173,845 (the 18 Sep files, replay identical), GE dirty- and clean-profiled empty (regenerated, replay identical), Raha run 1 30,861/15,138/45,999 (warm, cache 508 files). adult: GE ×3 empty (replay identical), HoloClean 1,677/663,530/665,207 regenerated per D8 (replay identical), Raha run 1 865/5,081/5,946 (warm, cache 513 files unchanged). The logged adult Raha runtime (3,103 s) includes a Mac sleep from 14:11 to 14:46 and is not a measurement. Logs in `reports/block_d/logs/step7_*`. |
| 13 Oct | 9 restore | `step9_restore.sh --apply` after the freezes: backup intact, inputs unchanged, 4 Raha cache files differ (`error-detection/detection.dataset`, not migrated), other live files: none. |
| 13 Oct | addendum rerun | `run_addendum.py` with frozen Raha run 1 on all four datasets: 26 mechanism scores change and **0 of 87 expected verdicts change**; pooled expectations equal §9 (19/10/0, 16/4/9, 12/1/16). Replays on the restored disk files: True for bc/nasa/bike GE hand-written and HoloClean; adult HoloClean False (the restored disk file is the stale 17 Sep set of 341,890 cells; the frozen flag set is the regenerated one). |
| 14 Oct | schedule | The server still gives the user no Docker access (admin request pending). The user decided to run steps 4–9 on the Mac, the plan's own fallback, so the V4 cross-machine gate no longer applies to Block D. The 13 Oct Mac core run (at `edf370b`) stays as the driver-validation record. The final runs (check, core and extension, mean and median) are repeated at one git HEAD, because `blockd_analysis.py` combines only runs with the same HEAD, image and host. §9 and `expected_pair_verdicts.csv` are unchanged. |
