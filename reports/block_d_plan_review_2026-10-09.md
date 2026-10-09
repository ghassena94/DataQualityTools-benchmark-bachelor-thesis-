# Block D plan: pre-run review against the REIN pipeline analysis

Date: 9 Oct 2026.

What was reviewed:
- the Block D plan (5 Oct);
- the driver spec (6 Oct, `driver_spec.md`);
- `reports/rein_downstream_protocol_2026-10-07.md` (the REIN pipeline analysis).

How it was checked:
- Three reviewers looked from three angles: the data, the plan's statements about REIN, and the protocol logic.
- An independent skeptic re-measured every finding.
- Everything was measured on `rein-datasets/` in the container, read-only.
- The Wilcoxon tie problem (item 5) was also re-checked by hand.

**Verdict:**
- No REIN pipeline bug carries over into the plan, and gate check 2 can pass exactly.
- **Eight design points must be fixed or written down before the prediction is committed.** Most of them are one rule or one sentence.
- **Eleven sentences about REIN in the plan are wrong or misleading.**

---

## A. Fix or decide before committing the prediction

**1. Delete counts flags in columns the model never sees.**
- The spec removes every row that has any flag, including flags in the excluded identifier and leak columns:
  - breast_cancer: row index, Sample code number;
  - bike: instant, dteday, casual, registered.
- Training rows kept per seed, all-column flags vs schema-only flags:

  | dataset, configuration | all-column flags | schema-only flags |
  |---|---|---|
  | bike Raha | 374–401 | 921–976 (2.4×) |
  | bc GE hand-written | 253–270 | 307–322 |
  | bc perfect | 195–208 | 234–250 |

- The cell-level reference is affected too: all 22 of GE hand-written's false positives on breast_cancer sit in identifier columns.
- *Fix:* restrict every flag set to the schema columns (features + label) before applying any policy. Use the same restricted set for:
  - the random-control k;
  - rows kept;
  - the Table 3/7 references.

  Report excluded-column flags as a separate count.

**2. Format-only false positives are not "explained by the model-visible ranking".**
- The scale of the problem:
  - nasa Raha: all 1,864 false positives are format-only (frequency 1,365, angle 499);
  - bike Raha: 13,261 of its 14,567 false positives are format-only.
- None of the true errors is format-only, so on nasa the model-visible truth equals the full truth (731 = 731). The planned mitigation therefore changes nothing.
- What these flags cost under each policy:
  - ground-truth repair: nothing;
  - impute: correct values overwritten;
  - delete: rows lost. nasa Raha's 0 rows under delete come entirely from these flags; without them it touches 731 rows, not 1,503.
- *Fix:* add a pre-specified "format-only FP" count, and possibly a reference without them, to the prediction. Correct the risk row and change "every frequency cell" to "every frequency cell plus 499 angle cells".

**3. The pooled permutation test is too liberal when two flag sets are identical.**
- Zero-flag configurations always yield the floor's data, so their pair always ties downstream:
  - bike: GE dirty- and clean-profiled;
  - adult: all three GE tiers.
- Permuting 5 reference scores moves that tie onto other pairs. Type I error at a nominal 0.05:
  - one model: bike 0.125, adult 0.167, all four datasets pooled 0.116;
  - three models sharing one permutation: bike 0.148, adult 0.310.
- breast_cancer and nasa are exact, so the core is unaffected.
- *Fix:* merge identical flag sets into one item before computing concordance, τ-b and the permutation (bike 4 items, adult 3). The pooled error then falls to 0.037. This also removes the τ-b footnote (see B8).

**4. The random-deletion control has no analysis.**
- The plan says it "shows whether a detector removes the right rows", but the spec never compares delete(c) with control(c).
- *Fix:* pre-specify a paired test per dataset × model × configuration, using the same pair rule. Note that the control equals the floor when k = 0 and is degenerate whenever the configuration is.

**5. SciPy 1.7.1's exact Wilcoxon depends on the order of the pair when |d| values tie.**
- The exact mode truncates the rank sum with `int()`.
- Checked here on the same differences, run in both directions:

  | p for d | p for −d | correct exact sign-flip p |
  |---|---|---|
  | 0.0371 | 0.0273 | 0.0293 |
  | 0.0840 | 0.0645 | 0.0684 |

  The skeptic also found a case where the verdict flips: 0.0488 vs 0.0645.
- Ties in |d| are common for F1.
- *Fix:* use an exact sign-flip test on the 10 paired differences (1,024 sign patterns). Keep "zeros dropped; ≤ 5 non-zero = tie".

**6. Under impute, a false flag on the label costs a whole row.**
- Labels are never imputed, so a flagged label drops its row. The plan's table says impute costs only "a correct value overwritten".
- nasa HoloClean flags 934 target cells, all false positives, so impute keeps only 444–465 of 1,202 training rows.
- bike HoloClean keeps 7–13 rows under impute, which is degenerate.
- *Fix:* add "a row, if the flag is on the label" to the table and the prediction.

**7. The degenerate list is incomplete.**
- nasa HoloClean also keeps only 26–34 training rows under delete on all 10 seeds. Under delete, nasa therefore ranks only 3 non-degenerate configurations.
- bike HoloClean is degenerate under delete and impute.
- *Fix:* add these to the plan's risk row and to spec §12. Have `--dry_run` print the degenerate list from the regenerated flags, and commit it with the prediction.

**8. Impute can only gain on parsable errors, and the floor already contains a mean fill.**
- Feature errors that do not parse are mean-filled by featurization in every version, including the floor:
  - breast_cancer 217 of 509;
  - nasa 382 of 731 (30 blanks + 352 typos like `22..`);
  - bike 0.
- Consequences:
  - On breast_cancer, the GE profiled tiers under impute are byte-identical to the floor on 10/10 seeds.
  - On nasa, the RF score with perfect detection + impute (2.260) equals the floor (2.262), with S4 at 1.771. That is 0.3 % of the gap; XGB closes 16 %, Ridge 99 %.
  - The training mean is also polluted by missed parsable typos. The nasa thickness mean is 3.2e8 in dirty against 0.011 in clean; the medians match.
- *Fix:* write in the prediction that
  - the floor = dirty data + mean-filled unparsable cells;
  - impute ranks by recall on *parsable* errors, not by cell precision;
  - tree-model ties on nasa under impute come from the repair, not the detector.

  Decide mean vs median deliberately. REIN's policy is mean-mode, so median would be a stated deviation.

---

## B. Wrong or misleading statements about REIN in the plan

1. "Its default run does not tune at all (hyperopt=False)." The paper says it tuned with Optuna (p.4), and the README command `--hyperopt False` turns tuning **on**. Which mode made the figures cannot be decided.
2. "REIN's training code … imputes the label." Label imputation happens in REIN's **repair** code (`cleaners.py` standardImputer, class mean 2.6981). Missing from the training-code list:
   - the per-array LabelEncoder (beers F1 0.000–0.004);
   - deletion of every row with a NaN;
   - binary F1 scored on the larger code, which is ≤50K on local adult.
3. "In REIN's code, S2 equals S4 for clustering." It *repeats the S4 procedure*, so it is equal only up to random initialisation.
4. "REIN trains models on three of them (Fig. 7)." REIN's Adult has a 0.58 error rate; local adult has 1,701 label flips. REIN shows only S1/S4 there; S2 appears only for Soil Moisture. REIN's closest analogue is its p.10 label-flip experiment, which is text only.
5. "They react differently to the same errors (Fig. 7c, 7j)." Each model is shown on a different set of versions (Nasa: DT 149, XGB 117, a linear model 10), and the published code cannot reproduce Fig. 7. Qualify the claim or rely on Grinsztajn et al.
6. "REIN's other models mostly repeat what these three show." REIN p.10 says the opposite for DT and GNB (Adult DT 0.17–0.99 against Ridge 0.74–0.78). Say instead that the other models are left out for scope.
7. "SciPy 1.7 silently switches to an approximation." It switches only when a zero difference is present, and it warns when it does. The ≤ 5 rule never changes a verdict, because the smallest possible exact p at n = 5 is 0.0625.
8. "Highest τ-b it allows: 0.95 on bike, 0.84 on adult." Zero-flag sets tie downstream too, so τ-b can reach 1.0. After the merge in A3 the sentence is not needed.
9. "No S5 … a dirty test set scores against wrong labels." That is true only for breast_cancer and adult; the nasa and bike targets have no errors.
10. "REIN uses the ground truth only as an upper bound." This is defensible, because REIN frames it that way, but REIN also applies GT repair per detector (Figs. 4c, 7m). Optional clarification.
11. Tuning cost "85,000–100,000". 3,240 × 31 = 100,440, plus 120 S4 models × 31 = 3,720, gives about 104,000. Minor.

Also in the plan: write "stratified by the **clean** class labels". The spec already does this.

---

## C. Notes (no change needed, or cheap extras)

- **Gate 2 passes exactly.** Writing the clean values into the `actual_errors` cells reproduces the clean training hash on 10/10 seeds in all four datasets. This holds when the hash covers the float feature matrix plus the label with excluded columns dropped, as the spec says; string hashes would fail on nasa and bike formatting. XGBoost with n_jobs 1 vs 4 gives identical predictions.
- **Gate 3 exercises no policy code.** An empty mask skips every policy branch. Add one non-empty-mask unit check:
  - perfect + delete keeps n_train minus the flagged rows;
  - perfect + impute changes exactly the flagged parsable cells.
- **Add `label_errors_left`.** Otherwise adult shows 0 errors left in every version: all 1,701 of its errors are in the label.
- **`errors_left_in_features` on breast_cancer** counts about 10 non-error `?` cells, because clean.csv itself has 16 `?` in Bare Nuclei. Compare parsed values before the mean fill.
- **Wasted trainings:**
  - 240 trainings are empty by construction (always-positive under delete or impute);
  - 240 duplicate S4 (perfect or always-positive + GT repair);
  - zero-flag configurations equal the floor under every policy.

  Cache fits by `train_hash`.
- **adult:** delete equals impute by construction, because every flagged row has a flagged label. The spec's "about 1.4k rows under HoloClean" comes from the stale 341,890-flag file; the Table 3 file allows at most 874.
- **S1/S3** use the version's labels and test rows that differ by configuration. Fine for an appendix; say so.

## D. REIN bugs the plan already avoids (measured)

The plan already avoids these REIN bugs:
- misaligned splits (REIN's dropna keeps breast_cancer 452/699 rows and nasa 1,473/1,503);
- unrecorded entropy seeds;
- S2/S3 stored as 0 (dirty breast_cancer and nasa have stray strings in every numeric feature);
- per-array LabelEncoder;
- label imputation;
- cleaning before the split;
- Delete shrinking the S2 test set;
- 60 hidden CV fits per call;
- identifier and leak features.

Two further checks came out clean:
- Column order, names and row counts match between dirty and clean in all four datasets.
- No dirty label falls outside the clean label set.

Scripts and raw output are in the session scratchpad (`data_checks*.py`, `skeptic_check*.py`).
