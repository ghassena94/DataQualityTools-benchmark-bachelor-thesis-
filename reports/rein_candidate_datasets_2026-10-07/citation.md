# Citation (REIN Table 4: 5005 x 2, Duplicates + Mislabels, C) — feasibility report

Date: 7 Oct 2026. REPO untouched (read-only). All numbers below marked **[measured]** were computed on the downloaded files with SCRATCH/venv/bin/python; **[inference]** marks reasoning that is not directly verified.

## 0. Bottom line

- REIN's Citation table is found: CleanML `data/Citation/raw/raw.csv` (5005 x 2, columns `CS,title`), and a prepared pair `dirty.csv` (5005 rows) / `clean.csv` (3997 rows) in the REIN author's own repo **mohamedyd/DVBench**. [measured]
- The pair is **not cell-aligned**: clean.csv is dirty.csv with 1008 duplicate rows removed (case-insensitive title dedup, keep first) and 104 labels changed. 1008 / 5005 = **0.2014**, which matches REIN's error rate of 0.2. [measured]
- This benchmark's ground truth is a positional cell diff. It cannot represent deleted rows, and `get_actual_errors` crashes with an IndexError at row 3997. [measured]
- None of GE, HoloClean or Raha can detect "later copy of a duplicate" in the sense of this ground truth (details in sections 5 and 6). [measured + inference]
  - 772 duplicate rows are byte-identical to an earlier row, so cell-level features cannot tell them apart from the first copy.
  - GE `unique(title)` flags every copy, including the first one.
  - HoloClean and Raha can at best find label conflicts through title -> CS.
- The ML task title -> CS is weak. With REIN's one-hot encoding it collapses to the majority class on clean data. The "clean" labels still contain at least 124 obvious mislabels (VLDB/SIGMOD/TODS papers labelled CS=0). [measured]
- **Recommendation: exclude from the main benchmark; at most a short case study (the numbers in §5 are already computed).** Full integration is about 2.5–4 days and touches Raha, the repair evaluation and Block D, which is not compatible with the 15 Oct freeze.

## 1. Downloads (DL = "/Users/ghassen.aicha@caronsale.de/Desktop/BA/REIN DATASETS")

| File (under DL/citation/) | Source URL | Size (B) | sha256 |
|---|---|---|---|
| CleanML-datasets-2020.zip (all CleanML datasets; only Citation extracted) | https://www.dropbox.com/s/nerfrhbrseev928/CleanML-datasets-2020.zip?dl=1 (linked from github.com/chu-data-lab/CleanML README) | 227636874 | d640bdb0fd6aa9420fa61852b38a78aa05ae7a886341750be38b1cb5aa6cb053 |
| cleanml_extract/data/Citation/raw/raw.csv | from the zip | 296588 | c7e4615645e4c67efc9a69422c30cf418ee5b70c55d18253abff603be4419a75 |
| cleanml_extract/.../raw/AutoER.csv | from the zip | 21763 | 1cb62ba0c61ed8ecb6faebdc581b6fd10d404c668bb59fdb01d14af578f8f63f |
| cleanml_extract/.../raw/dirty_train.csv | from the zip | 211864 | 88f7f6a5e4647098e8ac907971cacd8c03853085f365d58e3dab5c199f747796 |
| cleanml_extract/.../raw/dirty_test.csv | from the zip | 89731 | 72649359440ba7708168613a7d8ca825bb0b8367184dd1f1d05067595f80e2b4 |
| cleanml_extract/.../raw/idx_train.csv | from the zip | 16734 | 418997ef1bf1d9b13cc3aa4565fb5690a301e887588c9d1de8dd733f2f8b6c95 |
| cleanml_extract/.../raw/idx_test.csv | from the zip | 7183 | 28debe5e325baff798e74d5373c06eb6e0d68433fa68c3abb3a5d6302a5051a9 |
| cleanml_extract/.../raw/version.json | from the zip | 17 | 0f8ac8738f4ec4b96017b7c84cf3c155743567c5b184a94f4eb1d97e63854020 |
| dvbench_mohamedyd/dirty.csv | https://raw.githubusercontent.com/mohamedyd/DVBench/local_tk/microbenchmark/data/datasets/citation/dirty.csv | 291584 | 3d2c7359a45b9dfd7f4e80a9387d11a21c62d1c5f646f4f978abd40d07b6a781 |
| dvbench_mohamedyd/clean.csv | https://raw.githubusercontent.com/mohamedyd/DVBench/local_tk/microbenchmark/data/datasets/citation/clean.csv | 232730 | b17a498da012ae2248861809d26b92d4659488418e8bfb9413cf13df3016f912 |
| upstream_leipzig/DBLP-Scholar.zip (upstream title source, no CS label) | https://dbs.uni-leipzig.de/files/datasets/DBLP-Scholar.zip | 4160005 | 80b9ddbe89d6b78ab583f801e86a8c451e94dbf1a57ba88dfbd180245cff138b |
| upstream_leipzig/DBLP-ACM.zip (upstream title source, no CS label) | https://dbs.uni-leipzig.de/files/datasets/DBLP-ACM.zip | 270239 | e37e7ed8e06722499e6d9e94583fdec279207b13ce6270a37595b6a5d594bc40 |

Notes:
- The same two DVBench files are also on DVBench branch `master` at `experiments/data/citation/`, with identical sizes. They were committed on 3 Aug 2022 ("moved to benchmark folder").
- A folder `DL/citation/rein_prepared/` (clean.csv, dirty.csv, created 11:46) appeared during this session. **I did not create it**; it was probably made by a parallel agent. Its files are byte-identical to my DVBench copies (same sha256). I left it untouched.
- The CleanML zip is 228 MB and covers all CleanML datasets. Only `data/Citation/` is needed, so the zip can be deleted if space matters.
- Searched every branch of the mohamedyd repos for "citation": rein-benchmark, AutoCure, D3Bench, DiffClean, ReClean, RTClean, SAGED, XAI2Clean, DVBench, DataLens, Haipipe and data_cleaning_with_latent_operators. **Only DVBench ships citation.** No `actual_errors.csv` or `error_rate.json` for citation exists in any of them.
- Magellan (REIN ref [13]): the repository page lists "DBLP-Scholar (Small Citation)", "DBLP-ACM" and "Citeseer-DBLP" as entity-matching datasets. The page CleanML cites (`sites.google.com/site/anhaidgroup/useful-stuff/data`) now returns 404. No 5005-row CS-labelled table is downloadable from Magellan.

## 2. Which file is REIN's 5005 x 2 table

[measured]
- `raw.csv` (CleanML) parses to exactly **5005 rows x 2 columns, `CS,title`**. It uses CRLF line endings.
- DVBench `dirty.csv` is **cell-identical** to `raw.csv` (`DataFrame.equals` is True). The only differences are line endings and the trailing newline.
- REIN's dictionary entry (`keys ['CS','title']`, `labels_clf ['CS']`) uses the same column names.
- The CleanML description says "titles of 5,005 publications from Google Scholar and DBLP".

There is no gap to explain: dirty.csv = raw.csv = REIN's 5005 x 2.

Columns:
- `CS`: binary label, 1 = paper is related to Computer Science, 0 = not (CleanML DatasetDescriptions.pdf). This is REIN's "1 numerical" column. Counts in dirty: 2878 x '1', 2125 x '0', 2 x blank.
- `title`: free-text publication title. This is REIN's "1 categorical" column. It has 4058 distinct exact values and 3997 distinct case-insensitive values.
- There are 2 fully blank rows (both cells ''), at rows 1506 and 1627. In clean.csv only one is left, at row 1205.

Upstream of the titles [measured]: 3994 of the 3997 distinct lowercase titles occur in the Leipzig DBLP-Scholar/DBLP-ACM entity-matching tables, 3947 of them in `Scholar.csv` (64,263 Google Scholar records). The CS label is in none of these sources, and how it was derived is undocumented [unverified]. Testing "CS = 1 iff the title is in DBLP/ACM" does not reproduce it (see §3.4).

Other CleanML files:
- `AutoER.csv` holds per-row entity-resolution cluster ids (-1 = no cluster). It is used by CleanML's `AutoERCleaner` and flags 261 duplicate rows.
- `dirty_train/test.csv` (3503 + 1500 rows) and `idx_*.csv` are CleanML's fixed 70/30 split, with the 2 blank rows dropped.
- CleanML has **no clean file** for Citation. Its "clean" method is `DuplicatesCleaner`: `df[key_columns=['title']].duplicated(keep='first')`, exact and case-sensitive, which removes 947 rows. CleanML treats Citation as duplicates only, with no mislabels.

## 3. Ground truth

### 3.1 How clean.csv was produced [measured]

- clean.csv has 3997 rows, and its titles are unique (exact and case-insensitive). Every clean title occurs in dirty.
- The clean rows are exactly the **first occurrence of each case-insensitive title** (`title.lower().strip()`), in original dirty order. There are 0 order inversions and the kept index equals the first occurrence for all 3997 rows.
- 5005 − 3997 = **1008 removed rows** = `dirty.title.str.lower().duplicated(keep='first').sum()`. This rule reproduces the row set exactly.
- Normalising punctuation as well would remove 1009 rows. Exactly one punctuation-variant pair survives in clean: "Privacy-preserving data mining" (CS 0) vs "Privacy Preserving Data Mining" (CS 1). This confirms the dedup key was case-insensitive only, not a careful manual entity resolution.
- In 12 of 3996 groups, clean keeps a different casing variant of the title than the first occurrence; for example "Fuzzy Control Systems" became "FUZZY CONTROL SYSTEMS". So 76 dirty rows have an exact title that is absent from clean.
- **Label resolution follows no mechanical rule.** 190 case-insensitive groups have conflicting CS labels (436 rows in them). Clean's label agrees with:
  - the first copy in 86 of 190 groups;
  - the last copy in 106 of 190;
  - max(label) in 128 of 190;
  - the majority, where one exists, in only 28 of 190; 146 of the groups are ties.
  - This is consistent with REIN's note "Actual errors detected manually, some duplicates have also mislabels" [inference: manual or arbitrary choice].
- **Labels were changed only inside conflicting duplicate groups.** No singleton title had its label changed (0 rows).

### 3.2 Alignment [measured]

- **Not cell-aligned.** Dirty has 5005 rows and clean has 3997.
- The first removed duplicate is dirty row 20, so a positional diff is shifted from row 20 onwards.
- A positional comparison of the first 3997 rows marks 5920 of 7994 cells (74.1 %) and 3977 rows as "errors", which is meaningless.
- `groundTruthDF.iat[3997, 0]` raises `IndexError`.

### 3.3 Counts (dirty = 5005 rows, 10010 cells) [measured]

| Quantity | Count | Rate |
|---|---|---|
| Exact duplicate rows (same CS and title as an earlier row) | 772 | 0.154 |
| Duplicate rows by exact title (CleanML key) | 947 | 0.189 |
| **Duplicate rows by case-insensitive title (= rows removed in clean.csv)** | **1008** | **0.2014** |
| Duplicate rows by case- and punctuation-insensitive title | 1009 | 0.2016 |
| Duplicate groups (case-insensitive) | 725 (sizes: 540×2, 134×3, 31×4, 11×5, 3×6, 2×7, 2×9, 1×10, 1×12) | — |
| Groups with conflicting CS | 190 (436 rows) | — |
| Dirty rows whose CS differs from clean CS of their group ("mislabels") | 209 (104 in kept rows, 105 in duplicate rows) | 0.042 |
| Rows that are a duplicate or mislabelled | 1112 | 0.222 |
| REIN-style cells: all cells of 1008 duplicate rows + 104 CS cells in kept rows | 2120 | 0.212 |
| Cell diff if clean is expanded back to the dirty shape (duplicates become invisible) | 285 (209 CS + 76 title casing) | 0.0285 |

### 3.4 How good the "clean" labels are [measured]

- **124 clean rows labelled CS=0 have titles that appear in the DBLP/ACM tables**, where the venues are VLDB (45), SIGMOD (39), TODS (17), VLDB J. (10), SIGMOD Record (6) and others.
- Examples: "Scheduling for shared window joins over data streams" (VLDB) and "Querying XML Views of Relational Data" (VLDB) are both labelled 0.
- 107 of these 124 are singletons that the manual pass never touched.
- So label noise of **at least 3.1 % remains in the ground truth**, and it is invisible to any evaluation against clean.csv.

## 4. How REIN handles duplicates (REPO read-only)

### Detectors
- `rein/detectors.py:976 duplicatesdetector` is the key collision detector, `DuplD`.
  - It applies `pd.DataFrame(dirtydf, columns=keys).duplicated(keep='first')` and marks **all cells** of every later copy.
  - The keys come from the dataset dictionary; for citation they are `['CS','title']`.
  - Because the label is part of the key, duplicates with conflicting labels are not found: 236 of the 1008 rows are missed. [measured]
- `rein/detectors.py:1036 mislabeldetector` compares `dirtydf.iat[i, col]` with `correct_labels.iat[i, col]` **by position**, where `correct_labels = groundtruthDF[labels]` (benchmark.py ~449). With a 3997-row ground truth this is misaligned from row 20 onwards.
- `rein/detectors.py:1896 zeroer`: there is also a Magellan-feature + GMM entity-resolution detector, not run here.

### Ground truth
- `rein/datasets.py:442 get_actual_errors` iterates `dirtyDF.iterrows()` and reads `groundTruthDF.iat[i, j]`, with the same shape required.
  - On citation it would crash at i = 3997.
  - Before that point it would produce 74 % shifted false errors.
  - The `drop_duplicates` helper (line 493) is unused.
- The only escape hatch is `benchmark.py ~417`: if `actual_errors.csv` and `error_rate.json` already exist in the dataset folder, they are loaded instead of being computed.
  - So REIN must have used a precomputed, dirty-indexed actual-errors file for citation [inference]. No such file is published anywhere I could find.

### Reconstructing REIN's ground truth [inference, supported by arithmetic]
- Take GT = all cells of the 1008 case-insensitive duplicate rows (2016 cells, rate 0.2014 → "0.2").
- Key collision with keys `['CS','title']` then scores P = 1.000, R = 0.766, **F1 = 0.867**. REIN reports "DuplD ... average F1 score of 0.86".
- If mislabel cells are added to the ground truth, F1 drops to 0.843.
- So REIN's citation ground truth was most likely the duplicate rows only, at row granularity with all cells marked.
- The REIN paper itself says Raha, ED2 and Meta "do not work in the presence of duplicates ... since the dirty and ground truth versions of the dataset become of different lengths" (rein.txt ~l.1281).

### Can this benchmark's cell-level diff represent duplicates?
- **No.** A same-shape positional diff has no row to compare a deleted duplicate against.
- If clean is expanded back to 5005 rows by copying each group's clean values, duplicate rows equal their clean counterpart. Duplicates disappear and only 285 cells remain (209 labels + 76 casing).

### Row-level alternative
- Define GT_rows = {i : row i is a non-first member of its case-insensitive title group} (1008), optionally ∪ mislabelled rows (209), giving 1112.
- Write it in dirty coordinates as `actual_errors.csv`, marking all cells of each duplicate row and the CS cell of each mislabelled row. The benchmark already supports loading this file.
- Then score detectors at row level with P/R/F1 over row ids.
- Caveat: "which copy is the error" is a positional convention (keep first). A fairer row-level metric scores **duplicate groups** or pairs, i.e. clustering or pair F1 as in entity resolution, not individual rows.

## 5. Tool fit

The simulated detector semantics below were applied to the real data and scored against two ground truths [measured]:
- **A** = 2120 cells (duplicate-row cells + kept-row mislabels);
- **rows** = 1112.

| Detector (semantics) | Cell P/R/F1 vs A | Row P/R/F1 |
|---|---|---|
| Key collision, keys = [CS, title] (REIN config) | 1.000 / 0.728 / 0.843 | 1.000 / 0.694 / 0.820 |
| Key collision, keys = [title] | 1.000 / 0.893 / 0.944 | 1.000 / 0.852 / 0.920 |
| Key collision, keys = [lower(title)] (the rule that built clean.csv) | 1.000 / 0.951 / 0.975 | 1.000 / 0.906 / 0.951 |
| **GE** `expect_column_values_to_be_unique(title)` (GE marks *all* copies, keep=False; the fork marks only the title cell) | 0.581 / 0.451 / 0.508 | 0.639 / 0.945 / 0.762 |
| GE `expect_compound_columns_to_be_unique([CS,title])` (all copies) | 0.602 / 0.755 / 0.670 | 0.605 / 0.724 / 0.659 |
| **HoloClean / Raha-RVD** FD title → CS (both cells of conflicting rows) | 0.672 / 0.247 / 0.361 | 0.790 / 0.277 / 0.410 |
| FD title → CS, CS cell only, vs mislabel-only GT (209 cells) | P 0.479 / R 0.895 / F1 0.624 | — |

### GE
- `expect_column_values_to_be_unique` is the only GE rule that sees duplicates. It cannot single out the "later" copy, so precision is capped at about 0.58–0.64. It is also case-sensitive and misses the 61 casing-variant duplicates.
- The fork's GE loop calls `getattr(ds, rule)(column, **kwargs)` with one `column` and marks only that column's cells (detectors.py ~705). `expect_compound_columns_to_be_unique` takes `column_list`, so it **needs a code change**.
- GE has no rule that can tell a title is mislabelled. `CS in {0,1}` catches only the 2 blank rows.
- dirty_profiled and clean_profiled rules: [inference] the profiler would produce little beyond a value set on CS, since titles are free text.

### HoloClean
- On two columns the only meaningful denial constraint is the FD title → CS.
- It finds label conflicts between exact-title copies (390 rows), but **zero duplicates**, because identical rows violate no FD.
- FDX learns from clean.csv, where title is unique. Whether FDX outputs anything for a 2-column table with a key column is unknown [inference]. The memory notes record FDX failure modes that depend on dataset shape, so this is untested.

### Raha
- Raha is cell-level, and the 772 exact duplicates are byte-identical to their first copy in both cells. Their feature vectors are therefore identical to the first copy's, and the classifier **cannot separate first from later copy** by construction.
- In this fork Raha also derives its labels from a positional dirty-vs-clean diff (memory: raha-labels-from-positional-diff), which is broken by the length mismatch. REIN states the same limitation.
- The pattern and outlier strategies have almost nothing to work with: one binary column and one free-text column.

### Downstream task title → CS [measured, 10 random 70/30 splits; NB coded in numpy because the venv has no sklearn]

| Model | Data | Accuracy | F1 |
|---|---|---|---|
| Majority class | clean | 0.618 | — |
| Exact-title lookup (≈ REIN's `OneHotEncoder(handle_unknown='ignore')` on `title`; models.py l.392) | clean | 0.618 (no signal: 0 % of test titles were seen in training) | 0.764 |
| Exact-title lookup | dirty | 0.676 (25.2 % of test rows leak through duplicates) | 0.773 |
| Bag-of-words naive Bayes | clean | 0.721 | 0.804 |

- With REIN's pipeline the task is degenerate on clean data. Any "gain" on dirty data is **train/test leakage through duplicates**, not learning.
- A text featuriser (TF-IDF or similar) would be needed. That is outside the Block D design fixed on 5 Oct (4 datasets, RF + linear + XGB, tabular).
- The residual 124+ wrong labels in clean.csv also cap any "ground-truth" upper bound.

## 6. Integration effort and recommendation

### Option A, full inclusion: about 2.5–4 working days [estimate]
1. Copy dirty.csv/clean.csv into rein-datasets/citation. Write `actual_errors.csv` and `error_rate.json` in dirty coordinates (duplicate-row cells, optionally mislabel cells) so that `get_actual_errors` is bypassed: 1–2 h.
2. Hand-written GE suite with unique(title), plus a code change for compound uniqueness: 1–2 h.
3. HoloClean: a DC file for title → CS and an FDX trial on 2 columns: 1–3 h.
4. Raha: patch label sourcing to use actual_errors instead of the positional diff, re-verify, and run 6 seeds: 4–8 h. The outcome is known in advance: it cannot detect duplicates.
5. Row- or group-level metrics in the reporting scripts, plus a check that `cell_detection_results.py` and the row metrics do not assume the clean shape: 3–5 h.
6. Repair evaluation and Block D: deleting rows changes the length, the positional repair metrics break, and title needs a text featuriser. That means new pipeline code plus re-validating the Block D gates on 11 and 15 Oct: 1–2 days.

This conflicts with the 15 Oct freeze and the Block D gates, and the result is foreseeable: all three tools fail on duplicates for structural reasons.

### Option B, case study only: about 2–4 h
- Report §3–§5 as a short "out-of-scope error type" box in the thesis:
  - real duplicates;
  - why a cell-level GT cannot encode them;
  - what GE unique, FD title → CS and Raha can and cannot do;
  - leakage in the downstream task.
- Optionally confirm the GE keep=False semantics by running `PandasDataset(dirty).expect_column_values_to_be_unique('title', result_format='COMPLETE')` once outside the benchmark (about 30 min). No changes to REPO are needed.

### Option C: exclude, 0 h.

### Recommendation: **exclude from the benchmark tables (Option C); use Option B only if a half-page case study helps the discussion of uncovered error types.**

Reasons:
1. The ground truth is not cell-aligned, so it needs a parallel row-level evaluation path.
2. None of the three tools can detect duplicates as defined: identical copies are indistinguishable cell by cell, and GE unique flags all copies.
3. The mislabel ground truth is itself noisy: label resolution follows no rule and at least 124 obvious mislabels remain in clean.csv.
4. The ML task is degenerate under the existing one-hot pipeline and is dominated by duplicate leakage.
5. Full integration costs days and would destabilise Block D before the freeze.
