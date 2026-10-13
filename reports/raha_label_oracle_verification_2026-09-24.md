# Raha label oracle: verification of the 23 Sep claim (2026-09-24)

**Verdict: confirmed.** In this benchmark Raha labels its sampled tuples from its own positional string diff of dirty.csv against clean.csv, not from actual_errors.csv, while the benchmark scores its detections against actual_errors.csv. The Table 3 rows of Raha on nasa, bike and smartfactory are artifacts of that mismatch; beers, breast_cancer, soilmoisture and adult are unaffected. Every number below was re-derived with Raha's own `Dataset` class inside the container and with the csv module on the host, independently of the 23 Sep script.

## Mechanism

`Detectors.raha` (rein/detectors.py:740-755) hands Raha two file paths, dirty.csv and clean.csv, and calls `Detection.run`; no labels are passed. `initialize_dataset` (raha/detection.py:128) builds `raha.dataset.Dataset`, whose `read_csv_dataset` (raha/dataset.py:53-59) reads both files as strings (`dtype=str, keep_default_na=False`) and only unescapes HTML, collapses whitespace and strips. `label_with_ground_truth` (raha/detection.py:289-301) labels a sampled cell as an error iff it is a key of `d.get_actual_errors_dictionary()` (raha/dataset.py:90-94), which is `get_dataframes_difference` (raha/dataset.py:69-80): `dataframe_1.values != dataframe_2.values`, a positional comparison of the two string arrays with no column-name alignment and no numeric tolerance. The benchmark scores the returned detections in `Detectors.__evaluate` (rein/detectors.py:520-535) against `self.actual_errors`, loaded from actual_errors.csv (rein/benchmark.py:421-436). That file comes from `Dataset.get_actual_errors` (rein/datasets.py:442-491), which reindexes the ground truth onto the dirty column order (lines 463-468) and compares cells with `__cells_differ` (lines 416-440: blank on both sides is equal, numerics through `isclose(rel_tol=1e-6)`). The three fixes of thesis section 5.1.1 therefore exist in REIN's oracle (committed in 28f4c46 on 12 Sep) but not in the oracle Raha learns from. Baran's wrapper (rein/cleaners.py:924-957) uses `Correction.label_with_ground_truth` (raha/correction.py:420-430), the same positional cell comparison, against REIN's typed groundTruthDF; it is not quantified here (see the Parked Flags doc).

## Per dataset: Raha's positional diff against actual_errors.csv

| dataset | rows x cols | positional diff | actual_errors.csv | in both | extras | what the extras are | affected |
|---|---|---|---|---|---|---|---|
| nasa | 1503 x 6 | 2597 | 731 | 731 | 1866 | all float-equal text ('800' vs '800.0'): frequency 1365, angle 499, sound_pressure_level 2 | yes |
| bike | 17379 x 17 | 47537 | 34274 | 34274 | 13263 | 10931 dteday rounding ('359399.0167' vs '359399.01666666666', inside REIN's 1e-6 tolerance) and 2332 float-equal (windspeed 2049, hum 279, atemp 3) | yes |
| smartfactory | 23645 x 19 | 388997 (86.6% of cells) | 7093 | 7093 | 381904 | clean.csv lists `labels` first, dirty.csv last; aligned by name the diff is exactly the 7093 injected cells | yes |
| breast_cancer | 699 x 12 | 631 | 631 | 631 | 0 | | no |
| beers | 2410 x 11 | 4362 | 4362 | 4362 | 0 | | no |
| soilmoisture | 679 x 129 | 26218 | 26218 | 26218 | 0 | | no |
| adult | 45222 x 15 | 1701 | 1701 | 1701 | 0 | | no |

No injected error is missing from any positional diff.

## Stored detections against both oracles

| dataset (run in raha/detections.csv) | detections | vs actual_errors.csv P / R / F1 | false positives inside the positional diff | vs positional diff P / R / F1 |
|---|---|---|---|---|
| nasa (cold run, 23 Sep) | 2595 | 0.2817 / 1.000 / 0.4396 | 1864 of 1864, all float-equal cells | 1.000 / 0.999 / 1.000 |
| bike (iteration 10, 21 Sep) | 46001 | 0.6833 / 0.9171 / 0.7832 | 13261 of 14567 | 0.972 / 0.940 / 0.956 |
| smartfactory (cold run, 23 Sep) | 386960 | 0.0183 / 0.9997 / 0.0360 | 376143 of 379869 | 0.990 / 0.985 / 0.988 |

The logged raha rows in results/detection_results.csv agree: nasa P 0.26 to 0.28, R 0.90 to 1.00, F1 0.40 to 0.44 over the ten seeds and the cold run; smartfactory P 0.017 to 0.018; bike P 0.57 to 0.69. Raha reproduces its own oracle almost perfectly, so the precision ceilings 731 / 2597 = 0.28 (nasa) and 7093 / 388997 = 0.018 (smartfactory) are the file artifacts, not detection behaviour.

## Indicative size of the effect

Raha at budget 20, seed 1, read-only, scored against actual_errors.csv:

| dataset | labels from Raha's own diff | labels from actual_errors.csv |
|---|---|---|
| nasa | F1 0.440 (P 0.28, R 1.00) | F1 0.929 (P 1.00, R 0.87) |
| bike | F1 0.780 (P 0.68, R 0.91) | F1 0.936 (P 0.96, R 0.91) |
| smartfactory | F1 0.032 (P 0.02, R 0.92) | F1 0.298 (P 0.46, R 0.22) |

One seed only; the ten-seed values will differ. smartfactory stays low because 11 of its 19 columns silently get no clustering inside Raha (a separate finding in the Parked Flags doc), which correct labels do not repair.

## Refutation attempts

- Code semantics: Raha cannot align by name (`.values !=` on positional arrays), its normalizer never touches digits, the benchmark passes no labels, and REIN's scoring oracle is a different function that carries the fixes. No hole found.
- Data and consequence: the counts reproduce with Raha's own class; the raw files show '800' vs '800.0' and the swapped header; the precision ceilings match the logged rows to three decimals; the four datasets listed as unaffected have identical diffs. One correction to the 23 Sep note: "381 904 of 449 255 cells (87%)" mixes two numbers; the positional diff is 388 997 cells (86.6%), of which 381 904 (85.0%) are not injected errors.

## Remediation options

(a) Fix the files. smartfactory: reorder clean.csv to the dirty column order; dirty.csv stays unchanged, so the strategy cache stays valid. nasa and bike: rewrite the non-error cells of clean.csv with the dirty text (dirty.csv unchanged, cache valid). Do not rewrite both files with a new float format: that changes dirty.csv, invalidates the Raha caches and makes every other detector's stored run on nasa and bike stale. Cost: 30 warm seeded runs, about 1 h under emulation (nasa seconds, bike about 2.5 min, smartfactory about 3 min per run), plus backups of results/detection_results.csv.

(b) Patch the benchmark. In `Detectors.raha`, drive Raha's steps and replace `d.get_actual_errors_dictionary` with `self.actual_errors` (about 12 lines); Baran's wrapper needs an equivalent clean frame. Same 30 runs, no file edits; the file defects stay in place for anything else that diffs dirty against clean positionally.

Either way, move `raha-baran-results-<ds>/strategy-profiling` aside only if dirty.csv changes, and back up `rein-datasets/<ds>/results/detection_results.csv` before any re-run.

## Thesis places that change if adopted

Table 3 (Raha column: nasa, bike, smartfactory), Table 7 (row level, same three), Table 8 (seeds), the ranking table (Raha's mean rank rises), the nasa, bike and smartfactory paragraphs in section 5.2.1, and section 5.1.1 gains a fourth defect: the same family as the other three (positional column indexing, no numeric tolerance), sitting inside Raha's label oracle, which the benchmark never checked.

## How this was verified

Scripts and raw outputs are in reports/verification_2026-09-24/. Nothing under rein-datasets/, rein/, cleaners/ or scripts/ was modified; Raha ran with SAVE_RESULTS=False on the existing strategy caches.
