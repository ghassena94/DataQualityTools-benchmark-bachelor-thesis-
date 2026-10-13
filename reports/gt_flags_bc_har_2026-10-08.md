# breast_cancer and HAR: what the Ch. 5 draft says and what the data shows (8 Oct 2026)

Scripts and raw output are in `reports/gt_flags_bc_har_2026-10-08/`.

The GE results are a replay: the real profiler and hand-written suite (`rein/auxiliaries/`) are evaluated with GE's legacy semantics. The replay reproduces the published numbers exactly:
- breast_cancer, Table 3: 0.554 / 0.603 / 0.803.
- HAR, §5.2.5: F G1 0.66–0.68 for the profiled suites and 0.89 for the hand-written suite.

HoloClean uses the stored detections, which match Table 3 (5691 detections, 416 TP). Raha's run-1 detections for breast_cancer are not on disk, so Raha is not re-scored.

---

## 1. breast_cancer (§5.2.1)

### What the draft says
> Of the 631 errors on breast cancer, 247 are blanks. The rest are corrupted strings [...] and values swapped for another legal value. [...] The clean-profiled suite adds only the 31 values that are not numbers (F1 = 0.603). The hand-written suite states the legal range of each column [...]. What it misses are mostly the swapped values, which are legal. **Precision is about 0.95 for all three suites.**

### What the data shows

**(a) The errors include 107 cells in two identifier columns.**

| Column | Errors | Kinds |
|---|---|---|
| `Unnamed: 0` (row number written by pandas; not in the UCI file, which has 11 columns, against 12 in clean.csv) | 47 | 23 another row's number, 19 blank, 5 non-digits (e.g. `425` → `\x9b425`) |
| `Sample code number` (patient ID) | 60 | 19 non-digits (e.g. `1298484` → `129848Ŵ4`), 18 blank, 17 another row's ID, 6 new numbers |

That is 17 % of the 631 errors. None of them is a medical value.

**(b) Every false positive of the three suites has a known cause, and none is a correct medical value.**

| Suite | FP | Where | Cause |
|---|---|---|---|
| dirty-profiled | 13 | Bare Nuclei | dirty value `?`, which clean.csv also has (rows 23, 139, 145, …). These are the UCI file's own missing values, documented in `breast-cancer-wisconsin.names` (16 cells, all 16 still in clean.csv). The profiler's `MISSING_TOKENS` contains `?`, so the cell is flagged; the ground truth says "unchanged". |
| clean-profiled | 13 | Bare Nuclei | the same 13 cells |
| hand-written | 22 | `Unnamed: 0` | `expect_column_values_to_be_unique`. Example: row 414's number was corrupted to `2`, so rows 2 and 414 both carry `2` and both are flagged. Row 414 is a TP; row 2 is a correct value. All 22 FPs are such untouched twins. |

**(c) The clean-profiled suite's advantage comes mostly from the identifiers.**
- It finds 31 more errors than the dirty-profiled suite: 19 patient IDs, 5 row numbers and 7 medical values.
- On the ten medical columns the gain is 7 cells. The F1 gap is 0.049 overall but 0.014 on the medical columns.

**(d) Sensitivity check.** Each scenario changes one thing:
- *As published*: Table 3.
- *Without the two identifier columns*: identifier errors and detections are removed.
- *With the 13 `?` as errors*: the 13 source `?` cells are counted as real errors.

| Configuration | As published P / F1 | Without identifiers P / F1 | With the 13 `?` as errors P / F1 |
|---|---|---|---|
| GE dirty-profiled | 0.950 / 0.554 | 0.942 / 0.562 | **1.000** / 0.575 |
| GE clean-profiled | 0.955 / 0.603 | 0.943 / 0.576 | **1.000** / 0.622 |
| GE hand-written | 0.952 / 0.803 | **1.000** / 0.808 | 0.952 / 0.793 |
| HoloClean | 0.073 / 0.132 | 0.073 / 0.134 (recall 0.659 → 0.794) | 0.073 / 0.131 |

HoloClean flags nothing in the identifier columns, because the uniqueness filter removes them. Its recall therefore rises once the 107 errors it cannot reach are removed.

**(e) Minor point.** 3 of the 16 source `?` cells received injected errors:
- row 40: `?` → `1`
- row 235: `?` → `??`
- row 275: `?` → blank

The ground truth's "correct value" for these cells is a missing marker. That matters for any repair evaluation.

### What is wrong or inconsistent
1. **"Precision is about 0.95" is the right number with the wrong reading.** It suggests the suites flag correct values about 5 % of the time. In fact:
   - no suite flags a single correct medical value;
   - the profiled suites' only FPs are real missing values of the original data;
   - the hand-written suite's only FPs are correct row numbers that collide with injected duplicates.
2. **Inconsistent with §5.1.3.** There you argue that HoloClean's false positives are *structural*: a violation shows that one of the cells is wrong, not which. The hand-written suite's uniqueness rule has exactly this structure, and it is the source of all 22 of its FPs. The draft attributes structural FPs only to HoloClean.
3. **"The clean-profiled suite adds only the 31 values that are not numbers" is incomplete.** 24 of the 31 are identifiers, which the conclusion "human knowledge decides the result only for malformed values" partly rests on.
4. **The error description is incomplete.** "corrupted strings and swapped values" leaves out that 17 % of the errors sit in a row number and a patient ID. One of those columns does not exist in the source.

No published F1 or ranking on breast_cancer changes. What changes is the interpretation.

---

## 2. HAR (Table 2, §5.1.1, §5.2.5)

### What the draft says
- **§5.1.1, defect 2:** NaN vs empty string. "A cell is now treated as erroneous only when it is missing on exactly one side." Also: "all three [defects] were fixed before any experiment was run."
- **Table 2, har:** ε = 0.1481, ρ = 0.5597, F1base 0.2580 / 0.7177, ρ̂ 0.5514, ρ − ρ̂ +0.0083.
- **§5.2.5:** "On har, Raha reaches 0.97–1.00, the hand-written suite 0.89, and the profiled suites 0.66–0.68, since they flag the missing values and almost none of the outliers."

### What the data shows

**(a) One label value is rewritten on every row; the others on 3 % of rows.**

| Clean label | Rows | Changed in dirty | Dirty value |
|---|---|---|---|
| stand | 40,164 | 1,185 (3.0 %) | blank |
| sit | 29,171 | 902 (3.1 %) | blank |
| **null** | **665** | **665 (100 %)** | `nan` ×640, blank ×25 |

- The text `nan` occurs nowhere else in dirty.csv. The 25 blanks on `null` rows match the 3.0 % blank rate of the injected missing values (20 expected, binomial p = 0.26).
- So the 640 `nan` cells come from no injector, and the 25 blanks are injected missing values that landed on these rows.

**(b) The mechanism reproduces with REIN's own code path and REIN's pandas 1.3.3** (run in the rein container on three toy rows):
1. `Datasets.__init__` reads clean.csv with pandas defaults. `null` is a default NA token, so it becomes NaN.
2. `inject_errors` calls `dirtyDF.astype(str)` before the error generator. NaN becomes the text `nan` (`rein/datasets.py:760`).
3. `to_csv` writes `nan`.
4. The benchmark later reads both files with `keep_default_na=False`, so `__cells_differ('nan', 'null')` is True: the cell counts as an error.

**(c) Effect on Table 2.**

| | errors | ε | ρ | F1base cell / row | ρ̂ | ρ − ρ̂ |
|---|---|---|---|---|---|---|
| Published | 51,845 | 0.1481 | 0.5597 | 0.2580 / 0.7177 | 0.5514 | +0.0083 |
| Without the 665 | 51,180 | 0.1462 | 0.5556 | 0.2551 / 0.7143 | 0.5464 | +0.0092 |

**(d) Effect on §5.2.5** (full table, F G1, the measure the draft quotes).

| Suite | Published | Without the 665 | Why |
|---|---|---|---|
| dirty-profiled | 0.658 | 0.667 | flags only the 25 blanks |
| clean-profiled | 0.682 | **0.662** | Its value set, profiled from clean, is {stand, sit}, so it rejects `nan`. Its 640 extra TPs over dirty-profiled are exactly the 640 `nan` cells. |
| hand-written | 0.886 | 0.881 | its rule allows `null`, so it flags all 665 |

- **The order of the two profiled suites on HAR flips.** The clean-profiled suite's whole lead on HAR is the artifact.
- The draft's reason ("they flag the missing values") is also not right for the clean-profiled suite: 640 of its hits are neither missing values nor outliers.
- Raha cannot be re-scored here: no full-table run, and the scalability detections were not kept.

**(e) Why the fix must not simply be widened.** Suppose any missing token (`''`, `nan`, `null`, `N/A`, `?` …) on both sides counted as unchanged. That rule would remove:

| Dataset | Cells removed |
|---|---|
| har | 665 |
| **beers** | **1,005** (ibu `''` → `N/A`: 23 % of beers' errors and the first row of Table 5) |
| breast_cancer | 1 |

beers' `N/A` cells are part of the published dirty file and of Raha's own ground truth (same ε 0.1645). HAR's `nan` cells are produced by no injector. **The criterion is where an error comes from, not the token.**

### What is wrong or inconsistent
1. **It is a defect in how REIN generated dirty.csv, not in your comparison.** Your defect-2 fix is correct for what it targets: the same blank cell read as `''` on one side and NaN on the other. (Correction to my previous message, which said "your fix doesn't catch it".)
2. **"All three were fixed" is true, but the list of ground-truth problems is not complete.** HAR has a fourth one of the same family, missing-value representation across I/O paths. It sits in the data: 24 % of HAR's label errors (665 of 2,752) are an I/O conversion of one class, at a 100 % rate.
3. **The rule as worded is broader than the code.** "missing on exactly one side", read literally, would also exempt beers' `''` → `N/A` (missing on both sides). Yet Table 5 counts those 1,005 cells as errors. The rule should be worded as the code implements it: only an empty cell (`''` or NaN) counts as missing; a missing value written with a different token is a changed value.
4. **The §5.2.5 HAR sentence is incomplete.** The ranking of the two profiled suites on HAR depends on this artifact.
5. **Scope:** HAR is scalability-only. Table 3, Table 7, the ranking and Block D are unaffected.

---

## Suggested wording (draft)

**§5.1.1, after defect 2:**
> The fix treats only an empty cell, read as the empty string or as NaN, as missing; a missing value written with a different token, such as N/A in beers, is a changed value and counts as an error. One effect of the same kind remains in the data itself: REIN's injector reads clean files with pandas' default missing-value tokens, so har's 665 labels `null` were read as missing and written back as the text `nan`. These 665 cells (24% of har's label errors) were produced by no error injector. har is used only in the scalability experiment; without them its ε would be 0.1462 instead of 0.1481.

**§5.2.1, breast cancer, replacing "Precision is about 0.95 for all three suites":**
> Precision is about 0.95 for all three suites, but none of them flags a correct medical value. The 13 false positives of the profiled suites are the original data's own missing values (`?` in Bare Nuclei), which the ground truth inherits as correct. The 22 of the hand-written suite are correct row numbers that an injected error duplicated: a uniqueness rule, like a denial constraint, shows that one of two cells is wrong but not which (Section 5.1.3). 107 of the 631 errors lie in the row number and the patient ID rather than in a medical attribute; 24 of the 31 cells the clean-profiled suite adds are among them.

**§5.2.5, HAR:**
> The clean-profiled suite's lead over the dirty-profiled one on har (F G1 0.68 against 0.66) comes from the 640 `nan` labels described in Section 5.1.1; without them the order reverses (0.662 against 0.667).
