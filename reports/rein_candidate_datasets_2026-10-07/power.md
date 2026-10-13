# Power (REIN Table 4, ref [18] Hebrail & Bérard 2012) — feasibility report

Date: 7 Oct 2026. Scripts and intermediate pickles: `SCRATCH/power/` (load.py, prof1-4b.py, pivot.py, count1456.py, dst.py, labels.py, uniq.py, write_derived.py).
Tags: **[M]** = measured / verified, **[I]** = inference or assumption.

## 0. Bottom line

**Recommendation: exclude from the experiments.** At most, use the measured raw-file facts (section 2) in one paragraph of the discussion or threats-to-validity section, as an example of what real numeric errors look like compared with injected ones. No tool runs are needed for that.

Reasons, in short:
1. REIN's 1456 x 24 table cannot be rebuilt from the UCI file: one row per day gives at most 1442 rows [M], and REIN's own files are not available (they are not in the upstream repo or its history, and ResearchGate returns HTTP 403) [M]. Any "Power" we add is our own construction, not REIN's.
2. REIN's injected error types for Power (typos, explicit MVs, implicit MVs) are already covered. Its implicit-MV injector writes the literal string `N/A` into every X column [M], which is the same variant beers already has.
3. HoloClean would get 0 DCs. Every hourly column is 92-99.9 % unique, so `fds_to_dcs.py` drops all FDs (the soilmoisture case) [M for uniqueness, I for the FDX outcome, not run].
4. The interesting part is the real cross-column physical rule. It cannot be expressed in the benchmark's GE driver (single column, string-typed, regex only) or as an FD-derived DC [M, code read].
5. Ground truth: the raw file has 1.25 % missing minutes, 440 empty hour cells in a day x hour pivot and a 400-minute frozen-sensor block. Any clean.csv would contain imputed or stuck values, so it would not be a true ground truth [M].
6. The task is clustering. Block D is fixed on 4 datasets with gates on 11 and 15 Oct. Natural labels exist (season, weekend), but adding one is out of scope [M for the labels].
7. Effort is about 3-4 working days for the REIN-style pivot and 4-6 for the raw-table variant [I]. That collides with the Block D core gate (11 Oct).

## 1. Raw file verification [M]

| item | value |
|---|---|
| user file | `DL/household_power_consumption.txt`, 132,960,755 bytes, 2,075,260 lines (header + 2,075,259 rows), CRLF line endings, mtime 12 Oct 2012 |
| sha256 (user file) | `4259c9d7ece5dbee9ab8d53682baac68d791c864f0f64a52b4043cb3b90894b7` |
| official download | `https://archive.ics.uci.edu/static/public/235/individual+household+electric+power+consumption.zip` -> `DL/power/uci_235_individual_household_electric_power_consumption.zip`, 20,640,916 bytes, sha256 `9f84b46ade8a2d8e1286ec4b2b6c2987a45a755c59f263be3b3b3d10dfbda3ff` |
| zip content | one file, `household_power_consumption.txt`, 132,960,755 bytes, dated 12-10-2012 13:38; sha256 of its content = **identical** to the user file |

The user's file is byte-identical to the official UCI file. It was not modified.

## 2. Profile of the raw minute-level file [M]

**Time axis.** The range is 2006-12-16 17:24 to 2010-11-26 21:02. The 2,075,259 rows form a perfect 1-minute grid: no duplicate timestamps, no missing timestamps, monotonic. There are 1442 calendar days (1440 full, plus 2 partial days with 396 and 1263 minutes). Date strings are not zero-padded (`1/1/2007`).

DST: at all 8 French clock changes there is no 60-minute gap or duplicate hour, and the daily profile shifts by at most 15 minutes across a change. So the timestamps appear to have been regularised by the provider [I]; the method is undocumented.

**Explicit missing values.**
- 25,979 rows (1.2518 %) are missing all 7 measures at once. There are no partially missing rows.
- Two encodings occur in the same row: `?` in 6 fields, and an **empty string** in Sub_metering_3 (the line ends `;?;` then empty).
- Missing minutes come in 71 runs: 38 runs of 1 minute, 14 of 2, 3 of 3-5, 1 of 6-10, 6 of 11-60, 3 of 61-1440 and 6 of 1 day or more.
- The 6 long outages hold 24,647 minutes, which is **94.9 %** of all missing minutes. They are:

| start | length |
|---|---|
| 2010-08-17 | 7226 min (~5.0 days) |
| 2010-09-25 | 5237 min |
| 2007-04-28 | 3723 min |
| 2009-06-13 | 3305 min |
| 2010-01-12 | 3129 min |
| 2010-03-20 | 2027 min |

This missingness is block-structured (outages), not MCAR. It is unlike every injected MV in the benchmark.

**Implicit or disguised values.**
- **Frozen sensor block:** 2008-10-06 10:09-16:48, 400 consecutive minutes with all 7 values identical (0.36, 0.078, 241.18, 1.6, 0, 0, 1). It is the only run of 5 or more identical rows in the whole file. Outside this block, Voltage never stays constant for more than 4 minutes. This is a stuck logger, i.e. disguised missing data, and no `?` marks it.
- **Censored zeros in Global_reactive_power:** 481,561 valid minutes (23.50 %) are exactly 0.000. The smallest non-zero value is 0.046, and the counts per 0.002 step from 0.046 to 0.068 are flat (about 18.5k each). Zero therefore means "below the meter's threshold", not a real 0 [I for the interpretation, M for the counts].
- Global_active_power is never 0 (minimum 0.076 kW). No negative values occur in any column. There are no sentinels (-1, 9999).

**Ranges and resolution.**

| column | range | resolution / notes |
|---|---|---|
| Global_active_power | 0.076-11.122 kW | 2 W steps |
| Global_reactive_power | 0-1.39 kvar | 2 var steps |
| Voltage | 223.2-254.15 V | 0.01 V |
| Global_intensity | 0.2-48.4 A | 0.2 A steps |
| Sub_metering_1 | integer Wh | 91.7 % zeros |
| Sub_metering_2 | integer Wh | 70.1 % zeros |
| Sub_metering_3 | integer Wh, max 31 | 41.6 % zeros |

Voltage exceeds 253 V (230 V + 10 %, the EN 50160 limit) in 57 minutes on 9 days, 51 of them in 2009.

**Physical consistency rules (on the 2,049,280 valid minutes).**
- **R1 (documented by UCI):** Sub_1 + Sub_2 + Sub_3 <= Global_active_power x 1000/60 (Wh per minute).
  - Exceeded at all: 1050 minutes (0.051 %).
  - Exceeded by more than 0.5 Wh: 99 minutes.
  - Exceeded by more than 1 Wh: **33 minutes (0.0016 %)**, on 33 distinct days.
  - Exceeded by more than 2 Wh: 2 minutes. The maximum excess is 2.4 Wh.
  - With a 1 Wh tolerance (the sub-meters are integer Wh), R1 holds in 99.998 % of minutes. Aggregated to hours it is violated in 0 of 34,589 hours.
- **R2:** Global_intensity ≈ sqrt(P² + Q²) x 1000 / Voltage.
  - Residual: mean -0.004 A, sd 0.158. Median |res| is 0.066 A and 99 % of residuals are within 0.687 A.
  - |res| > 0.5 A in 33,262 minutes (1.6 %), > 1 A in 8,299, and > 2 A in **434 (0.021 %, on 329 days)**. The maximum is 4.52 A.
  - Using P alone, without Q, the fit is worse (mean residual +0.071 A).
  - The largest residuals occur where Q = 0 (censoring) and in morning load transitions [I: averaging inside the minute]. R2 is a soft rule and needs a tolerance.
- The extreme peaks are genuine. For example, 11.122 kW and 48.4 A on 2009-02-22 17:09 satisfy R2 within 0.01 A. A σ-based outlier rule would mislabel them, since |robust z| > 4 holds in 131k minutes of Global_active_power.

**Duplicates.**
- There are no tuple duplicates in the entity sense.
- 142,582 valid rows repeat an earlier value vector. This is expected for quantised low-load states.
- 3,411 rows are identical to the previous row; 400 of them are the frozen block.

## 3. Reconstructing REIN's 1456 x 24

**What REIN's code says [M].**
- In `rein/detectors.py:215`, the NADEEF patterns for Power use the columns **X0..X23** with `^[\d]+\.?[\d]*$`, i.e. non-negative decimals.
- In `datasets_dictionary.py`, `power` has error_types `[outliers]` (with `missing_values, typos` commented out), ml_tasks clustering, n_clusters 2, and no label. This does not match Table 4 ("Typos, MVs, Implicit MVs").
- In the paper (§6.2), NADEEF has F1 0.9 with 1088 pattern violations (typos + implicit MVs), Max Entropy has 0.84, and MVD finds only the explicit MVs. Power is also used in the error-rate robustness experiment (Fig. 3b: outliers + MVs, outlier degree 4).
- 0.037 x 34,944 cells ≈ 1,293 erroneous cells. If NADEEF's precision were about 1, roughly 205 of them would be explicit MVs [I].
- REIN's implicit-MV injector (`tools/error-generator/.../implicit_missing_value.py`) maps column names to values by string similarity. None of X0..X23 reaches the 0.3 threshold, so every implicit MV is the string **`N/A`** [M, computed].

**Hypothesis "one row per day, 24 hourly aggregates" [M].**
- The file has 1442 distinct Date strings. A day/month swap during parsing (old pandas, no dayfirst) is injective, so it cannot create extra days.
- Dropping days with an empty hour leaves 1417 rows. Keeping only fully complete days leaves 1358.
- Other groupings tested:

| grouping | rows |
|---|---|
| weekly | 207 |
| 2-day | 721 |
| 12 h | 2883 |
| hourly series | 34,589 (/24 = 1441.2) |
| ISO (year, week, day) | 1442 |

None gives 1456.

**What stays unexplained.**
- The 14 extra rows (1456 - 1442).
- Which variable REIN used, and whether it took the mean or the sum. All 7 variables are non-negative, so NADEEF's pattern does not discriminate. Global_active_power (hourly mean or sum) is the most plausible candidate [I], because it is the standard daily-profile construction and the variable behind UCR PowerCons.

**Numeric coincidences only, not evidence [I].**
- 1456 = 1096 + 360, i.e. UCR ItalyPowerDemand (1096 x 24, 2 classes) + UCR PowerCons (360 x 144, 2 classes, from the same EDF household; 144 points at 10 minutes = 24 after hourly averaging).
- 1456 = 208 x 7 = 4 x 364.

n_clusters = 2 matches PowerCons' warm/cold seasons. This cannot be tested without REIN's file.

**Derived files written** (`DL/power/derived/`):
- `daily_hourly_mean_<var>.csv` for all 7 variables (1442 x 24, columns X0..X23, NaN where an hour has no data)
- `daily_hourly_sum_Global_active_power.csv`
- `hour_cell_valid_minute_counts.csv`
- `missing_minute_runs.csv` (71 runs)
- `minute_rule_violations.csv` (R1 > 1 Wh: 33, R2 > 2 A: 434, V > 253 V: 57, frozen block: 400 rows)

## 4. Ground-truth question [M unless marked]

There is no independent clean measurement. The raw file is the only record, so any clean.csv is "raw minus missing", made by dropping or imputing. For a day x hour pivot (1442 x 24 = 34,608 cells):

**Missing data that must be dropped or imputed.**
- 19 boundary cells are absent (first and last day are partial).
- **421 hour cells have 0 valid minutes.** Together that is 440 NaN cells, or 1.27 %.
- 83 hour cells are aggregated from only 1-59 valid minutes. Their means are based on fewer minutes, and their sums are biased low.
- 25 days have at least one empty hour, and 9 days are completely empty.
- Option A, drop those days: 1417 rows (even further from 1456).
- Option B, impute: about 440 cells (1.3 % of cells, plus 9 whole synthetic days) end up as made-up values in the "ground truth". That is about **34 % of the size of REIN's own injected error count** (~1,293 cells) [I for the comparison].

**Real anomalies that would stay in "clean".**
- The frozen block contaminates 7 hour cells on 2008-10-06 (5 of them entirely).
- R1/R2 violations and over-voltage minutes would also stay. A detector that flags them would be scored as a false positive.

**Verdict:** not a true ground truth. It is a defect of the same family as the existing C1 ground-truth defects, but it cannot be quantified against REIN, because REIN's files are unavailable.

## 5. Fit for this benchmark

**ML task.** REIN's task is clustering with no label (Block D excludes clustering; see the 6 Oct plan). Natural binary labels can be derived from the date, tested on 1417 complete days (24 standardised hourly means of Global_active_power, numpy logistic regression, 5-fold CV, seed 0) [M]:

| label | positives | majority-class accuracy | accuracy | F1 |
|---|---|---|---|---|
| weekend | 28.2 % | 0.718 | 0.809 | 0.616 |
| warm season (Apr-Sep) | 50.4 % | 0.504 | 0.801 | 0.803 |

k-means with k = 2 agrees with these labels 0.678 (weekend) and 0.718 (season). Both labels are well posed, but they are exogenous (derived from the date) and could not contain injected errors. Regression on "daily total" would leak, because it is the sum of the features.

**GE.**
- The benchmark driver (`rein/detectors.py`, around lines 690-705) calls `method(column, **kwargs)` on a string-typed PandasDataset. Only single-column expectations work, and numeric ranges must be written as regexes [M].
- On the REIN-style pivot, GE can only check format and range per column.
- R1 needs `expect_column_pair_values_A_to_be_greater_than_B` on a derived column, or a multicolumn expectation. GE 0.18.19 should have these [I, not checked in the container], but the driver cannot call them. That means a driver change plus a derived column, which changes the dataset shape [I for the effort].

**HoloClean.**
- Pivot: hourly columns are 92.2-99.9 % unique. `fds_to_dcs.py` drops FDs whose LHS uniqueness is >= 0.9, so 0 DCs and HoloClean reduces to its null detector [M for uniqueness; FDX not run].
- Minute level: uniqueness is <= 0.2 %, so FDs would not be filtered. But FDX/HoloClean on 2M rows is infeasible, and arithmetic rules (R1, R2) cannot be expressed as EQ/IQ DCs [I].

**Raha.**
- 1456 x 24 is cheap.
- The minute table (2.08M rows) is far beyond Raha's row ceiling (about 60k rows in 31 GB; clustering takes about 8 x rows² bytes). Only a slice would work: 1 week is 10,080 rows, about 0.8 GB [I, from the 23 Sep scalability memory].

**New error types.**
- REIN-style Power adds **none**: typos are already in nasa, explicit MVs in smartfactory/har/..., and the `N/A` implicit MV in beers.
- The raw minute table has real and new ones: block-structured outage MVs, a frozen sensor (disguised numeric MV), threshold-censored zeros, and cross-column physical-rule violations (R1/R2).
- However, their ground truth is either trivial (`?` cells, which any null check finds), single-event (one frozen block) or ambiguous (R1/R2 residuals within rounding or averaging). There are too few error cells, and too ill-defined, to compute meaningful P/R/F1. A usable version would need a verified clean slice plus newly designed injected cross-column errors (e.g. unit/scale errors, swapped sub-meters), which is synthetic again.

## 6. Integration effort before the 15 Oct freeze [I]

| variant | steps | estimate |
|---|---|---|
| REIN-style pivot (own construction, 1417 or 1442 x 24) | build clean, inject + audit errors (the injector is known to be buggy for typos, see nasa), actual_errors.csv, hand_written GE suite, FDX (expect 0 DCs), Raha 10 seeds, all reporting tables and figures | 3-4 days |
| raw-minute slice with physical rules | define GT, choose slice, extend the GE driver for multi-column expectations, design an injector for rule-breaking errors, runs + reporting | 4-6 days |

Both compete with Block D: the core must be verified by 11 Oct, and bike/adult must finish by 15 Oct. Neither variant feeds Block D, which uses classification/regression and a fixed dataset list.

**Recommendation: exclude.** If the user wants it mentioned at all, write one paragraph with the measured facts from section 2: outage-structured MVs (94.9 % of missing minutes in 6 outages), the 400-minute frozen block, 23.5 % censored zeros, and the R1 rule holding to 99.998 %. Contrast them with the benchmark's injected MCAR errors, and note that REIN's 1456-row Power cannot be reproduced from its cited source.
