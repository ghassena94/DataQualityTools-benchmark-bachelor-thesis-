# REIN datasets not yet in the benchmark: include, ground truth, new error types (7 Oct 2026)

Eight agents downloaded and profiled every dataset in REIN Table 4. Their full reports are in
`reports/rein_candidate_datasets_2026-10-07/` (citation, print3d_water, power, soccer,
gt_existing_A, gt_existing_B, rein_release_hunt, error_types). All downloads are in
`~/Desktop/BA/REIN DATASETS/<dataset>/`, with URL, size and sha256 recorded in each report.
Nothing under `rein-datasets/` was changed.

## 1. Which of the five missing datasets to include

REIN Table 4 has 14 datasets. The benchmark has 9. The five missing ones are Citation,
3D Printer, Water, Power and Soccer.

**Recommendation: add none of them to the evaluation tables before the 15 Oct freeze.**
Two of them can serve as case studies that need no new tool runs.

| Dataset | REIN files published? | Main reasons | Verdict | Effort |
|---|---|---|---|---|
| Citation (5005×2, duplicates + mislabels) | Yes, in `mohamedyd/DVBench`: dirty 5005 rows, clean 3997 rows | The files are not row-aligned: errors are 1008 deleted duplicate rows, so the cell-wise ground truth cannot represent them. REIN's own `get_actual_errors` crashes at row 3997. Raha and HoloClean cannot detect duplicates. GE `be_unique(title)` reaches only cell F1 0.51 / row F1 0.76. The clean labels are noisy too (≥124 VLDB/SIGMOD/TODS papers have CS=0). | Exclude; optional case study (2–4 h, numbers are in the report) | 2.5–4 days |
| 3D Printer (50×12) | No; REIN's errors were "generated manually" | 50 rows: Raha's 20 labels are 40 % of the data, and one TP moves recall by 3.3 points. The raw file has no detectable errors, and REIN has no duplicate injector. About 15 test rows per Block D split. | Exclude | 0.5–1 day |
| Water (527×38, clustering) | No | Injected types (outliers, MVs) repeat har/mercedes/soilmoisture. HoloClean likely gets 0 constraints. No usable Block D label (the classes come from clustering). The raw file has 591 real `?` cells, which the profiled GE tiers would flag as false positives on clean data. | Exclude; **best real-error case study** (≈9 rule-breaking rows, 591 real MVs, 18 documented abnormal days) | 1–1.5 days |
| Power (1456×24, clustering) | No; ResearchGate and repos checked | The table cannot be rebuilt from the UCI file, which has only 1442 days, and the 14 extra rows are unexplained. Every hourly column is 92–99.9 % unique, so HoloClean gets 0 DCs. The injector writes `N/A`, the same variant beers already has. | Exclude | 3–6 days |
| Soccer (180228×44, scalability only) | REIN's clean.csv yes (via LOP repo, 180228×43); REIN's dirty no (LOP's own injections only) | Full-size Raha needs about 260 GB for clustering alone. Injected errors add no new type. Scale is already covered by adult/har/mercedes. | Exclude; optional case study: REIN's soccer "clean" has ≈2 % wrong rows (3501 high confidence), and REIN's own rule "name → birthday" fails on 5551 clean rows | 1.5–3 days |

The deciding factors: the freeze is 15 Oct and the Block D core gate is 11 Oct. None of the
five adds an error type that fits the cell-level evaluation and is not covered already.
Citation's duplicates are the one new type, and they do not fit.

## 2. Are they ground truth?

**No.** None of the 14 `clean.csv` files is a verified ground truth. REIN took each public
source, often transformed, and *assumed* it was clean. Every real error in the source
therefore counts as "clean".

| Dataset | clean.csv vs the cited source | Real errors already inside clean.csv |
|---|---|---|
| adult | Rebuilt exactly: UCI test + train, 3620 `?` rows dropped, label recoded (1 = <=50K) | 47 duplicate rows, 5 pairs with identical features and opposite labels, 229 `capital_gain = 99999` caps |
| breast_cancer | Identical (plus index column and header) | All 16 `?` in Bare Nuclei kept; 3 dirty cells whose "correct" value is `?`; 8 exact duplicates; 4 IDs with both classes |
| nasa | Identical up to float formatting | None found |
| bike | 16/17 columns identical; `dteday` re-encoded wrongly (month stored as minutes) | Humidity 0 on a rainy day (22 rows), frozen "feels-like" temperature (24 rows), 2180 windspeed 0 (likely a disguised MV) |
| beers | Same values as Raha's clean.csv; dirty.csv byte-identical to Raha's | Curator's scripted cleanup, not manual: 1005 empty ibu, 33 duplicate listings, 7 breweries with two IDs |
| smartfactory | One of 4 Kaggle files; Timestamp dropped; **1828 decimal cells rounded to integers** | 160 exact duplicates; 847 rows with both labels; 15 negative power/voltage cells |
| mercedes | Identical (column order differs); Kaggle check via mirrors only | 298 rows with the same features but a different y; 56 duplicate columns |
| soilmoisture | Identical up to formatting | None found (closest to a real ground truth) |
| har | **Wrong citation**: it is a 70k-row slice of UCI Heterogeneity Activity Recognition (Stisen 2015), not Anguita 2013 | 665 `null` labels, which become 24 % of har's label "errors" (null→nan conversion) |
| citation | DVBench clean = first copy per title (case-insensitive), labels corrected by hand | Label noise remains (≥124 database-venue papers have CS=0) |
| 3D printer, water, power, soccer | No REIN clean.csv published (soccer: via LOP, unconfirmed) | Raw sources: water 591 `?` + ≈9 rule breaks; power 25,979 missing minutes + 400-minute frozen sensor; soccer ≈2 % wrong rows |

The downloaded originals are raw data, not ground truth. Only beers (Raha) and citation
(DVBench) also have a published dirty version.

For the thesis (C1, threats to validity): the "ground truth" is the source-as-published.
nasa and soilmoisture show no detectable real errors. adult, breast_cancer, bike,
smartfactory, mercedes and har carry measurable ones.

## 3. New error types

What we already cover: explicit MVs, outliers, typos, pattern/format violations, the `N/A`
implicit MV, FD/rule violations, value swaps and label flips.

How the tools would respond to candidate new types. GE and HoloClean were replayed in a
scratch script that reproduces the stored results exactly. Raha's response is inferred from
its strategy code.

| Type | GE dirty-prof. | GE clean-prof. | GE hand | HoloClean | Raha | Fits cell-level GT |
|---|---|---|---|---|---|---|
| Numeric sentinel `9999` | 0 | 0 | 0.88 | ≈0.02 | high | yes |
| Sentinel `0` | 0 | 0 | 0.56 | ≈0.02 | medium | yes |
| Sentinel = column mode | 0 | 0 | 0 | ≈0.02 | low | yes |
| Category spelling variants (adult) | 0 | 0.94 | 0 | 0.003 | likely | yes |
| Cross-column inconsistency | 0 | 0 | 0 | 0.003 | low | yes |
| Tuple duplicates | 0 | 0 | 0.57 (beers id) | n/a | cannot run | **no** (adds rows) |

**Recommended: numeric disguised missing values (sentinels), injected into a scratch copy of nasa.**
- Inject at 5 % per non-label column (about 375 cells), in two variants: `9999`, and the column mode as a control.
- Reuse `robustness_driver.py` with a new `inject()`.
- The profiled GE tiers cannot see it, because the profiler builds no range rules for numeric columns. The hand-written tier and Raha can.
- It also closes a gap REIN itself declares: implicit MVs are listed for 5 of 14 datasets, but REIN's `implicit_mv` injector writes column-name-matched nonsense (e.g. `Afghanistan` into nasa `chord_length`, `N/A` into mercedes).
- Effort: about 1 day.

**Optional second: category spelling variants on adult.**
- This is the only type where clean-profiled GE beats hand-written GE, so it reverses the tier order seen on all nine datasets.
- Effort: about 1 day. Raha on adult takes about 10 min and 16 GB per run.

**Not worth adding:**
- Duplicates break the cell-aligned ground truth.
- Scale errors, sign flips and column swaps behave like the existing outliers.
- Cross-column inconsistencies are missed by every tool, so they do not discriminate between them.

**Timing:** start only after the Block D core gate (11 Oct). If it does not fit, it is a Ch. 7 item.

## 4. Corrections to earlier assumptions

- HoloClean in this benchmark runs **only** the `ViolationDetector` (`rein/detectors.py:1153`). `NullDetector` is imported but not used.
- Do not run `create_dirty.py` on an existing dataset: it overwrites the frozen `dirty.csv`. Inject only on scratch copies.
