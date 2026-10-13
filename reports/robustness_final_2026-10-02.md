# Robustness of the five detection configurations (REIN §6.2.1): final results

Session "Robustness", 2026-10-02, revised after a second and a third refutation pass the same
evening.

- **The only robustness report.** On 3 Oct the earlier reports (`robustness_2026-09-30.md`,
  `robustness_outlier_degree_2026-10-02.md`) were deleted together with the runs of the
  superseded generator variants (degree 3, the 30 Sep rounding and `format_like_clean`). The
  numbers below that come from those variants are marked "deleted 3 Oct".
- **The predictions** they contained are reproduced word for word in the Appendix.
- **Verified 3 Oct (knob 1, then knob 2).** Five independent checkers plus a refutation pass recomputed all 60
  knob-1 runs and all 100 knob-2 runs (both generators) from the run folders; every results.csv
  value matches to 1e-13.
  The errors they found are corrected in place and marked "(corr. 3 Oct)".

**Answer (nasa, cell level; Raha as the average of 6 runs):**

- **The profiled GE suites** catch blanks only: F1 0.29-0.30 at every error rate, 0 when no
  blanks are injected.
- **The hand-written GE suite** catches blanks plus values outside its ranges. Its precision is
  1 by construction (every clean value satisfies its rules). Its F1 is flat in the error rate
  (0.71-0.77) and rises with the outlier degree (0.41 → 0.79).
- **For both GE suites, flat F1 still means falling FG1,** because the always-positive baseline
  rises with the error rate.
- **Raha is unstable at low error rates.** At 1-2 % its average is below the hand-written suite
  (0.60 and 0.62 vs 0.71 and 0.77). Single runs range from 0.24 to 0.87, and 3 of the 12 beat
  the hand-written suite. This holds for Raha's default budget of 20 labelled tuples. From 5 %
  Raha is above the hand-written suite (0.90-0.97; corr. 3 Oct, was 0.98 by double rounding). Across outlier degrees it is above it at
  every degree (0.83 → 0.94-0.97).
- **HoloClean** is below the always-positive baseline (FG1 < 0.5) in every run. Its 4 DCs already
  flag 83 % of the cells of the *clean* nasa table, because one of them has the label as its
  right-hand side (§5).
- **The generator:** with REIN's generator unchanged, injected outliers carry a 12-21-digit
  fingerprint. Raha then scores F1 ≥ 0.9995 in every knob-2 draw and in 26 of 36 knob-1 draws.
  The GE results above barely depend on the generator: the profiled suites' only as-is catches
  are 13 values in scientific notation, F1 < 0.005 (0.0044 at degree 1; corr. 3 Oct). HoloClean's do depend on it, through value
  ties (§5): as is, its knob-2 F1 is flat at 0.223 (FG1 −0.16) instead of falling from 0.34
  to 0.25. All results here use our corrected generator (§2).

## 1. Design

REIN §6.2.1 runs two experiments. We repeat both on nasa with our five configurations: GE
dirty-profiled, GE clean-profiled, GE hand-written, HoloClean (4 FDX-derived DCs) and Raha (20
labelled tuples).

| | knob 1: error rate | knob 2: outlier degree |
|---|---|---|
| varies | asked rate 2, 4, 10, 20, 40, 60 % (measured 1.00-28.59 %) | degree k = 1, 2, …, 10 |
| fixed | outlier degree 4 (REIN paper; REIN's code uses 3) | asked rate 30 % (measured 24.92-24.99 %) |
| injected | outliers + blanks (about 83 % / 17 %) | outliers only |
| REIN ran it on | Adult, Power (Fig. 3a/b) | Smart Factory (Fig. 3c) |

- **Generator.** REIN's own `inject_errors` with the same arguments as `run_robustness_exp` (error
  types, `[rate, degree]`, the label column `sound_pressure_level` muted), starting from nasa's
  clean.csv. Our own choices:
  - the levels and the degree in knob 1 (REIN's code steps through 10-100 % at degree 3);
  - the seeding;
  - restoring the column order;
  - rewriting the injected values' format (§2).

  An outlier is value + N(0, (k·σ_col)²), so k is a noise spread, not the paper's "standard
  deviations away from the mean".
- **Why nasa.** All-numeric datasets with DCs in our benchmark are nasa, bike and Smart Factory
  (soilmoisture has no DCs). nasa is by far the smallest (1 503 × 6), so each run takes seconds,
  including cold Raha runs. Its own shipped dirty file is not used.
- **Pairing.** The injection seed depends only on the rate, so all configurations at a level and
  all degrees in knob 2 start from the same injected cells and draws. Rewriting the format rounds
  a few injected values back to their clean value, and those then drop out of the error set:
  7, 4, 2, 2, 2, 2, 1, 1, 0, 0 cells at degrees 1-10, and 1 cell at the 28.59 % level. Each dirty
  file's sha256 is recorded.
- **Isolation.** Each run uses a fresh container and a scratch copy that is deleted afterwards
  (`scripts/robustness_driver.py`, `run_all.sh`, `run_knob2.sh`). nasa's own files are
  unchanged: none was modified after 27 Sep (a results-file tier rename), and every kept run
  dates from 2 Oct (corr. 3 Oct: no before/after checksum record survives). No time cap.
- **Draws.** The GE suites and HoloClean are deterministic, one run per point. Raha depends on
  its sampled tuples, so every Raha point has the campaign run plus 5 more seeds
  (`raha_seed_check.py`). Text and figures use the average of the 6 runs, as REIN's own figure
  plots average F1; the tables also give the range. A single run can be the best or the worst of
  the six.
- **Metrics.** Cell precision, recall, F1 and FG1 = (F1 − π)/((1 − π)F1), π = measured error rate.
  FG1 0.5 is the always-positive baseline (F1 = 2π/(1+π)); FG1 < 0 means F1 < π. Tables print
  "<0" or "n/a" (no detections); the figures clip both to 0.

## 2. The generator: why and how its output is rewritten

1. **Fingerprint.** REIN's generator writes every injected outlier at full float precision:
   12-21 digits, and 16 of 32 356 values in scientific notation (corr. 3 Oct: 13 of 22 540 in knob
   2, 3 of 4 908 in the degree-3 knob-1 runs, deleted 3 Oct, and 0 of 4 908 in the degree-4
   knob-1 runs reported here). Every clean nasa value has at
   most 10 digits; blanks carry no digits.
   - With the generator as is, Raha's F1 is ≥ 0.9995 in all 60 knob-2 draws, including degree 1.
   - In knob 1 it is ≥ 0.9995 in 26 of 36 draws (averages 0.82 at 1 %, 0.92 at 2 %, 0.98-1.00
     above).
   - A single dBoost outlier strategy per column (gaussian or histogram; Raha writes the file with
     its header, so dBoost reads every value as a string) flags almost exactly the long strings
     (`raha_strategy_check_asis.txt`; corr. 3 Oct: this check ran on the knob-2 degree-1 file only
     and misses one 14-character angle value. No knob-1 file was strategy-checked, but there too
     every injected value is longer than every untouched value of its column: 13-19 vs 4-11
     characters).
   - The GE suites barely use it. Their knob-1 F1 at degree 4 is the same with either generator to
     within 0.001 (max 0.0009; corr. 3 Oct). Their only fingerprint catches are values in scientific notation, which fail the "is a
     number" pattern: 13 in knob 2 and none in the degree-4 knob-1 files, where the profiled
     suites catch exactly the blanks (corr. 3 Oct).
   - HoloClean does not use the digits, but the generator changes its result through value ties
     (§5): within 0.05 F1 in knob 1, and flat vs falling in knob 2.
2. **Rule (`--write_like_clean`, our addition, chosen after seeing the as-is results and two
   earlier attempts).** Each injected non-blank value is rewritten in its column's number
   format:
   - fixed-decimal columns keep their width and real precision (frequency "-4513.0", angle
     "6.4", chord "0.6047", velocity "70.6");
   - thickness is rounded to 6 significant digits with trailing zeros dropped (so 3-6 digits;
     clean thickness has 4-6);
   - a column whose clean values never end in 0 gets no value ending in 0. The last digit is moved
     by one unit of the column's precision, which doubles the share of values ending in 1 in
     chord and velocity; 1 is not a clean final digit there either.
   - never "-0.0".

   This changes the values slightly (rounding, plus the one-unit move). The earlier attempts
   (their runs deleted 3 Oct) had these flaws:
   - the 30 Sep rounding padded every value to a fixed width;
   - `format_like_clean` left thickness with 7-9 significant digits.
3. **What the rule removes and what it cannot remove.**
   - **Removed:** number formatting. No injected value is longer than the column's longest clean
     format allows unless its magnitude or sign differs. No scientific notation, no padding, no
     "-0.0".
   - **Not removable:** the injected values are *new* values. On nasa's small value sets
     (velocity 4 distinct values, chord length 6, frequency 21 on a 1/3-octave grid, angle 27),
     a new value is visible as a string too. 47-56 % per file over all 16 main-protocol files (knob 2 alone: 50-55 %; corr. 3 Oct) of the in-range (hence non-negative) injected
     values contain a digit, final digit, significant-digit count or length that no clean value
     of their column has. Examples: chord values ending in any digit other than 4, 6 or 8 (the
     only clean endings); frequencies with 4-5 significant digits (the grid has at most 3); and
     velocity digits outside {1, 3, 5, 6, 7, 9}.
   - These are properties of the values, not of their formatting. A real error that moves a
     value off a small grid shows them too. They make nasa easy for any detector that learns a
     column's value set; Raha's character-pattern strategies are such detectors. Negative
     numbers (no clean nasa value is negative) and out-of-range magnitudes also remain.
4. **Table 3: bike is affected, the others are not or only through typos.** Checked per column
   (as Raha's strategies work), the share of float-parseable error cells longer than every
   untouched value of their column is:
   - **bike 73.5 %:** its shipped dirty file has Gaussian outliers written with 8-9 decimals,
     e.g. hour "2" → "12.56705226";
   - **nasa 29 %:** its errors are typos, not outliers;
   - **soilmoisture 1.6 %;**
   - **breast_cancer and adult 0 %.**

   Bike's Raha row in Table 3 may therefore be inflated by the same effect. This is parked for
   the main session; this report does not re-run Table 3. Mercedes' file carries the
   fingerprint fully, but mercedes is not in Table 3.

## 3. Knob 1: error rate (outlier degree 4)

![Knob 1, main](robustness/fig_robustness_error_rate_d4_cleanstyle.png)

- **Figure:** `fig_robustness_error_rate_d4_cleanstyle.{pdf,png}` (Raha: average of 6
  draws).
- **With the as-is generator above it:** `fig_robustness_error_rate_d4_asis_cleanstyle.{pdf,png}`.

**Cell F1 / FG1** (Raha: the single campaign run; averages in the next table)

| asked | measured | dirty-prof. | clean-prof. | hand-written | HoloClean | Raha (1 run) |
|---|---|---|---|---|---|---|
| 2 % | 1.00 % | 0.286 / 0.975 | 0.286 / 0.975 | 0.705 / 0.996 | 0.018 / 0.443 | 0.776 / 0.997 |
| 4 % | 1.97 % | 0.288 / 0.950 | 0.288 / 0.950 | 0.772 / 0.994 | 0.029 / 0.330 | 0.541 / 0.983 |
| 10 % | 4.98 % | 0.286 / 0.869 | 0.286 / 0.869 | 0.761 / 0.984 | 0.076 / 0.360 | 0.858 / 0.991 |
| 20 % | 9.86 % | 0.289 / 0.731 | 0.289 / 0.731 | 0.746 / 0.963 | 0.139 / 0.320 | 0.983 / 0.998 |
| 40 % | 19.34 % | 0.294 / 0.423 | 0.294 / 0.423 | 0.753 / 0.922 | 0.253 / 0.293 | 0.946 / 0.986 |
| 60 % | 28.59 % | 0.298 / 0.056 | 0.298 / 0.056 | 0.752 / 0.868 | 0.334 / 0.203 | 0.960 / 0.983 |

**Raha, all six runs** (averages from exact counts), next to the hand-written suite and to Raha on
the as-is generator

| measured | campaign run | seeds 1-5 | average of 6 | range | hand-written | Raha as is (average of 6) |
|---|---|---|---|---|---|---|
| 1.00 % | 0.776 | 0.667, 0.636, 0.571, 0.615, 0.333 | **0.600** | 0.333-0.776 | 0.705 | 0.822 |
| 1.97 % | 0.541 | 0.833, 0.625, 0.623, 0.870, 0.244 | **0.623** | 0.244-0.870 | 0.772 | 0.924 |
| 4.98 % | 0.858 | 0.980, 0.933, 0.868, 0.932, 0.855 | **0.904** | 0.855-0.980 | 0.761 | 0.981 |
| 9.86 % | 0.983 | 0.972, 0.974, 0.983, 0.979, 0.958 | **0.975** | 0.958-0.983 | 0.746 | 1.000 |
| 19.34 % | 0.946 | 0.937, 0.916, 0.954, 0.974, 0.949 | **0.946** | 0.916-0.974 | 0.753 | 1.000 |
| 28.59 % | 0.960 | 0.964, 0.973, 0.948, 0.970, 0.941 | **0.959** | 0.941-0.973 | 0.752 | 0.992 |

## 4. Knob 2: outlier degree (asked rate 30 %)

![Knob 2, main](robustness/fig_robustness_outlier_degree_cleanstyle.png)

- **Figure:** `fig_robustness_outlier_degree_cleanstyle.{pdf,png}`.
- **With the as-is generator above it:** `fig_robustness_outlier_degree_asis_cleanstyle.{pdf,png}`.

**Cell F1 / FG1** (profiled suites: no detections, FG1 undefined; Raha: single campaign run)

| degree | measured | dirty-prof. | clean-prof. | hand-written | HoloClean | Raha (1 run) |
|---|---|---|---|---|---|---|
| 1 | 24.92 % | 0.000 / n/a | 0.000 / n/a | 0.414 / 0.531 | 0.339 / 0.354 | 0.834 / 0.934 |
| 2 | 24.95 % | 0.000 / n/a | 0.000 / n/a | 0.550 / 0.728 | 0.321 / 0.296 | 0.867 / 0.949 |
| 3 | 24.97 % | 0.000 / n/a | 0.000 / n/a | 0.638 / 0.811 | 0.309 / 0.255 | 0.919 / 0.971 |
| 4 | 24.97 % | 0.000 / n/a | 0.000 / n/a | 0.688 / 0.849 | 0.292 / 0.195 | 0.956 / 0.985 |
| 5 | 24.97 % | 0.000 / n/a | 0.000 / n/a | 0.719 / 0.870 | 0.281 / 0.149 | 0.882 / 0.955 |
| 6 | 24.97 % | 0.000 / n/a | 0.000 / n/a | 0.746 / 0.887 | 0.270 / 0.100 | 0.914 / 0.969 |
| 7 | 24.98 % | 0.000 / n/a | 0.000 / n/a | 0.759 / 0.894 | 0.274 / 0.118 | 0.974 / 0.991 |
| 8 | 24.98 % | 0.000 / n/a | 0.000 / n/a | 0.771 / 0.901 | 0.263 / 0.068 | 0.971 / 0.990 |
| 9 | 24.99 % | 0.000 / n/a | 0.000 / n/a | 0.780 / 0.906 | 0.258 / 0.042 | 0.979 / 0.993 |
| 10 | 24.99 % | 0.000 / n/a | 0.000 / n/a | 0.790 / 0.911 | 0.252 / 0.012 | 0.970 / 0.990 |

**Raha, all six draws**, next to the hand-written suite and to Raha on the as-is generator

| degree | campaign run | seeds 1-5 | average of 6 | range | hand-written | Raha as is, all 6 draws |
|---|---|---|---|---|---|---|
| 1 | 0.834 | 0.884, 0.831, 0.812, 0.733, 0.860 | **0.826** | 0.733-0.884 | 0.414 | ≥ 0.9995 |
| 2 | 0.867 | 0.905, 0.926, 0.911, 0.900, 0.895 | **0.901** | 0.867-0.926 | 0.550 | ≥ 0.9995 |
| 3 | 0.919 | 0.883, 0.919, 0.930, 0.884, 0.908 | **0.907** | 0.883-0.930 | 0.638 | ≥ 0.9995 |
| 4 | 0.956 | 0.918, 0.952, 0.923, 0.949, 0.931 | **0.938** | 0.918-0.956 | 0.688 | ≥ 0.9995 |
| 5 | 0.882 | 0.929, 0.963, 0.915, 0.972, 0.971 | **0.939** | 0.882-0.972 | 0.719 | ≥ 0.9995 |
| 6 | 0.914 | 0.933, 0.965, 0.942, 0.964, 0.942 | **0.943** | 0.914-0.965 | 0.746 | ≥ 0.9995 |
| 7 | 0.974 | 0.974, 0.973, 0.966, 0.975, 0.971 | **0.972** | 0.966-0.975 | 0.759 | ≥ 0.9995 |
| 8 | 0.971 | 0.976, 0.980, 0.951, 0.978, 0.981 | **0.973** | 0.951-0.981 | 0.771 | ≥ 0.9995 |
| 9 | 0.979 | 0.900, 0.981, 0.981, 0.987, 0.982 | **0.968** (corr. 3 Oct: as plotted; seeds stored to 3 decimals, exact value 0.9684-0.9687) | 0.900-0.987 | 0.780 | ≥ 0.9995 |
| 10 | 0.970 | 0.927, 0.933, 0.934, 0.987, 0.982 | **0.955** | 0.927-0.987 | 0.790 | ≥ 0.9995 |

## 5. Mechanisms

- **Dirty- and clean-profiled: identical in every run.** Their profiles hold only "not a missing
  token" and "is a number" per column; the profiler builds no ranges and no value sets on
  numeric columns.
  - **Knob 1:** they catch every blank and no outlier. P = 1 and R = the blank share
    (0.167-0.175), so F1 is 0.286-0.298.
  - **Knob 2:** they detect nothing (as is: only the 13 values in scientific notation).
  - **FG1:** in knob 1 it falls from 0.975 to 0.056; the baseline overtakes F1 ≈ 0.29 at π ≈ 17 %.
- **Hand-written: precision 1 in all 16 main runs, by construction.**
  - Every clean nasa value satisfies its regexes, so whatever it flags is an injected error. A
    false positive is impossible under any injection; precision 1 is not a test result.
  - Its bounds are close to the clean ranges for angle (0-22.x vs 0-22.2) and velocity (31-72.x
    vs 31.7-71.3). They are loose for chord and thickness ("below 1", clean maxima 0.3048 and
    0.0584) and frequency (3-5 digits, clean 200-20 000).
  - **Knob 1:** it catches every blank and the outliers that break a bound. That share depends
    on the spread, not on the rate, so F1 is flat.
  - **Knob 2:** recall rises from 26 % to 65 % (77 % of that rise by degree 5).
  - **Two blind spots.** First, new values inside the clean range: at degree 1, 1 514 of 2 247
    injected values. Second, values outside the clean range but inside its loose bounds (e.g.
    at degree 10: chord 0.7105, thickness 0.204625, frequency 31692.0). A third, small group: values equal to an existing clean value (43 at degree 1, 9 at degree 10; corr. 3 Oct). The second grows with k: 103 of 1 660
    misses at degree 1, 419 of 783 at degree 10.
- **HoloClean: FG1 below 0.5 in every run.**
  - **What it flags.** For every violated FD it flags the FD's own attribute cells: angle, chord,
    velocity, thickness and the label sound_pressure_level. Frequency is in none of the 4 DCs and
    is never flagged (corr. 3 Oct: FDX did learn an FD with frequency as right-hand side, but
    `fds_to_dcs.py` dropped it because its left-hand side contains the near-unique label; the
    filter checks only left-hand sides, so DC4, with the label as right-hand side, was kept), which puts 20 % of the injected outliers out of reach. The never-corrupted label is
    flagged 286-1 429 times per run, all false positives (knob 2: 369-375).
  - **Why it stays low.** Applied to the clean table, its 4 DCs already flag 7 515 of 9 018 cells.
    That is every cell of the five DC columns, and the fourth DC alone does it: its right-hand
    side is the label sound_pressure_level, with 1 456 distinct values in 1 503 rows, so every
    group of two or more rows violates it. Per DC on the clean table: 844, 4 509, 0 and 7 515
    cells.
    - So its low FG1 is a property of this DC set as much as of HoloClean.
    - Because the clean table already saturates these columns, injected values can only break
      groups apart. HoloClean therefore flags fewer cells as the data get dirtier (7 339 at 1 %,
      4 068 at 29 %).
    - Precision stays near the error rate (P/π 0.76-1.02 over the 16 main runs; knob 1: 0.76-0.96, below 1 at every rate), and most of its knob-1 rise in F1 comes
      from the data getting dirtier.
  - **Why the generator variant matters.** With the as-is generator, every injected value is
    unique, so HoloClean flags exactly the same cells at every degree (F1 0.223, FG1 < 0). With
    our rewriting, injected values written at a column's own precision often equal *each other*:
    at degree 1, 568 tie cells (angle 298, velocity 200, chord 54, frequency 16). Ties in FD
    columns create new FD groups and new flags, a majority of them true (degree 1, corr. 3 Oct: ties add 768 flags, 479 of them true; versus the as-is file 782 extra flags,
    483 true). Ties become rarer as k grows, so its knob-2 F1 falls (0.339 → 0.252). In knob 1
    they grow with the rate and account for about 0.03-0.05 of its top-level F1.
  - **Evidence.** Replicating its detection from the 4 DCs reproduces detections.csv exactly
    (`holo_replicate.py`). Removing all ties restores the as-is F1 (degree 1: 0.339; existing-value
    ties removed 0.328; injected-injected ties removed 0.238; all removed 0.223).
- **Raha: what it learns is not isolated.**
  - **Knob 1, 1-2 %.** Raha's cluster sampling labels 3-6 dirty tuples (3-7 error cells, at most
    1 blank) out of 20, against 8-11 dirty tuples (10-17 error cells) at 5 % and
    10-20 at higher rates (`raha_labels.py`, which reproduces the seed-check
    F1 exactly). Most of these draws are recall-limited (P = 1). The worst 1 % draw is a
    precision collapse (P 0.29, R 0.39); the worst 2 % draw fails on both (P 0.48, R 0.16) and has
    the fewest labelled errors of the seeded 2 % draws (3 dirty tuples; corr. 3 Oct). Two 1 % draws
    with the same label count scored 0.57 and 0.33; at 2 %, draws with 5 dirty tuples scored 0.83
    and 0.63, with 6 tuples 0.87 and 0.62.
    - At 1-2 % the labelled errors cover 2-4 of the 5 columns, from 5 % always all 5. A column
      without a labelled error gets no detections: with no positive label, Raha predicts every
      cell of the column clean (corr. 3 Oct, was "few").
    - Label counts overlap across the step: a 2 % draw with 6 dirty tuples scored 0.870, a 5 % draw
      with 9 scored 0.855.
    - So the step between 2 % and 5 % is consistent with label scarcity (fewer dirty tuples, fewer
      columns covered), but no experiment varied the labels. It does not explain the spread within
      a level.
  - **Knob 2.** No single strategy explains its F1. The best single strategy per column reaches
    0.46-0.56 at degree 1, at most 0.72 at degree 5 and 0.88 (velocity) at degree 10. Raha's
    combined average is 0.83-0.97.
  - **What it catches (degree 1, campaign run):**
    - 99 % of the negative values;
    - 77 % of the new values inside the clean range;
    - 80 % of the new non-negative values outside it;
    - 28 % of the 43 values that equal an existing clean value. These are almost all in angle,
      Raha's weakest column, so this contrast is confounded by column.

    Corr. 3 Oct: within angle, which holds 41 of the 43 existing-value cases, new non-negative
    values are caught about as rarely as existing ones (31 % vs 29 %), and within every column
    Raha catches new in-range values about equally often whether or not their digits or length
    are unseen in the clean column (e.g. velocity 61 % vs 57 %, chord 86 % vs 91 %). The best
    single strategies at degree 1 are dBoost OD in 3 columns and PVD in 2 (velocity, chord), none
    above 0.56. So the data do not support the hypothesis within a column.
    Which strategies drive which column was not ablated. The data fit "Raha flags values new to
    the column", but do not prove it.

## 6. Predictions and how they held

Timing:

- **Knob 1** was predicted on 30 Sep (Appendix A.1), for degree 3 and REIN's
  generator as is, after an injection probe and one test run. The test run (hand-written at
  9.9 %) is itself a campaign point.
- **Knob 2** was predicted on 2 Oct at 17:55 (Appendix A.2), for
  both REIN's generator as is and the formatted v1 variant, after one injection probe.
  - Already known at that time: the knob-1 as-is and rounding results at degrees 3 and 4,
    their Raha seed checks and the fingerprint diagnosis. Several knob-2 predictions carry these
    over.
  - Not yet known: the knob-1 v1 runs, which started seconds later.
- **The main protocol (`--write_like_clean`) came after all of these**: after the as-is runs, the
  v1 runs, their seed checks and the first refutation pass.

The verdicts below apply the predictions to the main protocol, with the predicted condition
noted where it differs.

| prediction | outcome on the main protocol |
|---|---|
| K1: profiled suites identical and flat, F1 ≈ 0.29 | held (0.286-0.298; largely known from the probe) |
| K1: hand-written flat, P = 1, R ≈ 0.55-0.60, F1 ≈ 0.72 | partly: flat held (P = 1 is guaranteed by construction, not tested); recall in band at 3 of 6 levels at two decimals (strictly only 0.595 at 9.86 %; corr. 3 Oct); F1 0.71-0.77 (at degree 3, as is: missed at 1 %) |
| K1: HoloClean F1 rises with the rate | held (0.018 → 0.334); not predicted: FG1 < 0.5 throughout |
| K1: Raha rises, lowest and most variable at 1-2 %, because the 20 labelled tuples hold "one or two dirty ones" at 1 % | partly: lowest and most variable at 1-2 % held; the "rise" is one step between 2 % and 5 % (averages 0.60, 0.62, 0.90, 0.97, 0.95, 0.96; corr. 3 Oct). The stated mechanism missed: Raha's sampling labels 3-6 dirty tuples at 1 %. On the as-is generator at degree 4, Raha's average is near 1 from 5 % (0.92 at 2 %; corr. 3 Oct, was "pinned near 1 from 2 %"); the predicted condition, degree 3, is not kept |
| K1: FG1 "falls slightly" where F1 is flat | did not hold for the profiled suites (0.975 → 0.056) |
| K1: the handoff's "dirty-profiled degrades with the rate", which our §1 rejected | our rejection held: the two profiled suites are identical |
| K2: profiled suites F1 ≈ 0 | held (no detections; as is < 0.005) |
| K2: hand-written P = 1, rising steadily with no plateau, as is ≈ rewritten | partly: rising and as is ≈ rewritten held (P = 1 by construction); "steady, no plateau" did not (flattening: gains shrink from +266 to +27-30 cells per degree, with one 3-cell uptick at 9→10; 77 % of the recall rise by degree 5; corr. 3 Oct, was "concave") |
| K2: HoloClean flat in the degree | held as is (identical detections); did not hold on the main protocol (0.339 → 0.252, ties) |
| K2: Raha as is ≈ 1.0 at every degree | held (F1 ≥ 0.9995 in 60 of 60 draws) |
| K2: Raha rising, lowest at degree 1 (predicted for v1) | held (averages 0.83 → 0.94-0.97; not monotone) |
| K2: Raha close to 1 from degree 3-4 | missed (averages 0.907, 0.938; ≥ 0.97 only at degrees 7-8) |
| K2: REIN's pattern, all detectors similar below degree 2 | did not hold: Raha 0.83 vs hand-written 0.41 at degree 1; the cause is not established |

## 7. Differences from REIN and threats to validity

- **Our own generator change.** Rewriting the injected values is our post-hoc decision.
  - It changes values slightly and changes HoloClean's result (ties), not only Raha's.
  - It cannot remove the string-level visibility of new values on small value sets (§2.3).
  - Raha's 1-2 % result depends on the draw. Six-run averages at 1 % / 2 % are below the
    hand-written suite (0.71 / 0.77) for every fingerprint-free variant tried: rounding 0.590 /
    0.708 and v1 0.450 / 0.762 (both deleted 3 Oct), main 0.600 / 0.623. Single runs are not: 3 of the 12 main-protocol
    runs beat it. On REIN's unchanged generator the averages are above it (0.822 / 0.924).
- **REIN's own Fig. 3.**
  - Smart Factory's clean values are short integers, so REIN's generator would leave the same
    fingerprint there.
  - Yet REIN reports Raha similar to the other detectors below degree 2 and improving only above
    it. That is not what a fingerprint-driven Raha does on nasa (≈ 1 at every degree).
  - Corr. 3 Oct: the candidate below does NOT explain Fig. 3c. Followed through REIN's upstream
    code, the same column shift also breaks REIN's own scoring (positional int(float())
    comparison, about 86 % 'errors'), so it would predict a high, flat Raha, not Fig. 3c's
    pattern. Keep it out of the thesis (it also touches the Raha label-oracle issue the thesis
    does not discuss).
  - One candidate difference is visible in REIN's code, but was not run. Smart Factory's label
    column is the first column of clean.csv. `inject_errors` drops it and appends it at the end,
    and the float noise writes untouched integers as "x.0". Raha labels by comparing dirty.csv
    and clean.csv position by position, so in REIN's loop it would see almost every cell as an
    error and train on broken labels. We restore the column order (§1), so this does not happen
    here.
  - Either way, we cannot tell from the paper why REIN's Raha behaves differently.
- **Dataset and draws.** nasa only, one dirty file per point. Raha has six draws per point;
  HoloClean is one run but deterministic.
- **Raha's budget.** Raha uses its default 20 labelled tuples with perfect labels. The 1-2 %
  result is specific to that budget.
- **HoloClean's DCs** are nasa's 4 FDs as learned by FDX, kept fixed at every level. One of them
  has the near-unique label as its right-hand side, so they flag 83 % of the clean table. A
  different DC set could behave very differently.
- **Hand-written suite.** We wrote its bounds ourselves, and every clean value satisfies them, so
  its precision of 1 is built in. Its recall depends on how tight the bounds are: close for angle
  and velocity, loose for chord, thickness and frequency.
- **Degree and levels.**
  - Degree 4 follows the paper, while REIN's code uses 3. Degree 3 was run only with the as-is
    generator and the 30 Sep rounding (deleted 3 Oct); there the GE and HoloClean conclusions
    were the same.
  - The degree is a noise spread.
  - Knob-1 levels are rates asked of REIN's generator, which delivers about half; the plots use
    measured rates.
- **FG1** is clipped to 0 in the figures (negative or undefined values).
  - The main-protocol tables show the true values.
  - The as-is panels hide HoloClean's knob-2 FG1 of −0.164 (F1 0.223 < π 0.25) and the profiled
    suites' negative as-is values (cell_FG1 in results.csv).

## 8. Files

- **Driver:** `scripts/robustness_driver.py` (`--write_like_clean`, `--outlier_degree_mode`;
  `--out` is required).
- **Run scripts:** `reports/robustness/{run_all.sh, run_knob2.sh}`.
- **Results and checks:** `reports/robustness/{results.csv, mechanism.csv, mechanism.py, plot.py,
  holo_replicate.py, raha_seed_check.py, raha_strategy_check.py, raha_labels.py,
  raha_seed_check_cleanstyle.txt, raha_seed_check_asis.txt, raha_strategy_check_cleanstyle.txt,
  raha_strategy_check_asis.txt, raha_labels_cleanstyle.txt}`.
- **Figures:** `fig_robustness_error_rate_d4_cleanstyle.*`, `fig_robustness_error_rate_d4_asis_cleanstyle.*`,
  `fig_robustness_outlier_degree_cleanstyle.*`, `fig_robustness_outlier_degree_asis_cleanstyle.*`.
- **Kept run folders:**
  - `runs/nasa_e*c_d4_*` and `runs/nasa_o*c_*` (main protocol);
  - `runs/nasa_e*_d4_*` and `runs/nasa_o<k>_*` without a letter (REIN's generator as is).
- **Modes in results.csv** (160 rows):
  - `error_rate_cleanstyle` and `outlier_degree_cleanstyle`: main protocol;
  - `error_rate` (degree 4) and `outlier_degree`: REIN's generator as is.

## Appendix: the predictions as written

Copied word for word from the deleted reports, so that §6 can be checked.
- The "formatted variant" in A.2 is `format_like_clean` (v1).
- A.1's "15 DCs" is a slip: HoloClean has 4 DCs, and 15 was the line count of the constraints
  file.

### A.1 Knob 1 prediction (written 2026-09-30 BEFORE the campaign)

Written after reading the code and after one test run (hand-written suite at the 10 % level:
P 1.000, R 0.566, F1 0.723), but before any other configuration or level was run.

REIN's generator produces only two kinds of error on nasa: numeric outliers (value + noise of
spread 3·σ_col) and blank cells, about 83 % / 17 % of the injected cells at every level. That
fixes what each suite can see:

- **Dirty-profiled and clean-profiled suites: identical to each other and flat.** Both profiles
  contain only "not a missing token" and "is a number" (`^-?\d+(\.\d+)?$`) on every column,
  because every non-blank value in both the clean and the injected files parses as a number; no
  ranges, no value sets. So both catch the blanks (plus the rare outlier printed in scientific
  notation) and no ordinary outlier: P ≈ 1, R ≈ 0.17, F1 ≈ 0.29 at every level. The handoff's
  expectation that the dirty-profiled suite degrades with the error rate does not apply here: the
  profiler never learns ranges, so there is nothing for extra dirt to spoil.
- **Hand-written suite: flat, and the best of the three GE suites.** Its regexes encode ranges
  (angle 0-22, velocity 31-72, thickness and chord below 1, frequency 3-5 digits), so it catches
  every blank plus the outliers that leave those ranges. That share is set by the noise spread
  (degree 3), not by the rate, so R ≈ 0.55-0.60, P = 1, F1 ≈ 0.72 at every level.
- **HoloClean: F1 rises with the rate.** Its DCs (15, from FDs learned on clean nasa) flag cells
  of tuples that violate them; more dirty tuples means a larger share of the flagged cells is
  really wrong, so precision (and F1) grow with the rate while staying well below the
  hand-written suite at low rates.
- **Raha: F1 rises with the rate.** Its 20 labelled tuples contain more dirty cells as the rate
  grows (at 1 % only about 6 % of the tuples are dirty, so the 20 labelled tuples hold one or two
  dirty ones), so the classifiers have more positive examples. Lowest and most variable at 1-2 %.

FG1 note: the always-positive baseline π equals the real error rate, so the same F1 is worth
less FG1 at a higher rate; FG1 curves will fall slightly where F1 is flat.

### A.2 Knob 2 prediction (written 2026-10-02 17:55, BEFORE any knob-2 detector run)

Already seen when this was written: the code (`run_robustness_exp` injects outliers only, at a
fixed asked rate of 30 %, degrees 1-10), and one injection probe of the formatted variant. The
probe showed a measured rate of 24.9-25.0 %, about 2 250 changed cells, no blanks, and the label
untouched. No detector had been run on a knob-2 file.

On nasa, an outlier is value + N(0, (k·σ_col)²). Every degree hits the same cells with the same
draws, so only the spread k changes.

- **Dirty-profiled and clean-profiled: F1 ≈ 0 at every degree.** They can only catch blanks,
  and this mode injects none. As is, they may catch the odd outlier printed in scientific
  notation. In the formatted variant they make no detections at all (F1 0, FG1 0).
- **Hand-written: P = 1, recall rising with the degree.** A bigger spread pushes more values
  out of its ranges (angle 0-22, velocity 31-72, thickness and chord below 1, frequency 3-5
  digits). It should be low at degree 1 (most jumps stay within range) and climb steadily, with
  no plateau before degree 10. As and formatted should be nearly identical, because its regexes
  bound ranges, not decimals.
- **HoloClean: flat in the degree, FG1 below 0.5.** Its constraints see only *whether* a value
  differs (knob 1: identical detections at degrees 3 and 4), and the same cells change at every
  degree. So its F1 should not move with k, apart from the few degree-1 outliers that the
  formatting rounds back to their clean value.
- **Raha as is: ≈ 1.0 at every degree, including degree 1.** The 14-20-digit fingerprint does
  not depend on the size of the jump.
- **Raha formatted: rising with the degree.** It should be lowest at degree 1, where many
  injected values stay inside the column's normal range and keep its format, and close to 1 from
  roughly degree 3-4. That would be REIN's pattern ("all detectors behave approximately the same
  below two, Raha improves beyond two").
- **FG1 baseline:** π ≈ 0.25 at every degree, so the always-positive baseline sits at F1 = 2π/(1+π)
  ≈ 0.40. A detector needs F1 above that to reach FG1 > 0.5.
