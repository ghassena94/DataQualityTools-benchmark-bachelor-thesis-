# Scalability campaign, 26–30 September 2026 (thesis §5.2.6)

Self-contained record of the scalability experiment: design, environment,
every result, the commands that produced them, and how to recreate the
figure. Written by the session "Thesis Performance evaluation section" so
that another session can rebuild the figures without it. Updated 30 Sep
2026 by the session "scalability plots": the 2 h time limit was removed,
mercedes Raha was re-run without it (40 % finishes, 50 % is OOM-killed),
and the figures were redrawn. §8 lists every change.

## 1. What was measured and why

REIN's own scalability test (paper §6.2.2, Fig. 3d/3e) runs ten detectors on
data fractions of one dataset (Soccer) and records F1 and runtime, noting
where a detector stops working. Our two excluded datasets fail Raha for two different
reasons (mercedes: 378 columns, strategy profiling; har: 70 000 rows,
clustering), so we measure two axes:

| axis | dataset | fractions | why this dataset |
|---|---|---|---|
| rows | har (70 000 × 5) | 10, 20, …, 100 % of the rows | Raha's row-driven failure (OOM at 100 %) |
| rows | adult (45 222 × 15) | 20, 40, 60, 80, 100 % | the largest evaluation dataset, and HoloClean has constraints on it; Raha finishes at 100 % |
| columns | mercedes (4 209 × 378) | 10, 20, …, 100 % of the columns | Raha's column-driven failure (OOM at 100 %) |

Five configurations on every fraction: GE dirty-profiled (`dirty_profiled`
tier, called `generic` before 27 Sep), GE clean-profiled (`clean_profiled`,
was `oracle`), GE hand-written (`hand_written`, was `domain`), HoloClean,
Raha.
Per run we record cell precision/recall/F1/FG1, TP/FP/FN, number of
detections, the detector's own runtime (`detection_runtime` from the
benchmark), a wall time (two definitions, see §5 note a), and the
container's peak memory.
For HoloClean the PostgreSQL container's memory was sampled every 5 s from
the host (`docker stats`) and its maximum recorded.

Rules of the campaign:
- One fresh container per run, so `/sys/fs/cgroup/memory.peak` read at the
  end of the run is the peak of exactly that run, worker processes included.
- Raha always runs cold (fresh strategies, no cache), because the fraction is
  a new table.
- No time limit per run. A run ends only when it finishes, is OOM-killed or
  raises an error. This follows REIN, which reports no time limit (§6.2.2
  names none, and its Raha, ED2 and KATARA averaged 3.5, 10.1 and 13.8 h;
  that HoloClean "is terminated" at 90 % is not explained). A configuration
  that fails at one fraction is not run at larger fractions; those rows
  carry status `skipped`.
- History of the limit: the first campaign (26–27 Sep) ran with a 2 h cap
  (`timeout 7200`). It was not a REIN value and no documented decision; it
  came from a planning suggestion in another session. It cut exactly one run
  (mercedes 40 % Raha), which was re-run without a cap on 29–30 Sep (§2).
  The cap was removed on 29 Sep. Every other run finished below it
  (longest: mercedes 30 % Raha, 4 591 s, 64 % of the cap; next har 90 %
  Raha, 3 109 s), so no other measured result depends on it. The mercedes
  60–100 % Raha `skipped` rows still date from the capped run (27 Sep
  04:48:50, "failed at 0.4"); they remain correct because 50 % is now
  OOM-killed.
- Fractions are nested: one permutation with seed 42 per axis, the first
  round(fraction × n) rows/columns kept in their original order; 100 % is the
  full table.
- Quality is reported as FG1; F1 is kept in the tables. The figures show a
  negative or undefined FG1 in two bands below the FG1 axis ("< 0",
  "undefined"), never as 0 (§7).

## 2. Environment

- Docker Desktop VM: 31.29 GiB memory (= 33.6 GB), 10 CPUs; kernel
  6.12.67-linuxkit; container image of the repo (`docker compose`, service
  `rein`, db container `rein-benchmark-db-1` up).
- Campaign timing: GE and HoloClean 26 Sep 21:27–22:06 (two helper runners
  in parallel for redone mercedes fractions); Raha 26 Sep 21:52 → paused
  22:20 (laptop moved) → resumed 22:36 → finished 27 Sep 04:49. Runs are
  never concurrent on the same dataset during the Raha phase.
- Re-runs without the time limit (mercedes Raha, one run at a time, Docker
  otherwise idle): 40 % on 29 Sep 16:42 → 22:42 (the runner, stopped by
  SIGTTIN, only logged it at 23:21 after `kill -CONT`, see §4), during which
  the Mac slept 19:27–22:32, so its runtime is unusable (row kept in
  `backup/`, see §3);
  50 % on 29 Sep 23:21 → 30 Sep 04:10, OOM-killed, no sleep; clean 40 %
  re-run on 30 Sep 04:11 → 06:44, no sleep, swapped into `results.csv`.
- Sleep: a Mac sleep during a run inflates `runtime_s` and `wall_s` but
  leaves F1 unchanged and peak memory within 0.2 GB (mercedes 40 %: F1, TP,
  FP, FN identical; 32.87 GB slept vs 33.04 GB clean). Subtracting the sleep periods from
  `pmset -g log` was tried on the slept 40 % run and overstated the clean
  runtime by 16 % (10 551 s vs 9 132 s), so a slept run is re-run, never
  corrected. On battery with the lid closed, `caffeinate` cannot prevent
  sleep: keep the Mac on power with the lid open.
- Every container carries an interpreter floor of about 0.65 GB (Python,
  pandas, datawig, torch, …) that is the same for all configurations; the
  figure draws it as a dotted line rather than subtracting it.

## 3. Files (all under `reports/scalability/`)

| file | content |
|---|---|
| `results.csv` | one row per run (125 rows, one per dataset × axis × fraction × configuration); columns: dataset, axis, fraction, rows, cols, detector, tier, status, precision, recall, f1, cell_TP, cell_FP, cell_FN, cell_FG1, detections, runtime_s, wall_s, peak_mem_bytes, baseline_mem_bytes, scratch, timestamp. `status` ∈ ok, oom_killed, skipped (the only `timeout` row, mercedes 40 % Raha, was replaced by the re-run). `baseline_mem_bytes` is the cgroup peak before the benchmark was imported. Rows are not in plan order (re-runs are appended). md5 on 30 Sep 2026: 627034d1f71009e86d697f25e1b8dd73 |
| `db_mem.csv` | dataset, axis, fraction, detector, tier, max PostgreSQL-container memory in bytes sampled during the run (only meaningful for HoloClean). Appended per runner run, so mercedes 40 % Raha has two entries (27 Sep timeout: 0.03 GB; 29 Sep slept run: 0, no successful sample); the clean 30 Sep re-run ran outside the runner and has none |
| `run_all.log` | the runner's log: start/end of every run, failures with the last stderr line, skips. The clean 40 % re-run is not in it (see `rerun_mercedes_c40_raha.csv` and its detection log) |
| `run_all.py` | host-side runner: plan, skip rule, db sampler, optional time limit `TIMEOUT_S` (now `None`); filters `[detector …] --dataset DS --fraction F --dry-run` |
| `progress.py` | live progress table used during the campaign |
| `plot.py` | the combined figure script (reads results.csv, writes fig_scalability.pdf/png) |
| `fig_scalability.pdf`, `fig_scalability.png` | the combined figure: 3 × 3 panels, rows = FG1 / cold runtime (log) / peak memory, columns = har rows / adult rows / mercedes columns |
| `plot_panels.py` | writes each of the nine panels as its own figure; same data rules as `plot.py` |
| `panels/` | `<metric>_<dataset>_<axis>.pdf/.png`, metric ∈ fg1, runtime, memory (e.g. `runtime_mercedes_cols.pdf`) |
| `rerun_mercedes_c40_raha.csv` | the clean 40 % re-run's own output row (30 Sep), identical to the row now in `results.csv` |
| `backup/` | before the campaign: `results/detection_results.csv` of adult, har, mercedes and nasa (the campaign never touched them; they changed later only through the 27 Sep tier rename and, for adult, the 28–29 Sep Raha re-run and clean-up). Later: `results.before_mercedes_c40_nocap_20260929.csv`, `results.before_mercedes_c50_20260929.csv`, `results.before_mercedes_c40_rerun_swap_20260930.csv` (results.csv before each change), `mercedes_c40_raha_slept_run_20260929.csv` (the slept 40 % row), `figures_2h_cap_20260927/` (figures drawn with the cap). Other `*_detection_results_*` files there belong to the adult/smartfactory Raha cache fixes, not to this campaign |

The driver itself is `scripts/scalability_driver.py` (repo root). The
original datasets under `rein-datasets/` were never modified: every run
worked on a scratch copy `rein-datasets/<ds>_<r|c><pct>_<detector>[_<tier>]`
that was registered in `datasets_dictionary` and `DATASET_EXPECTATIONS` at
runtime and deleted afterwards. The driver also drops `dirty_<scratch>` /
`ground_truth_<scratch>` in the `rein` database, but those tables are never
created: the benchmark's insert fails inside the container (its engine
points at localhost) and the error is ignored ("Unable to insert the
datasets into the REIN database" in every log). HoloClean's own working
tables for each scratch copy stay in the `holo` database (25 after the
campaign, e.g. `adult_r20`, `mercedes_c90_holoclean`); the driver does not
remove them.

## 4. Commands

Every driver command appends a row to `results.csv` unless `--out` names
another file; a duplicate row would silently replace the campaign's row in
the figures (the plot scripts keep the last row per fraction). So test
runs always get `--out`.

Smoke test of the driver (seconds). It works on a scratch copy and writes
its row to a file inside the container that disappears with it; to check
that the originals stay untouched, compare checksums before and after:

```bash
md5 rein-datasets/nasa/*.csv
```

```bash
docker compose run --rm -T rein python3 scripts/scalability_driver.py --dataset nasa --axis rows --fraction 0.1 --detector greatExpectations --tier hand_written --out /tmp/smoke.csv
```

Use the tier names `dirty_profiled`, `clean_profiled`, `hand_written`;
nothing validates them. Any other name, including the old `generic`,
`oracle` and `domain` and any typo, silently runs the hand-written suite
and is recorded under the name given, so `generic`/`oracle` do not give the
profiled suites.

One run by hand (what the runner executes, so it appends to `results.csv`;
`EXPECTATION_TIER` only matters for greatExpectations; no `timeout` wrapper
since 29 Sep):

```bash
docker compose run --rm -T -e EXPECTATION_TIER=hand_written rein python3 scripts/scalability_driver.py --dataset har --axis rows --fraction 0.5 --detector raha
```

The same with its own output file instead of `results.csv` (the clean
mercedes 40 % re-run on 30 Sep wrote `rerun_mercedes_c40_raha.csv` this
way; command reconstructed from the driver's options, not copied from a
log):

```bash
docker compose run --rm -T rein python3 scripts/scalability_driver.py --dataset mercedes --axis cols --fraction 0.4 --detector raha --out reports/scalability/rerun_mercedes_c40_raha.csv < /dev/null
```

The whole campaign. Runs with an `ok` row are skipped, but failed runs are
retried: on today's `results.csv` it would re-launch har 100 % and mercedes
50 % Raha (both OOM-killed, the latter after 4 h 49 min) and append
duplicate `oom_killed` and `skipped` rows. Check with `--dry-run` first and
restrict it with the filters below. Always launch the runner with
`< /dev/null`: started in the background from a shell, it otherwise leaves
`docker compose run` stopped by SIGTTIN (`docker compose run` keeps STDIN
open by default, and the service also sets `stdin_open: true`); the
container still finishes and writes its row, but the runner hangs until
`kill -CONT` (29 Sep: 39 min between the container's end and the runner's
`ok`).

```bash
docker compose up -d db && nohup python3 reports/scalability/run_all.py < /dev/null > /dev/null 2>&1 &
```

Restrict the plan by detector, dataset and fraction. `caffeinate` holds its
no-sleep assertions exactly as long as the runner lives, but it cannot stop
lid-close sleep on battery: the 29 Sep mercedes 40 % run was launched this
way and still slept 19:27–22:32 (§2), so keep the Mac on power with the lid
open. That run was also launched without `< /dev/null`, which is how the
hang above was found:

```bash
nohup caffeinate -dims python3 reports/scalability/run_all.py raha --dataset mercedes --fraction 0.4 < /dev/null > /dev/null 2>&1 &
```

See what a filter would start, without running or logging anything:

```bash
python3 reports/scalability/run_all.py raha --dataset mercedes --dry-run
```

Live progress (refreshes every 30 s):

```bash
while true; do clear; python3 reports/scalability/progress.py; sleep 30; done
```

Pause (kill the runner and its container, remove the scratch copy of the
interrupted run; the interrupted run leaves no row and is redone on resume):

```bash
pkill -f reports/scalability/run_all.py; docker ps --format '{{.Names}}' | grep rein-run | xargs -r docker kill; find rein-datasets -maxdepth 1 -type d \( -name '*_r[0-9]*' -o -name '*_c[0-9]*' \) -exec rm -rf {} +
```

Keep the Mac awake while it runs (a sleep in the middle of a run inflates
that run's time; keep it on power with the lid open, see §2):

```bash
caffeinate -dims
```

Recreate the combined figure (matplotlib is in the container, not on the
host):

```bash
docker compose run --rm -T rein python3 reports/scalability/plot.py
```

Recreate the nine standalone panels, or only some of them:

```bash
docker compose run --rm -T rein python3 reports/scalability/plot_panels.py
```

```bash
docker compose run --rm -T rein python3 reports/scalability/plot_panels.py --metric runtime memory --dataset mercedes
```

Clean-up after a killed run. Scratch directories: use the `find … -exec rm
-rf {} +` part of the Pause command above. Postgres: the runs create no
tables in the `rein` database (see §3), so there is nothing to drop there.
HoloClean's working tables stay in the `holo` database; list them with:

```bash
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d holo -At -c "select tablename from pg_tables where schemaname = '"'"'public'"'"' and tablename ~ '"'"'_(r|c)[0-9]+'"'"' order by 1"'
```

(The earlier clean-up command here, via `Database().remove_table_postgres`,
did nothing: it looked in the `rein` database, where no such table exists,
and its engine points at localhost, which is unreachable inside the
container.)

## 5. Results

Summary of the failure points and the cost curves (full tables in §6):

| configuration | har rows | adult rows | mercedes columns |
|---|---|---|---|
| GE (all three suites) | finishes everywhere; runtime 0.02–0.27 s, linear in rows; memory flat ≈ 0.66–0.70 GB | finishes; 0.06–0.36 s; ≈ 0.66–0.70 GB | finishes; 0.1–5 s, roughly linear in columns for the profiled suites (hand-written non-monotone, 0.12–2.43 s); 0.66–0.87 GB |
| HoloClean | finishes (no constraints on har: 0 detections); 0.1–0.9 s | finishes; 5.1 → 25.9 s linear; container 0.81 → 1.35 GB, db container 0.06 → 0.13 GB; FG1 0.50 at every fraction (flags 96–98 % of all cells) | finishes (no constraints: 0 detections); 0.4–5.3 s |
| Raha | 10–90 % finish (F1 0.87–0.98); runtime 22, 51, 87, 129, 177, 244, 350, 948, 3 109 s; peak 2.3, 2.8, 4.9, 7.9, 11.6, 16.2, 21.6, 27.7, 32.9 GB; **100 % OOM-killed** after 335 s | finishes; 201, 429, 569, 886, 1 217 s; peak 4.1, 5.6, 10.1, 15.8, 23.2 GB; F1 0.30, 0.00, 0.27, 0.00, 0.23 (the 0.00s: see readings; note c) | 10–40 % finish (F1 0.999); 433, 1 704, 4 591, 9 132 s; peak 5.7, 11.5, 21.7, 33.0 GB; **50 % (189 columns) OOM-killed** after 17 357 s (4 h 49 min); 60–100 % skipped; 100 % is also the original OOM |

Readings:
- Quality does not depend on size for any configuration (all FG1 curves
  are flat), with one exception that is not a size effect either. **In one
  sentence:** Raha's FG1 on adult alternates between ≈ 0.99 and undefined
  (the "undefined" band in the figure) because each fraction is a different table and therefore
  gets a different sample of 20 labelled tuples, and since all adult errors
  sit in `income` in only 3.8 % of the rows (1 701 of 45 222), Raha either
  happens to label a dirty row and then finds between half and all of the
  errors with many false alarms (recall 0.51–0.99, F1 0.23–0.30, FG1 ≈ 0.99)
  or labels none and flags nothing (TP = FP = 0 at 40 % and 80 %).
  - Evidence: `raha/detection.py` (in the container) predicts "clean" for a
    whole column when all its labels are clean (lines 346–347) and always
    reports the dirty cells of its labelled tuples (line 366), so zero
    detections means none of the 20 labelled tuples was dirty. The sample is
    not random between runs: importing datawig seeds NumPy (42), which
    drives the tuple sampling (line 285), and Python's `random`, which
    drives the strategy shuffle of a cold run (line 187); the driver's
    fraction permutation uses a private `RandomState` and touches neither.
    A re-run should therefore reproduce its result. This was observed on
    the full table (the campaign's cold 100 % run on 26 Sep, the cold cache
    rebuild on 27–28 Sep and a cached re-run on 28 Sep all gave TP 865 /
    FP 5 081);
    the 20–80 % fractions were not re-run. A different draw usually finds
    errors: ten consecutive runs on the full table (28 Sep) found them 9
    times out of 10.
- Cost separates the tools by four orders of magnitude, with different
  shapes: GE linear and at the floor in memory; HoloClean linear in rows;
  Raha superlinear on both axes. Rows (har; clustering builds a pairwise
  distance matrix per column): runtime log-log slope 1.2–1.8 per step up
  to 60 %, then 2.4, 7.5 and 10.1; memory 1.3–1.9 per step from 20 %
  (approaching quadratic). Columns (mercedes; strategy profiling enumerates
  column pairs): runtime 2.0–2.5 per step, memory 1.0–1.6.
- Raha's ceiling at 31.3 GiB (33.6 GB) is between 63 000 and 70 000 rows × 5
  columns (32.9 GB survives, 70 000 rows killed) and between 151 and 189
  columns × 4 209 rows (33.0 GB survives in 2 h 32 min, 189 columns killed
  after 4 h 49 min). On har, runtime explodes before memory kills (80 → 90 %:
  948 s → 3 109 s, slope 10). On mercedes, runtime keeps its steady slope
  (30 → 40 %: 4 591 s → 9 132 s, slope 2.4) while memory reaches 33.0 GB,
  98 % of the limit, and the next step is OOM-killed.

Notes:
- (a) `runtime_s` is the benchmark's `detection_runtime` (detector only).
  For finished runs, `wall_s` is the driver's own time from after its
  imports and database connection to the end (data preparation, benchmark
  setup, detection, evaluation; container start-up excluded). For
  OOM-killed and timed-out rows it is the runner's host-side time for the
  whole `docker compose run`. Use `runtime_s` for the runtime panel.
- (b) Peak memory is the container's cgroup peak, floor ≈ 0.65 GB included.
  For HoloClean add the db-container column if a total is wanted.
- (c) The adult Raha points come from complete strategy caches computed
  fresh on each fraction. The thesis's adult Raha rows were first computed
  on a truncated cache (101 of the 513 strategy files, from an August
  session; see the memory note `raha-truncated-caches-adult-smartfactory`),
  which is why they showed 0–2 true positives while the 100 % run here shows
  865. Resolved 27–29 Sep: the cache was rebuilt (27–28 Sep), adult Raha
  re-run (28 Sep) and the old rows cleaned up (29 Sep); the corrected run 1 (TP 865, FP 5 081, F1 0.2262) equals this campaign's
  100 % point exactly.
- (d) mercedes lists its columns in a different order in clean.csv; the
  driver aligns the clean file onto the dirty column order by name (the
  benchmark's ground-truth oracle does the same). The first mercedes GE
  fractions failed before this fix and were redone; the failed rows were
  removed from results.csv.
- (e) Scratch names gained the detector/tier suffix during the campaign
  (after two runners collided on `mercedes_c90`); the `scratch` column shows
  both forms. The two affected HoloClean rows were redone.
- (f) All adult GE runs, all har/mercedes HoloClean runs and the adult
  Raha runs at 40 % and 80 % have undefined FG1 (TP = 0); the profiled GE
  suites on mercedes have strongly negative FG1 (−15 to −19: recall ≈ 0.006,
  far below the error rate ≈ 0.17–0.19, although precision is 1.0). The
  figures show the two cases in separate bands below the FG1 axis (§7). An
  undefined FG1 means "nothing to score", not "worse than chance".
- (g) The mercedes 40 % Raha row is the clean 30 Sep re-run (no sleep). The
  29 Sep run of the same fraction gave identical F1, TP, FP and FN and a
  peak of 32.9 GB, but its logged runtime (21 509 s) includes 3 h of sleep;
  it is kept only in `backup/mercedes_c40_raha_slept_run_20260929.csv`.

## 6. Full results (one table per configuration and axis)

### har, row fractions (70 000 rows x 5 columns)


**GE dirty-profiled**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 % | 7000 | 5 | ok | 1.0000 | 0.2044 | 0.3394 | 0.6593 | 1066 | 0 | 4149 | 1066 | 0.04 | 3.9 | 0.66 | 0.05 |
| 20 % | 14000 | 5 | ok | 1.0000 | 0.2025 | 0.3369 | 0.6569 | 2104 | 0 | 8284 | 2104 | 0.06 | 5.3 | 0.66 | 0.05 |
| 30 % | 21000 | 5 | ok | 1.0000 | 0.2012 | 0.3349 | 0.6565 | 3115 | 0 | 12370 | 3115 | 0.08 | 6.5 | 0.67 | 0.05 |
| 40 % | 28000 | 5 | ok | 1.0000 | 0.2026 | 0.3369 | 0.6583 | 4195 | 0 | 16514 | 4195 | 0.10 | 7.9 | 0.67 | 0.05 |
| 50 % | 35000 | 5 | ok | 1.0000 | 0.2030 | 0.3374 | 0.6594 | 5251 | 0 | 20620 | 5251 | 0.13 | 9.4 | 0.67 | 0.05 |
| 60 % | 42000 | 5 | ok | 1.0000 | 0.2029 | 0.3373 | 0.6592 | 6297 | 0 | 24743 | 6297 | 0.15 | 12.4 | 0.67 | 0.05 |
| 70 % | 49000 | 5 | ok | 1.0000 | 0.2021 | 0.3363 | 0.6579 | 7315 | 0 | 28877 | 7315 | 0.17 | 12.3 | 0.68 | 0.05 |
| 80 % | 56000 | 5 | ok | 1.0000 | 0.2012 | 0.3350 | 0.6561 | 8316 | 0 | 33022 | 8316 | 0.21 | 13.8 | 0.68 | 0.05 |
| 90 % | 63000 | 5 | ok | 1.0000 | 0.2024 | 0.3366 | 0.6578 | 9432 | 0 | 37172 | 9432 | 0.21 | 14.3 | 0.68 | 0.05 |
| 100 % | 70000 | 5 | ok | 1.0000 | 0.2026 | 0.3369 | 0.6577 | 10502 | 0 | 41343 | 10502 | 0.25 | 16.6 | 0.69 | 0.05 |

**GE clean-profiled**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 % | 7000 | 5 | ok | 1.0000 | 0.2176 | 0.3575 | 0.6853 | 1135 | 0 | 4080 | 1135 | 0.04 | 3.9 | 0.66 | 0.05 |
| 20 % | 14000 | 5 | ok | 1.0000 | 0.2148 | 0.3536 | 0.6814 | 2231 | 0 | 8157 | 2231 | 0.06 | 5.3 | 0.66 | 0.05 |
| 30 % | 21000 | 5 | ok | 1.0000 | 0.2138 | 0.3523 | 0.6820 | 3311 | 0 | 12174 | 3311 | 0.10 | 6.7 | 0.67 | 0.05 |
| 40 % | 28000 | 5 | ok | 1.0000 | 0.2151 | 0.3540 | 0.6832 | 4454 | 0 | 16255 | 4454 | 0.11 | 8.1 | 0.67 | 0.05 |
| 50 % | 35000 | 5 | ok | 1.0000 | 0.2155 | 0.3546 | 0.6842 | 5575 | 0 | 20296 | 5575 | 0.14 | 9.4 | 0.67 | 0.05 |
| 60 % | 42000 | 5 | ok | 1.0000 | 0.2159 | 0.3551 | 0.6851 | 6702 | 0 | 24338 | 6702 | 0.16 | 10.7 | 0.67 | 0.05 |
| 70 % | 49000 | 5 | ok | 1.0000 | 0.2149 | 0.3538 | 0.6834 | 7778 | 0 | 28414 | 7778 | 0.17 | 11.5 | 0.67 | 0.05 |
| 80 % | 56000 | 5 | ok | 1.0000 | 0.2140 | 0.3525 | 0.6819 | 8845 | 0 | 32493 | 8845 | 0.19 | 13.3 | 0.68 | 0.05 |
| 90 % | 63000 | 5 | ok | 1.0000 | 0.2149 | 0.3538 | 0.6829 | 10016 | 0 | 36588 | 10016 | 0.22 | 14.7 | 0.68 | 0.05 |
| 100 % | 70000 | 5 | ok | 1.0000 | 0.2149 | 0.3538 | 0.6824 | 11142 | 0 | 40703 | 11142 | 0.27 | 16.0 | 0.69 | 0.05 |

**GE hand-written**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 % | 7000 | 5 | ok | 1.0000 | 0.4324 | 0.6037 | 0.8851 | 2255 | 0 | 2960 | 2255 | 0.02 | 3.8 | 0.66 | 0.05 |
| 20 % | 14000 | 5 | ok | 1.0000 | 0.4310 | 0.6024 | 0.8850 | 4477 | 0 | 5911 | 4477 | 0.04 | 5.2 | 0.66 | 0.05 |
| 30 % | 21000 | 5 | ok | 1.0000 | 0.4335 | 0.6048 | 0.8870 | 6713 | 0 | 8772 | 6713 | 0.06 | 6.7 | 0.67 | 0.05 |
| 40 % | 28000 | 5 | ok | 1.0000 | 0.4344 | 0.6056 | 0.8870 | 8995 | 0 | 11714 | 8995 | 0.07 | 8.4 | 0.67 | 0.05 |
| 50 % | 35000 | 5 | ok | 1.0000 | 0.4333 | 0.6047 | 0.8866 | 11211 | 0 | 14660 | 11211 | 0.08 | 8.8 | 0.67 | 0.05 |
| 60 % | 42000 | 5 | ok | 1.0000 | 0.4316 | 0.6029 | 0.8858 | 13396 | 0 | 17644 | 13396 | 0.09 | 10.0 | 0.67 | 0.05 |
| 70 % | 49000 | 5 | ok | 1.0000 | 0.4303 | 0.6017 | 0.8853 | 15573 | 0 | 20619 | 15573 | 0.11 | 12.0 | 0.68 | 0.05 |
| 80 % | 56000 | 5 | ok | 1.0000 | 0.4298 | 0.6012 | 0.8851 | 17767 | 0 | 23571 | 17767 | 0.12 | 13.4 | 0.68 | 0.05 |
| 90 % | 63000 | 5 | ok | 1.0000 | 0.4313 | 0.6026 | 0.8855 | 20098 | 0 | 26506 | 20098 | 0.13 | 14.6 | 0.69 | 0.05 |
| 100 % | 70000 | 5 | ok | 1.0000 | 0.4321 | 0.6034 | 0.8857 | 22400 | 0 | 29445 | 22400 | 0.15 | 15.2 | 0.70 | 0.05 |

**HoloClean**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 % | 7000 | 5 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 5215 | 0 | 0.10 | 4.2 | 0.67 | 0.12 |
| 20 % | 14000 | 5 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 10388 | 0 | 0.18 | 5.5 | 0.68 | 0.12 |
| 30 % | 21000 | 5 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 15485 | 0 | 0.28 | 7.7 | 0.69 | 0.12 |
| 40 % | 28000 | 5 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 20709 | 0 | 0.36 | 8.5 | 0.70 | 0.13 |
| 50 % | 35000 | 5 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 25871 | 0 | 0.42 | 10.0 | 0.71 | 0.13 |
| 60 % | 42000 | 5 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 31040 | 0 | 0.48 | 11.2 | 0.72 | 0.14 |
| 70 % | 49000 | 5 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 36192 | 0 | 0.58 | 14.1 | 0.73 | 0.14 |
| 80 % | 56000 | 5 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 41338 | 0 | 0.66 | 14.5 | 0.74 | 0.14 |
| 90 % | 63000 | 5 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 46604 | 0 | 0.91 | 16.2 | 0.75 | 0.16 |
| 100 % | 70000 | 5 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 51845 | 0 | 0.93 | 17.7 | 0.77 | 0.15 |

**Raha**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 % | 7000 | 5 | ok | 0.9690 | 0.8805 | 0.9226 | 0.9853 | 4592 | 147 | 623 | 4739 | 21.82 | 25.8 | 2.33 | 0.21 |
| 20 % | 14000 | 5 | ok | 0.8695 | 0.8803 | 0.8749 | 0.9751 | 9145 | 1372 | 1243 | 10517 | 50.84 | 55.9 | 2.85 | 0.21 |
| 30 % | 21000 | 5 | ok | 0.9407 | 0.8128 | 0.8721 | 0.9746 | 12586 | 794 | 2899 | 13380 | 86.75 | 93.1 | 4.87 | 0.21 |
| 40 % | 28000 | 5 | ok | 0.9750 | 0.9788 | 0.9769 | 0.9959 | 20270 | 519 | 439 | 20789 | 128.59 | 136.2 | 7.89 | 0.21 |
| 50 % | 35000 | 5 | ok | 0.9484 | 0.9428 | 0.9456 | 0.9900 | 24391 | 1328 | 1480 | 25719 | 176.62 | 185.6 | 11.63 | 0.21 |
| 60 % | 42000 | 5 | ok | 0.9295 | 0.9453 | 0.9373 | 0.9884 | 29341 | 2227 | 1699 | 31568 | 243.75 | 254.1 | 16.15 | 0.21 |
| 70 % | 49000 | 5 | ok | 0.9320 | 0.9694 | 0.9503 | 0.9909 | 35084 | 2558 | 1108 | 37642 | 349.93 | 361.7 | 21.58 | 0.21 |
| 80 % | 56000 | 5 | ok | 0.9451 | 0.9784 | 0.9615 | 0.9931 | 40446 | 2351 | 892 | 42797 | 947.86 | 961.0 | 27.69 | 0.21 |
| 90 % | 63000 | 5 | ok | 0.9251 | 0.8377 | 0.8792 | 0.9761 | 39039 | 3162 | 7565 | 42201 | 3109.40 | 3124.5 | 32.95 | 0.21 |
| 100 % | | | **oom_killed** | | | | | | | | | | 335.1 |  | 0.03 |

### adult, row fractions (45 222 rows x 15 columns)


**GE dirty-profiled**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 % | 9044 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 356 | 0 | 0.08 | 7.8 | 0.66 | 0.05 |
| 40 % | 18089 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 671 | 0 | 0.15 | 12.6 | 0.67 | 0.05 |
| 60 % | 27133 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 1007 | 0 | 0.21 | 17.6 | 0.68 | 0.05 |
| 80 % | 36178 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 1336 | 0 | 0.28 | 22.5 | 0.69 | 0.05 |
| 100 % | 45222 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 1701 | 0 | 0.34 | 27.1 | 0.70 | 0.05 |

**GE clean-profiled**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 % | 9044 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 356 | 0 | 0.09 | 8.8 | 0.66 | 0.05 |
| 40 % | 18089 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 671 | 0 | 0.20 | 12.4 | 0.67 | 0.05 |
| 60 % | 27133 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 1007 | 0 | 0.23 | 18.2 | 0.68 | 0.05 |
| 80 % | 36178 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 1336 | 0 | 0.36 | 23.7 | 0.69 | 0.05 |
| 100 % | 45222 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 1701 | 0 | 0.33 | 27.9 | 0.70 | 0.05 |

**GE hand-written**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 % | 9044 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 356 | 0 | 0.06 | 8.1 | 0.66 | 0.05 |
| 40 % | 18089 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 671 | 0 | 0.13 | 13.6 | 0.67 | 0.05 |
| 60 % | 27133 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 1007 | 0 | 0.17 | 21.1 | 0.68 | 0.05 |
| 80 % | 36178 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 1336 | 0 | 0.20 | 24.5 | 0.69 | 0.05 |
| 100 % | 45222 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 1701 | 0 | 0.28 | 30.4 | 0.70 | 0.05 |

**HoloClean**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 % | 9044 | 15 | ok | 0.0026 | 0.9522 | 0.0052 | 0.4955 | 339 | 129978 | 17 | 130317 | 5.07 | 14.5 | 0.81 | 0.06 |
| 40 % | 18089 | 15 | ok | 0.0025 | 0.9762 | 0.0050 | 0.5025 | 655 | 262893 | 16 | 263548 | 10.12 | 26.7 | 0.96 | 0.08 |
| 60 % | 27133 | 15 | ok | 0.0025 | 0.9791 | 0.0050 | 0.5015 | 986 | 396316 | 21 | 397302 | 14.86 | 37.5 | 1.11 | 0.09 |
| 80 % | 36178 | 15 | ok | 0.0025 | 0.9828 | 0.0049 | 0.5020 | 1313 | 529878 | 23 | 531191 | 19.58 | 49.0 | 1.24 | 0.11 |
| 100 % | 45222 | 15 | ok | 0.0025 | 0.9859 | 0.0050 | 0.5026 | 1677 | 663530 | 24 | 665207 | 25.94 | 62.9 | 1.35 | 0.13 |

**Raha**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 % | 9044 | 15 | ok | 0.1792 | 0.9916 | 0.3035 | 0.9940 | 353 | 1617 | 3 | 1970 | 200.84 | 209.1 | 4.11 | 0.21 |
| 40 % | 18089 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 671 | 0 | 429.41 | 442.1 | 5.57 | 0.35 |
| 60 % | 27133 | 15 | ok | 0.1700 | 0.6326 | 0.2679 | 0.9932 | 637 | 3111 | 370 | 3748 | 569.46 | 586.0 | 10.15 | 0.21 |
| 80 % | 36178 | 15 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 1336 | 0 | 885.52 | 907.1 | 15.83 | 0.21 |
| 100 % | 45222 | 15 | ok | 0.1455 | 0.5085 | 0.2262 | 0.9914 | 865 | 5081 | 836 | 5946 | 1217.35 | 1244.2 | 23.16 | 0.21 |

### mercedes, column fractions (4 209 rows x 378 columns)


**GE dirty-profiled**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 % | 4209 | 38 | ok | 1.0000 | 0.0063 | 0.0126 | -15.4071 | 175 | 0 | 27475 | 175 | 0.19 | 9.3 | 0.66 | 0.05 |
| 20 % | 4209 | 76 | ok | 1.0000 | 0.0063 | 0.0125 | -16.1509 | 360 | 0 | 56781 | 360 | 0.42 | 16.8 | 0.68 | 0.05 |
| 30 % | 4209 | 113 | ok | 1.0000 | 0.0062 | 0.0123 | -17.1324 | 542 | 0 | 87060 | 542 | 0.56 | 25.5 | 0.69 | 0.05 |
| 40 % | 4209 | 151 | ok | 1.0000 | 0.0061 | 0.0122 | -17.4298 | 725 | 0 | 117246 | 725 | 0.74 | 30.1 | 0.71 | 0.05 |
| 50 % | 4209 | 189 | ok | 1.0000 | 0.0059 | 0.0117 | -18.5069 | 879 | 0 | 148424 | 879 | 1.09 | 36.4 | 0.74 | 0.06 |
| 60 % | 4209 | 227 | ok | 1.0000 | 0.0059 | 0.0118 | -18.2591 | 1065 | 0 | 177937 | 1065 | 1.13 | 40.8 | 0.75 | 0.08 |
| 70 % | 4209 | 265 | ok | 1.0000 | 0.0059 | 0.0117 | -18.4968 | 1236 | 0 | 208326 | 1236 | 1.34 | 46.0 | 0.76 | 0.09 |
| 80 % | 4209 | 302 | ok | 1.0000 | 0.0059 | 0.0117 | -18.6830 | 1412 | 0 | 238688 | 1412 | 1.57 | 52.7 | 0.77 | 0.11 |
| 90 % | 4209 | 340 | ok | 1.0000 | 0.0059 | 0.0117 | -18.6251 | 1585 | 0 | 268014 | 1585 | 1.97 | 60.6 | 0.80 | 0.13 |
| 100 % | 4209 | 378 | ok | 1.0000 | 0.0059 | 0.0117 | -18.8211 | 1774 | 0 | 300198 | 1774 | 2.17 | 70.0 | 0.81 | 0.14 |

**GE clean-profiled**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 % | 4209 | 38 | ok | 1.0000 | 0.0063 | 0.0126 | -15.4071 | 175 | 0 | 27475 | 175 | 0.17 | 9.1 | 0.66 | 0.15 |
| 20 % | 4209 | 76 | ok | 1.0000 | 0.0063 | 0.0125 | -16.1509 | 360 | 0 | 56781 | 360 | 0.35 | 16.0 | 0.68 | 0.15 |
| 30 % | 4209 | 113 | ok | 1.0000 | 0.0062 | 0.0123 | -17.1324 | 542 | 0 | 87060 | 542 | 0.51 | 22.3 | 0.69 | 0.16 |
| 40 % | 4209 | 151 | ok | 1.0000 | 0.0061 | 0.0122 | -17.4298 | 725 | 0 | 117246 | 725 | 0.74 | 28.8 | 0.70 | 0.17 |
| 50 % | 4209 | 189 | ok | 1.0000 | 0.0059 | 0.0117 | -18.5069 | 879 | 0 | 148424 | 879 | 0.94 | 36.0 | 0.74 | 0.17 |
| 60 % | 4209 | 227 | ok | 1.0000 | 0.0059 | 0.0118 | -18.2591 | 1065 | 0 | 177937 | 1065 | 1.24 | 41.2 | 0.74 | 0.17 |
| 70 % | 4209 | 265 | ok | 1.0000 | 0.0059 | 0.0117 | -18.4968 | 1236 | 0 | 208326 | 1236 | 1.53 | 48.1 | 0.75 | 0.18 |
| 80 % | 4209 | 302 | ok | 1.0000 | 0.0059 | 0.0117 | -18.6830 | 1412 | 0 | 238688 | 1412 | 1.85 | 53.6 | 0.76 | 0.20 |
| 90 % | 4209 | 340 | ok | 1.0000 | 0.0059 | 0.0117 | -18.6251 | 1585 | 0 | 268014 | 1585 | 2.43 | 64.8 | 0.79 | 0.21 |
| 100 % | 4209 | 378 | ok | 1.0000 | 0.0059 | 0.0117 | -18.8211 | 1774 | 0 | 300198 | 1774 | 4.98 | 131.9 | 0.81 | 0.21 |

**GE hand-written**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 % | 4209 | 38 | ok | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 27650 | 0 | 0 | 27650 | 0.12 | 14.6 | 0.67 | 0.21 |
| 20 % | 4209 | 76 | ok | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 57141 | 0 | 0 | 57141 | 0.20 | 16.9 | 0.69 | 0.21 |
| 30 % | 4209 | 113 | ok | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 87602 | 0 | 0 | 87602 | 0.33 | 23.6 | 0.72 | 0.21 |
| 40 % | 4209 | 151 | ok | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 117971 | 0 | 0 | 117971 | 0.88 | 41.5 | 0.74 | 0.21 |
| 50 % | 4209 | 189 | ok | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 149303 | 0 | 0 | 149303 | 0.89 | 79.3 | 0.77 | 0.21 |
| 60 % | 4209 | 227 | ok | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 179002 | 0 | 0 | 179002 | 1.40 | 87.9 | 0.80 | 0.21 |
| 70 % | 4209 | 265 | ok | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 209562 | 0 | 0 | 209562 | 0.94 | 82.7 | 0.80 | 0.21 |
| 80 % | 4209 | 302 | ok | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 240100 | 0 | 0 | 240100 | 0.90 | 57.3 | 0.82 | 0.34 |
| 90 % | 4209 | 340 | ok | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 269599 | 0 | 0 | 269599 | 1.12 | 64.5 | 0.86 | 0.21 |
| 100 % | 4209 | 378 | ok | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 301972 | 0 | 0 | 301972 | 2.43 | 123.1 | 0.87 | 0.21 |

**HoloClean**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 % | 4209 | 38 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 27650 | 0 | 0.36 | 10.0 | 0.66 | 0.16 |
| 20 % | 4209 | 76 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 57141 | 0 | 0.79 | 15.5 | 0.70 | 0.16 |
| 30 % | 4209 | 113 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 87602 | 0 | 1.13 | 22.4 | 0.74 | 0.17 |
| 40 % | 4209 | 151 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 117971 | 0 | 1.49 | 29.9 | 0.75 | 0.18 |
| 50 % | 4209 | 189 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 149303 | 0 | 1.90 | 36.1 | 0.82 | 0.18 |
| 60 % | 4209 | 227 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 179002 | 0 | 2.30 | 42.2 | 0.85 | 0.18 |
| 70 % | 4209 | 265 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 209562 | 0 | 3.14 | 48.2 | 0.87 | 0.20 |
| 80 % | 4209 | 302 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 240100 | 0 | 3.52 | 57.3 | 0.87 | 0.21 |
| 90 % | 4209 | 340 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 269599 | 0 | 3.98 | 69.9 | 0.89 | 0.21 |
| 100 % | 4209 | 378 | ok | 0.0000 | 0.0000 | 0.0000 | undefined | 0 | 0 | 301972 | 0 | 5.26 | 71.2 | 1.02 | 0.21 |

**Raha**

| fraction | rows | cols | status | precision | recall | F1 | FG1 | TP | FP | FN | detections | runtime s | wall s | peak container GB | db container GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 % | 4209 | 38 | ok | 0.9988 | 0.9991 | 0.9989 | 0.9998 | 27624 | 33 | 26 | 27657 | 432.62 | 442.9 | 5.70 | 0.03 |
| 20 % | 4209 | 76 | ok | 0.9994 | 0.9989 | 0.9991 | 0.9998 | 57077 | 34 | 64 | 57111 | 1704.01 | 1719.7 | 11.48 | 0.03 |
| 30 % | 4209 | 113 | ok | 0.9998 | 0.9989 | 0.9994 | 0.9999 | 87510 | 19 | 92 | 87529 | 4590.99 | 4611.6 | 21.69 | 0.03 |
| 40 % | 4209 | 151 | ok | 0.9998 | 0.9987 | 0.9993 | 0.9998 | 117821 | 19 | 150 | 117840 | 9132.10 | 9159.7 | 33.04 |  |
| 50 % | | | **oom_killed** | | | | | | | | | | 17356.9 |  | 0.02 |
| 60 % | | | **skipped** | | | | | | | | | | 0 |  |  |
| 70 % | | | **skipped** | | | | | | | | | | 0 |  |  |
| 80 % | | | **skipped** | | | | | | | | | | 0 |  |  |
| 90 % | | | **skipped** | | | | | | | | | | 0 |  |  |
| 100 % | | | **skipped** | | | | | | | | | | 0 |  |  |

## 7. Recreating or changing the figure

`plot.py` reads `results.csv`, keeps the status-ok points per configuration,
and draws FG1, runtime on a log axis and peak memory in GB, with the 0.5 FG1
baseline, the 31.3 GiB limit and the 0.65 GB floor as reference lines.

FG1 keeps three cases apart. A real FG1 ≥ 0 is drawn on the axis. A
negative FG1 (F1 below the cell error rate; FG1 < 0 exactly when F1 < π) and an undefined FG1 (no true
positive, nothing to score) are drawn in two shaded bands below the axis,
labelled "< 0" and "undefined". Inside a band every configuration that ever
lands there has its own row, the same on every panel (undefined: all five;
< 0: the two profiled GE suites), so no series hides another; the band
shows that a score is missing or negative, not how negative (−15 to −19,
see §6). A series is broken where it leaves the axis, so Raha on adult is
three separate points at ≈ 0.99 plus two points in the "undefined" band.
The remaining overlaps are real equal values: HoloClean on adult lies on the
0.5 baseline, and Raha and GE hand-written share FG1 ≈ 1.0 on mercedes
10–40 %.

An OOM-killed fraction has no quality and no runtime, so the FG1 and runtime
panels mark it with a dotted vertical line in the configuration's colour at
the killed fraction, one step past the curve's last point (har 100 %,
mercedes 50 %), labelled OOM, never with a point at an invented height. The
memory panel marks it with an × on the limit line: a symbol for
"killed", not a measured peak. The peak of a killed run is not recorded
(its status comes from exit code 137); the container has no limit of its
own and shares the 31.3 GiB VM with the kernel and the db container, so it
died somewhere between the highest surviving peak (33.04 GB) and 33.6 GB.
Both scripts draw the same marks for a `timeout` row, which would put a
timed-out run on the memory limit line; change that branch before
`TIMEOUT_S` is ever set again. Colours are the five fixed slots of the
validated categorical palette (blue, orange, aqua, yellow, magenta) with
distinct markers, one legend for all panels. The fractions drawn are the
status-ok rows in `results.csv` (there is no fractions constant). The FG1
row of both figures comes from one function, `draw_fg1` in `plot_panels.py`
(`plot.py` imports it together with `fg1_slots`); the bands are set by
`BANDS` and `BAND_STEP` there, and the 0.5 baseline is its `axhline(0.5)`.
To change panels or the runtime/memory reference lines edit `PANELS`,
`LIMIT_GB`, `FLOOR_GB` at the top of both `plot.py` and `plot_panels.py`
(each keeps its own copy). Run it with the command in §4; it writes
`fig_scalability.pdf` and `.png` next to the data.

`plot_panels.py` draws the same nine panels as separate figures in
`panels/` (same data rules, same palette, each with its own legend below the
plot; `--metric` and `--dataset` select a subset). The figures drawn with
the 2 h cap (× at 7 200 s, dotted cap line) are kept in
`backup/figures_2h_cap_20260927/`.

What a thesis caption should still say: what the two bands mean (undefined
= no true positive; < 0 = F1 below the cell error rate, here −15 to −19),
that the dotted line marks an OOM-killed fraction, and that on mercedes
60–100 % Raha was not run (skipped after the 50 % OOM).

## 8. Change log

- 26–27 Sep: campaign run with a 2 h cap per run (§1, §2).
- 27 Sep: GE tiers renamed `generic`/`oracle`/`domain` →
  `dirty_profiled`/`clean_profiled`/`hand_written` in code, in the `tier`
  column of `results.csv` and in `db_mem.csv`. This is why the file's md5 no
  longer matched the first version of this report: reverting the `tier`
  column of `backup/results.before_mercedes_c40_nocap_20260929.csv` to the
  old names reproduces that md5 (255fad4188c3d6f1e63c08448ee6dcaf) exactly.
  The `scratch` column keeps `_domain` in three mercedes rows, and
  `run_all.log` and the 26 Sep detection logs keep the old names.
- 27 Sep: `plot_panels.py` added; nine standalone panels drawn with the
  2 h cap (now in `backup/figures_2h_cap_20260927/panels/`).
- 29 Sep: time limit removed (`run_all.py`: `TIMEOUT_S = None`, new
  `--dataset`/`--fraction`/`--dry-run` filters); the mercedes 40 % Raha
  timeout row removed from `results.csv` (backup first). mercedes 40 % Raha
  re-run: ok, but the Mac slept during it.
- 29–30 Sep: mercedes 50 % Raha: OOM-killed after 17 357 s; its stale
  `skipped` row was replaced. 60–100 % stay `skipped`.
- 30 Sep: clean mercedes 40 % Raha re-run (9 132 s, 33.0 GB) swapped into
  `results.csv`; the slept row moved to `backup/`.
- 30 Sep: `fig_scalability` and the nine `panels/` redrawn without the cap
  by `plot.py` and `plot_panels.py` (dotted vertical line for OOM on the
  runtime panels); this report updated (§1–§8), the adult Raha alternation
  explained (§5 readings), and the report checked claim by claim against
  the data, logs, scripts, Raha's code and the figures by five independent
  reviewers. Afterwards the FG1 row was redrawn: undefined and negative FG1
  moved from 0 into two bands below the axis (one row per configuration,
  so no series is hidden), and the OOM line added to the FG1 panels; the
  FG1 drawing now lives in one function shared by both scripts. That check also corrected errors present since the first
  version: the §5 summary ranges for GE and HoloClean, note (f) (recall,
  not precision, is below the error rate), the "quadratic" growth claims
  (now measured slopes), the definition of `wall_s`, and the §4 clean-up
  command, which never removed anything.
