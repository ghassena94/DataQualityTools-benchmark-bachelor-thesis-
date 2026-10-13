# Server plan for the 1 TB machine (13 Oct 2026)

> **13 Oct (later): Block D moved to the server at the user's request.** Block D steps 3–9 (P3) and the exploratory P6 now run on the server, gated by the cross-machine check V4. The flags are still frozen on the Mac (P0). The frozen prediction (c61ee72: §9 and `expected_pair_verdicts.csv`) is untouched. The bike/adult drop rule is removed; the Block D gates are milestones, not cut-offs. See "Block D on the server" below and the Fable review of the move (§8).

Lead plan built from three planner reports (examiner value, rigor, compute) and `reports/hpc_har_mercedes_2026-10-13.md`. The 15 Oct freeze is dropped. **Revised the same day after the Fable 5.1 review (§7), and again after the move of Block D to the server (§8).**

**Conventions:**
- est. = estimate at Mac speed: amd64 under emulation, 10 workers.
- Memory is in decimal GB; limits are in bytes.
- † = measured on the server. Every † peak is reported with its memory limit.
- Pass criteria are TP/FP counts and file counts, never runtimes or peaks.
- Block D §9 and `expected_pair_verdicts.csv` (c61ee72) are never edited.

## 1. Goal

**What the plan delivers:**
- **RQ3, the critical path (server, since 13 Oct later).** Block D as pre-registered: core bc/nasa, then the bike/adult extension. The flags are frozen on the Mac (P0), because Raha run 1 follows the Mac's listdir order. The driver and the analysis script are written on the Mac from day 1; the runs start on the server once V4 passes. Compute is under 1 h and < 8 GB (D7). The thesis has no RQ3 result yet.
- **RQ2, amount of human input (server).** A Raha label-budget curve: 5–640 tuples × 10 explicit seeds × 7 datasets, in the Mac file order. The thesis currently has one budget (l. 510, 1387). bike above ≈ 500 labels needs more than 33.6 GB; adult's ceiling of ≈ 250 was measured on its truncated cache and is likely lower (est.).
- **RQ2, stability (server).** The sweep's budget-20 slice gives Table 10 an independent-seed row: same file order, other seeds.
- **RQ2, scaling (server).** † points where Fig. 3 has OOM or skipped runs: har 100 %; mercedes 100 % (aligned), then 50/70 % if time allows. The 1 TB row ceiling follows from 8·N², checked at 70 000 rows.
- **RQ1, optional (server).** har as a marked 8th dataset, with supervisor approval.
- **Method.** An environment paragraph: both machines, the emulation, and which number comes from where.
- **Clean migration.** The server gets only the tracked repo plus `rein-datasets/` (≈ 0.9 GB). Nothing that backs a reported number is lost.

**Not doing:**
- Re-running the benchmark to replace Mac numbers. Cached Raha run 1 follows `os.listdir` order, so Tables 3/7/8/10, Fig. 2 and the Block D reference would move.
- Regenerating Block D flags on the server (freeze check 2 would likely refuse Raha), or touching §9, the primary tests or the dataset set.
- mercedes in Tables 3/7/8/9/10, or Raha on raw mercedes files (668 163 positional labels vs 301 972 errors).
- Full Raha on upsampled har.
- Beers FDX regeneration, tuning, LLM detectors, new datasets.
- Speed-factor rescaling, or a full native Fig. 3 replication (unless the P2 switch rule fires).
- Transferring the har, mercedes or `.truncated-*` caches, or rebuilding the image.
- The 100 000–200 000-row clustering probe and FDX on full mercedes (idle filler only, §4).

## Block D on the server (13 Oct, later)

- **Decision (user).** Block D steps 3–9 (P3) and P6 run on the server, gated by V4. The flags stay Mac-frozen, c61ee72 is never edited, the bike/adult drop rule is removed, and gates 1 and 2 are milestones.
- **Minimal Mac prerequisites.** (1) F1: freeze all 10 extension sets. Raha run 1 *must* be made here: it follows the Mac's listdir order, and check 2 (Table 3 counts) is its only test. The other eight sets cost < 1 min and keep `MANIFEST.csv` on one machine. (2) K10, then the step-9 restore (F2–F4), **then** rerun the addendum and commit it (K10c), then F5. (3) `env/` manifests, including the 12 live `detections.csv` files and the BLAS/CPU fingerprint. (4) `server_env/` with `calib.sh v4`, rehearsed on the Mac, which gives the V4 baseline. (5) The driver and the analysis script, reviewed; `--dry_run` and a core run on the Mac, committed as the V4d baseline (< 2 min).
- **Cross-machine check V4** (server, own copy `~/rein-v4`, project `-p reinv4`; J6a, first in P2):
  - V4a: the sha256 of all 20 flag files equals `MANIFEST.csv`.
  - V4b, flags only: `measure_fixes.py`, `implied_predictions.py`, `reference_rankings.py`, `run_addendum.py` and `d8_adult_holoclean.py` reproduce their committed outputs (`git diff --exit-code`).
  - V4c, training: d2 (plain, then `adult`; one concatenated file), d3, d4, d5_fill_statistic (bc, nasa, `bike floor,impute`), d5_why_mean_wins, d5_bike_columns, d5_bike_holiday and d6 (nasa, bike) reproduce the Mac baseline at their printed precision. d7 is skipped (timings only).
  - V4 ends with `git status --porcelain` empty and `git diff c61ee72 -- …/expected_pair_verdicts.csv` empty.
  - V4d, in P3: the server core `results.csv` equals the Mac core run without `fit_s` and `timestamp`.
- **Pass rule (one rule for V4a–V4d).** `calib.sh v4` prints each changed line as a word diff, so the branch follows mechanically:
  - **Pass:** no diff.
  - **Pass with a note:** V4a and V4b are clean, and only `linear` numbers or verdicts differ (on bc/adult also `xgb`). Rows kept, fill values and `degenerate` are unchanged. P3 runs on the server, and an appendix note counts the changed lines.
  - **Stop:** a V4a or V4b diff, or any RF or XGBRegressor number, rows kept or fill value. No debugging. Re-check the transfer (T5); if that is clean, P3 steps 5–9 run on the Mac.
- **Thread and CPU settings** (every Block D, V4 and P6 command, and the Mac rehearsal and Mac core run):
  - `run --rm -T --no-deps --entrypoint python3`: no Postgres, because the entrypoint would wait for it.
  - `-e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -e MKL_NUM_THREADS=1 -e PYTHONHASHSEED=0`. These override the 10 that `server_env` sets for Raha.
  - `-e OPENBLAS_CORETYPE=<the Mac's value from P0 step 4>`, and `-e REIN_IMAGE_ID=<T8 ID>`.
  - Models stay as in plan §6 (`n_jobs=1`, `random_state=0`), and the driver runs with `--jobs 1`.
  - `manifest.json` records `threadpool_info()`, numpy's `__cpu_features__`, `len(os.sched_getaffinity(0))`, the hostname and the variables above. `os.cpu_count()` would only show the `sitecustomize` value 10.
- **New order:**
  - **Mac:** F1 → K10 → F2–F4 → addendum + K10c → F5 → manifests → `server_env/` + rehearsal (V4 baseline) → merge, bundle, transfer. The driver is written in parallel, then the Mac dry run + core run, then a bundle.
  - **Server:** P1 → J6a V4 (gate) → J3–J7 in lane T. J9 (core) and J10 (extension) run in lane Q as soon as V4 has passed and the driver is pulled; on a single NUMA node, they run between J7 and J12. Then `blockd-final` → J12/J13 → P4 → P6.
  - **Earliest core run:** Thu 15 Oct; realistic: Fri 16 Oct.
- **Thesis:** the Block D numbers come from the server, the D2–D8 decision runs from the emulated Mac, plus one sentence on V4 (and the appendix note, if any). **Fallback:** if V4 stops or the P1 stop rule fires, P3 steps 5–9 run on the Mac.

## 2. Phases

**Order:**
1. P0 on the Mac, including the extension freeze, the restore and the V4 baseline (Block D's only Mac compute besides the Mac core run).
2. P3's scripts are written on the Mac from day 1. Its runs start on the server after V4.
3. P1 → P2 on the server, V4 (J6a) first.
4. P3's runs (J9, J10) as soon as V4 passes and the driver is pulled.
5. P5's timed jobs after P2; P4 after P2 and its pilot.
6. P6 after `blockd-final` and P4 → P7 (optional) → P8.

**Value rank:** P3 is the critical path and takes the next free lane before P4 and P5 jobs. Among the other server phases: P4 > P5 > P6 > P7. P5 starts early because it needs little user time.

**Planner disagreements, resolved:**
1. **Where Block D runs** (examiner: either machine + Mac cross-check; rigor: server only if V4 passes; compute: server). **Decision (revised 13 Oct, later, user):** the server, gated by V4. The flags are still frozen on the Mac. (Before: the Mac from day 1, after Fable 5.1, §7 item 1.) **Why:**
   - V4 makes the move checkable. The frozen flags must match `MANIFEST.csv`, and d2–d6 plus the addendum must reproduce their committed outputs. V4d compares the final driver's core run on both machines.
   - The D3 near-tie risk (2 of 45 core verdicts flip with the RF seed) now has a rule: RF and XGBRegressor must be identical, and linear-only drift is reported, not hidden.
   - Bring-up (≈ 1 day, est.) overlaps with writing the scripts (≈ 2 days, est.).
   - If V4 stops or the P1 stop rule fires, Block D runs on the Mac.
2. **Budget sweep** (examiner: 7 datasets × 10 seeds × 5–640; compute: only above the ceilings, caches rebuilt). **Decision:** the examiner design, on the transferred complete caches, read in the Mac file order (`--order mac`). **Why:**
   - RQ2 names the amount of input; points above the ceilings alone answer nothing.
   - Rebuilt caches add unverified state.
   - Sorted order differs from the Mac order on all seven caches (checked 13 Oct).
3. **Separate independent-seed campaign.** **Decision:** no. **Why:** the budget-20 slice gives the same runs at no extra cost.
4. **mercedes** (examiner: c50/c70/c100 in parallel; compute: c100 then c50–c90 serially, ≈ 46 h). **Decision:** c100 first. c50 and c70 follow in lane T only if c100 finishes within 25 h. **Why:**
   - Parallel timed runs contaminate runtimes.
   - Three points test the 2.21 exponent.
   - c60/c80/c90 add ≈ 33 h.
5. **har cold run + 10 cached runs** (compute: core; examiner: last). **Decision:** optional P7, needs supervisor approval. **Why:** little detector insight, and it carries the format fingerprint.
6. **HPC stop rule 1** ("no server work before gate 1"). **Decision:** dropped with the freeze. **Why:** P1/P2 unblock ≈ 10–40 h of unattended P5 runs.

### P0 Mac: backup, freeze, provenance, cleanup, migration

**Goal:** a clean repo on the server, without losing any file behind a reported number.

**What "remove unnecessary code" means here.** Every script we wrote that is kept backs a reported number (manifest §3, B/C evidence column). So nothing we wrote is deleted from git, except `generate_openrefine_clusters.py` if ASK-7 = delete (K9). The cleanup does three things:
- It archives the untracked leftovers on the Mac (≈ 7.6 GB).
- It deletes only regenerable files and dead git refs.
- It sends the server only the tracked repo plus `rein-datasets/`.

**Steps** (all commands are in `reports/cleanup_manifest_2026-10-13.md`):
0. **Done 13 Oct:** B0. The 13 scratchpad scripts are in `reports/hpc_har_mercedes_2026-10-13/` (committed in K7).
1. **Done 13 Oct:** the backup in `~/Desktop/BA/backups/pre-migration_2026-10-13/` (all-refs bundle, full-tree tar, `SHA256SUMS`).
2. **Freeze the Block D extension flags (F1, plan step 7), then restore (F2–F4), then rerun the addendum.** Warm run 1 depends on the Mac's listdir order, so Raha cannot be frozen on the server. The other eight sets take < 1 min and are frozen here too, so `MANIFEST.csv` stays on one machine and K10 sees 21 files.
   - **State before F1** (checked read-only, 13 Oct later): the `step9_restore.sh` dry run prints backup intact, inputs unchanged, "Raha cache files that differ: 2", and as other live files exactly the 8 bc/nasa files. bike's GE and HoloClean files are the 18 Sep files (24 247 and 198 979 lines).
   - **F1, in this order.** One detector per fresh process: `docker compose run --rm -T [-e EXPECTATION_TIER=<tier>] rein python3 scripts/detect_errors.py --dataset_name <ds> --detect_method <greatExpectations|holoclean|raha> --n_iterations 1 < /dev/null > reports/block_d/logs/step7_<ds>_<config>.log 2>&1`. Freeze each set right after its run with `scripts/blockd_freeze_flags.py <ds> <config>`, then `chmod 444` it on the host.
     1. bike `ge_hand_written holoclean`, from the 18 Sep files, **before any GE run**: GE writes all tiers to one file.
     2. bike GE `dirty_profiled`, then `clean_profiled` (0/0/0 each).
     3. bike Raha run 1, with `--n_iterations 1`. The default of 10 would freeze iteration 10 (the 21 Sep batch starts at 45 999 and ends at 46 001). ≈ 150 s; a much longer run means a cold cache, so stop.
     4. adult GE `dirty_profiled`, `clean_profiled`, `hand_written` (0/0/0 each).
     5. adult HoloClean, regenerated (D8; ≈ 26 s; 1677/663530/665207, replay identical).
     6. adult Raha run 1, alone, `--n_iterations 1` (≈ 600 s, ≈ 18 GB).
   - **Stop rule:** any `NOT FROZEN` or `REFUSED` → stop and report. Never retry: a retry appends to `detection_results.csv` and cannot change a warm, seeded run. Raha's cell identity cannot be verified (check 2 compares counts only); the thesis says so.
   - **K10a, K10b and the K10 check** (21 flag files), as in the manifest. K10a now shows no addendum change.
   - **F2–F4, the step-9 restore (ASK-2).** The 1.80 GB snapshot is not migrated, so this is possible only here.
     - Dry run: "Raha cache files that differ: 4", plus the 8 bc/nasa files and the bike/adult files F1 touched.
     - `--apply`, without `--cache`.
     - Dry run again → "other live files: none".
   - **Then rerun `checks/addendum_raha_run1/run_addendum.py` and commit its outputs (K10c).** Only the post-restore state can be reproduced elsewhere (V4b). The 11 Oct addendum prints `ge_hand_written replay == file on disk: False (disk 291/384 cells)`, because the profiled GE runs had overwritten the file. After the restore it is the 18 Sep file again (`True`, 460/680), as in the 9 Oct `measure_fixes_output.txt`. adult HoloClean reads `False (disk 341890 cells)` again (the 17 Sep file), as on 9 Oct.
   - **F5:** `git status --short` is empty. Then tag `mac-reference`.
3. **Done 13 Oct:** tidy and commit, W1–W5, G1, K1–K8 (`3db79eb..269e581`). K10 and K10c are in step 2.
4. **Manifests** (after F5):
   - `env/MANIFEST.sha256` (`shasum -a 256`):
     - the manifest §5.1 step 3 list (27 inputs + the suite file + 20 633 cache files);
     - each dataset's `results/detection_results.csv` and `constraints/` files;
     - **the 12 live `{breast_cancer,nasa,bike,adult}/{greatExpectations,holoclean,raha}/detections.csv`**. V4b and the d-scripts read them (`measure_fixes.py:146,149`, `mini_driver.py:52`), and P3 step 9 checks that the driver never wrote into them.
     - Per-file hashes only. Cache completeness is a separate count check (T6).
   - `env/order_manifest.json`: the listdir of the seven `strategy-profiling` folders, taken inside the container. Commit it with `git add -f`, because `*.json` is ignored (`.gitignore` l. 60).
   - `env/mac_20261013/`: architecture, `pip freeze`, `os.cpu_count`, and the BLAS/CPU fingerprint taken inside the container with the Block D thread settings:
     - `threadpool_info()`, after importing numpy, scipy.linalg, sklearn and xgboost;
     - numpy's `__cpu_features__`;
     - `len(os.sched_getaffinity(0))`.
     - Write the OpenBLAS `architecture` to `openblas_coretype.txt` only if numpy's and scipy's agree. Otherwise there is no pin, and V4 alone decides.
     - `/proc/cpuinfo` is no use under emulation.
5. **Write `server_env/`. Fable 5.1 reviews it before use.**
   - `docker-compose.server.yml` at the repo root: `image:` without `build:`, no `ports:`, cpuset and memory from `REIN_CPUSET`/`REIN_MEM`, `PYTHONPATH=/rein/server_env`, thread variables = 10. Keep the db service and `depends_on` for detector runs. Block D, V4 and P6 bypass them with `run --no-deps --entrypoint python3`: `entrypoint.sh:14–19` waits for Postgres, and the driver and the d-scripts need no database.
   - `sitecustomize.py` (overrides `os.cpu_count`).
   - `calib.sh`: modes v1–v5, c4 and probe. Each lane has its own `-p` project. It also samples `memory.stat` anon.
     - **`v4`** runs V4a–V4c in the current copy with `-p reinv4` and the Block D settings ("Block D on the server").
     - It diffs against `checks/decisions/v4_baseline_mac/<file>` where that exists, and otherwise against the committed file.
     - It prints each changed line as a word diff and a count per file, and ends with `git status --porcelain` and the c61ee72 diff.
   - Commit `env/` and `server_env/`, then merge into `master`. Use the manifest's fallback step 1, or the PR route R1–R3 with your OK.
6. **Save into `~/rein-transfer/`:**
   - `git bundle create ~/rein-transfer/rein-master.bundle master` (not needed if origin is used, R1–R10).
   - `docker save rein-benchmark-rein:latest | gzip > ~/rein-transfer/rein-image.tar.gz` (ID `sha256:8ccf6a40cb8a…`, amd64).
   - The checksum files.
   - **Postgres, only if the server cannot pull from Docker Hub.** The Mac's `postgres:14-alpine` is most likely arm64, because the db service has no `platform:` (compose l. 16–17). So run `docker pull --platform linux/amd64 postgres:14-alpine && docker save postgres:14-alpine | gzip > ~/rein-transfer/postgres-14-alpine-amd64.tar.gz && docker pull postgres:14-alpine`. The last pull restores the Mac's native image.
7. **Rehearse on the Mac** in `~/rein-calib-mac`, built exactly like the server copy:
   - Clone the bundle.
   - `rsync -a` `rein-datasets/` with `~/Desktop/BA/rein-move-excludes.txt`.
   - `shasum -a 256 -c env/MANIFEST.sha256`.
   - U3 (needs ≥ 10 CPUs in the Docker VM).
   - `calib.sh v1`.
   - `calib.sh v4` with the Block D settings → `V4 PASS`. The committed d2–d6 outputs were made with OpenBLAS's default of 10 threads (compose sets no thread variables), so a linear diff here comes from the thread count, not the machine. If it differs, copy the rehearsal outputs into the Mac tree as `checks/decisions/v4_baseline_mac/` (beside the originals, which are never edited), commit them, and rerun `calib.sh v4` → `V4 PASS`.
   - Never run these in the Mac tree: V1 rewrites `detections.csv` and appends to `detection_results.csv`, and V4b rewrites the frozen `expected_pair_verdicts.csv` in place (`implied_predictions.py:125`).
8. **Migrate by copy** (T1–T8). The Mac tree stays the reference, and the Block D fallback, until submission.

**Gate:**
- The backups exist (done 13 Oct).
- The new flag MANIFEST rows match:
  - bike: GE hand 24247/0, HoloClean 25134/173845, Raha 30861/15138;
  - adult: HoloClean 1677/663530, Raha 865/5081;
  - five empty sets.
- After `--apply`, the step-9 dry run prints "other live files: none".
- The rerun addendum (K10c) prints `ge_hand_written replay == file on disk: True` for bc (460), nasa (680) and bike (24 247), and `holoclean … False (disk 341890 cells)` for adult. F5 prints nothing.
- `git ls-tree -r --name-only mac-reference` lists every COMMIT/PROMOTE file of manifest §3.
- `git diff --name-status 17f416c mac-reference` has no `D` line, except K9's file if ASK-7 = delete. Every other line is `A` or `M`.
- Rehearsal: the checksums pass, U3 prints `/rein/server_env/sitecustomize.py 10 10 10`, `calib.sh v1` passes, and `calib.sh v4` prints `V4 PASS` (against the committed outputs or `v4_baseline_mac/`).

**Cost:**
- Compute est. 15 min: bike 150 s, adult 600 s at ≈ 18 GB, run alone. Plus ≤ 40 min (est.) for the V4 rehearsal, unattended.
- User est. 3–4 h for steps 2 and 4–8, plus ≈ 0.5–1 day (est.) to write and review `server_env/`.

**Thesis:** none.

### P1 Server bring-up

**Goal:** know the machine before anything runs.

**Steps:** S1–S9 (read-only; they can run on day 1), then T1–T8 and U1–U5 (§3).

**Gate:**
- x86_64, ≥ 500 GB RAM, cgroup v2;
- overcommit 0/1 and `ulimit -v` unlimited;
- Docker + Compose v2;
- ≥ 100 GB and ≥ 1 M inodes free;
- `frozen-ok`, checksums OK, cache counts match, image ID equal;
- `10 10 10` printed; `memory.peak` readable; `pip freeze` identical.

**Cost:** user est. 1.5–2 h (≈ 0.9 GB of repo and data + ≈ 3 GB image, est.).

**Stop rule:** at most 3 h of user time from login to V2a passing. Otherwise pause the server track and ask the admin. Block D then runs on the Mac (P3 fallback).

**Thesis:** environment facts.

### P2 Calibration and migration verification

**Goal:** the server reproduces the Mac where it must.
- V4 runs first, in its own byte copy `~/rein-v4` (`-p reinv4`). Everything else runs in the byte copy `~/rein-calib`.
- Jobs run one at a time in lane T: J6a (V4) → J3 → J6 → J4 → J5 → J7.
- Only J8 may run beside them, plus J9/J10 (Block D, lane Q) once V4 has passed.

**Checks (in run order):**

| Check | What it runs | If it fails |
|---|---|---|
| V4 (gate for P3) | V4a: the sha256 of the 20 flag files equals `MANIFEST.csv`. V4b: `measure_fixes.py`, `implied_predictions.py`, `reference_rankings.py`, `run_addendum.py` and `d8_adult_holoclean.py` reproduce their committed outputs. V4c: the d2–d6 reruns reproduce the Mac baseline at their printed precision. Own copy, because V1/V3 rewrite the `detections.csv` files that V4b reads, and `implied_predictions.py:125` rewrites the frozen `expected_pair_verdicts.csv` in place. | The pass rule in "Block D on the server": pass / pass with a note → P3 on the server; stop → re-check T5, else P3 steps 5–9 on the Mac. |
| V1 | GE ×3 tiers and HoloClean on the stored DCs, 7 datasets + har | Server used for cost only. |
| V3 | Mac order replayed (cached Raha, bc/nasa/beers) | Informational. |
| V2 | Raha cold, 7 datasets. Each runs in its `~/rein-calib` folder with the cache moved aside (`strategy-profiling.mac`), after V1/V3. | Any TP/FP or cache-file-count mismatch: stop, no debugging. Server Raha becomes a server-only † series, noted in §5.2.4. |
| C4 | Driver points | — |
| J8 | Linkage at 70 000 rows (2.45e9 > 2^31 entries) | No har r100. |
| V5 | Speed factor and peak ratios, from all runs above | — |

**Why V2 does not use `scalability_driver.py`:**
- It reindexes `clean.csv` by column name (l. 68). That changes Raha's positional labels on smartfactory, whose clean column order differs from the dirty one.
- It deletes its scratch folder with the new cache (l. 162–166), so the file counts could not be read.

**Switch rule:** Table 9 and Fig. 3 stay Mac-primary unless V5 changes a qualitative claim: tool order, order-of-magnitude gaps, growth class, or Raha's failing fraction at 33.6 GB.

**Gate:** V4 passes (for P3). V1 and V2a pass on TP/FP and file counts (for P4/P5).

**Cost:** compute est. 1.5–2 h serial (V2 = 2 805 s of summed cold runtimes), plus ≤ 40 min for V4 (Mac speed; faster natively). User est. 2 h.

**Thesis:**
- environment paragraph (§5.1), including where the Block D numbers come from and the V4 result;
- Table 9 speed-factor footnote;
- §5.2.4 file-order sentence.

### P3 Block D as pre-registered (RQ3), on the server

**Goal:** plan v2.1 steps 3–9 on the server, on the Mac-frozen flags. The drop rule for bike/adult is removed (user, 13 Oct). Gates 1 and 2 are milestones, not cut-offs.

**Steps** (the server commands are in §3, table P3):
1. **Mac, from day 1:** `scripts/blockd_driver.py`, built from `checks/decisions/mini_driver.py`, with `--fill median`, the D6 nasa diagnostic, checks 1–4 and `--dry_run`. It is read-only on `rein-datasets/`.
   - `--dry_run` also writes `<out>/dryrun.txt`: the version table, the reprinted verdicts and one digest of the rounded `train_hash` per dataset. It holds no timings, so the two machines' files can be diffed.
   - `manifest.json` records the fingerprint from "Block D on the server" and `REIN_IMAGE_ID`. This replaces the spec's hard-coded "x86_64 under Rosetta".
   - Add `/reports/block_d/runs/*/inputs/` to `.gitignore`. Their sha256 is in the manifest, and adult alone is ≈ 10 MB per run.
2. **Mac:** the analysis script, tested on a synthetic `results.csv`. It has a `--compare <run_a> <run_b>` mode for V4d: it reports `train_hash`, RF, XGB and linear separately and ignores `fit_s` and `timestamp`.
3. **Mac:** Fable 5.1 reviews both; log the fixes in plan §15.
4. **Mac:**
   - `--dry_run` (four datasets) into `reports/block_d/runs/<date>_mac_dryrun/` reprints the committed verdicts.
   - Then the core run (bc, nasa; mean fill) with the Block D settings into `reports/block_d/runs/<date>_mac_core/` (< 2 min est.). This is the V4d baseline, not a reported result.
   - Commit on `master`, overwrite the bundle and transfer it (P3.0).
5. **Server, after V4:** `--dry_run`; its `dryrun.txt` equals the Mac's.
6. **Server:** checks 1–4 (`--check`; seconds for the core, ≈ 4–6 min for adult at the d7 fit times).
7. **Server:** core + median runs (J9); V4d (`--compare` against the Mac core); core analysis (milestone 1).
8. **Server:** extension + median runs (J10), then the four-dataset analysis (milestone 2).
9. **Server:**
   - `sha256sum -c` prints `ALL_OK`, `reports/block_d/flags` has no change, and the c61ee72 diff is empty.
   - Commit, tag `blockd-final`, and bring both back to the Mac by bundle.
   - No step-0 backup or step-9 restore runs on the server. The driver never writes into `rein-datasets/`, and `backup_20261011` stays on the Mac.

**Gate:**
- V4 passed (or passed with a note), and both `dryrun.txt` files are equal.
- V4d: `train_hash`, RF and XGBRegressor are equal. Linear and XGBClassifier fall under the V4 rule.
- Checks 1–4 pass on four datasets.
- `git diff c61ee72 HEAD -- reports/block_d_final_plan_2026-10-09/checks/expected_pair_verdicts.csv` is empty, and §9 is unchanged.
- Step 9 prints `FINAL_OK`.

**Cost:**
- Compute (D7): core < 2 min, bike ≈ 15 min, adult ≈ 20 min, plus ≈ 10 min of `--check`; < 8 GB est. (limit 16000000000).
- User est. 2 days of scripts + ≈ 1 h for the two code transfers + 1 day of writing.

**Fallback:** if V4 stops or the P1 stop rule fires, steps 5–9 run on the Mac, where the flags and the V4d baseline already are. The thesis says which machine.

**Thesis:**
- new §5.3: concordance table and pair-verdict figure;
- Ch. 6 trade-off;
- threats: the D5 markers and dependence;
- §5.1: the Block D numbers come from the server, the D2–D8 decision runs from the emulated Mac, plus the V4 result (and the appendix note, if any).

### P4 Raha label-budget curve (RQ2; server rank 1)

**Goal:** how many labelled tuples Raha needs to reach the hand-written suite, and whether 20 is representative.

**Steps:**
1. Write `scripts/raha_budget_sweep.py`. It:
   - sets `LABELING_BUDGET`;
   - replays the Mac file order from `env/order_manifest.json` for every run (`--order mac`);
   - seeds NumPy and `random` (seeds 0–9) after all imports and immediately before each `Detection.run()`. `import datawig` resets NumPy to 42. The labelling loop is `detection.py:411` in the raha 1.26 copy; re-check the line in the image's 1.25.
   - runs on per-job scratch copies and scores against `actual_errors.csv`;
   - writes `results/server/budget_sweep_<date>.csv`;
   - saves the flagged cells of budget 20 (all seeds; bc also 160) on bc, nasa, bike and adult under `results/server/budget_flags/`, for P6.
2. Commit a predicted curve per dataset. The commit discloses the 23 Sep pilot:
   - bc and soilmoisture were measured at 5–320, bike at 20–160;
   - beers and nasa were flat;
   - adult and smartfactory were measured only on truncated caches.
3. Fable 5.1 reviews the script and the prediction.
4. **Pilot:** one seed at 640 on adult, then on smartfactory, each alone under a 200000000000 limit. Set each dataset's per-job limit to ≈ 1.3 × its measured peak.
5. Run budgets 5–640 (doubling, capped at row count) × 10 seeds × 7 datasets.

**Gate:**
- `--order mac`, budget 20 and the datawig stream reproduce Table 3 run 1: bc 317/78, nasa 710/1864.
- The pilot finishes without OOM.
- No logged exception.

**Cost:**
- Compute est. ≈ 50 h serial. Per seed ≈ 5 h: smartfactory 2.3 h, adult 1.5 h, bike 0.5 h, beers and soilmoisture 0.5 h together.
  - The adult and smartfactory times come from truncated caches (8 of 15 and 11 of 19 columns without clustering), so they are low. The pilot measures them.
- That is 6–10 h wall-clock in lane Q at ≤ 400 GB in total (est.; fewer adult jobs fit at once).
- Adult at 640 ≈ 95–105 GB (est.): the complete-cache peak of 23.2 GB at 20, plus 640 × 59 MB × 15/7. The 23 Sep slope of 59 MB per label was measured with 7 of 15 columns clustered.
- User est. 1 day.

**Caveats:**
- The nasa and smartfactory curves are capped by ground-truth artifacts.
- "adult cannot benefit" was measured on the truncated cache, so it is unverified.

**Thesis:**
- a §5.2.3 figure: F1 against labelled tuples, with the hand-written F1 and its 3–4 h cost as reference lines;
- an independent-seed row in Table 10 (same file order as Table 10, only the seeds differ);
- l. 1387.

### P5 Scalability completion (RQ2; server rank 2, starts after P2)

**Goal:** measured † points instead of extrapolations.

**Steps:**
1. Commit the predictions:
   - har r100 ≈ 41 GB, 11–64 min;
   - mercedes c100 8–25 h, 100–210 GB;
   - linkage ≈ 8·N² B (checked by J8 at 70 000 rows).
2. har r10–r100 with `scalability_driver.py --out results/server/scal_har_<date>.csv`.
3. mercedes c100, aligned. Then c50 and c70, only if c100 finished within 25 h.
4. Every run records `memory.peak`, its limit, and a sampled maximum of `memory.stat` anon. `memory.stat` has no peak field, and `memory.peak` includes page cache that a high limit never reclaims.

**Gate:**
- Every run is recorded as `ok` or `oom_killed`, with `memory.events`.
- No linkage exception.
- har r100 has clusters in all 5 columns.

**Cost:**
- Compute est. ≈ 10–28 h unattended (J12 + J13), + 13 h if J14 runs.
- User est. 3 h + 0.5 day of writing.

**Thesis:**
- a † series in Fig. 3, each peak with its limit; no curve is fitted across machines;
- l. 345–350, including the false claim at l. 348;
- the ceiling at 33.6 GB, and at 1 TB (analytic, checked at 70 000 rows).

### P6 Block D exploratory (server rank 3)

**Goal:** does Raha's downstream place depend on which 20 tuples were labelled? On bc, F1 spreads 0.41–0.64.

**Steps:**
1. After `blockd-final`, write down the expectations.
2. Run P4's saved budget-20 flag sets (plus bc at 160) through the frozen driver on the server, at `blockd-final`, with the Block D settings (`$BD`, lane Q). Nothing is copied back to the Mac.
3. Write to `reports/block_d/runs/<date>_exploratory/`, labelled "exploratory". The driver refuses `results/` (spec §2).

**Gate:** `git diff --exit-code blockd-final -- scripts/blockd_driver.py` is empty.

**Cost:** compute est. < 2 h (server, lane Q, < 8 GB); user 0.5 day.

**Thesis:** a marked paragraph and a small table in §5.3.

### P7 har as an 8th dataset (optional, rank 4)

**Condition:** written supervisor approval.

**Steps:** HPC report §8, R3 (cold run, new cache) and R4 (fresh 10 cached runs).

**Gate:** 110 cache files, clusters in all 5 columns, no MemoryError.

**Cost:** compute est. 1.5–3.2 h; user 1–1.5 days.

**Thesis:**
- marked rows in Tables 3, 8 and 10, plus a Table 9 footnote;
- caveats: 665 null GT cells, the format fingerprint, and the server file order;
- Table 7 stays on 7 datasets.

### P8 Thesis integration

**Steps:**
- environment paragraph and † markers;
- §5.3;
- the budget figure;
- Fig. 3;
- Ch. 6 and Ch. 7;
- a final Fable 5.1 review of every changed number against its CSV.

**Gate:** every Ch. 5 number traces to a file at a tag.

**Cost:** user est. 2–3 days. This is outside the 6-day calendar (§4).

Writing is the real limit, so weigh P6 and P7 against writing days.

## 3. Step tables, P1, P2 and P3

**How to run:**
- One step at a time; paste the output before going on.
- Server repo: `~/rein-benchmark`; calibration copy: `~/rein-calib`; V4 copy: `~/rein-v4`.
- Set `DC='docker compose -f docker-compose.server.yml'` once per shell.
- Lane T uses `-p reint`. Each lane Q job gets its own project (`-p reinq1`, `-p reinq2`, …), so each has its own db. V4 uses `-p reinv4`, and Block D uses `-p reinb` in `~/rein-benchmark`. Neither starts a db (`--no-deps`).
- For Block D and P6, set this once per shell in `~/rein-benchmark`. Drop the `OPENBLAS_CORETYPE` part if P0 step 4 wrote no `openblas_coretype.txt`.
  `export REIN_CPUSET=<lane Q cores> REIN_MEM=16000000000; BD="$DC -p reinb run --rm -T --no-deps --entrypoint python3 -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -e MKL_NUM_THREADS=1 -e PYTHONHASHSEED=0 -e OPENBLAS_CORETYPE=$(cat env/mac_20261013/openblas_coretype.txt) -e REIN_IMAGE_ID=$(docker image inspect -f '{{.Id}}' rein-benchmark-rein:latest) rein"`
- Block D output goes to `reports/block_d/runs/<date>_<name>/`, never to `results/` (the driver refuses it).
- Gate only on TP/FP and file counts. Runtimes and peaks go to V5.
- Never gate on an exact read-back of a limit that is not a multiple of 4096 B.

| Step | Command | Expected | Stop if |
|---|---|---|---|
| S0 (Mac) | `ssh -t <user>@<server> tmux new -A -s rein` | tmux shell | login fails |
| S1 | `uname -m; uname -r; nproc` | `x86_64`, kernel ≥ 5.19, cores | not x86_64 |
| S2 | `lscpu \| grep -E 'Model name\|^Socket\|NUMA'` | NUMA nodes + CPU lists | — (sets lanes) |
| S3 | `free -b; swapon --show` | total ≈ 1000000000000 | < 500000000000 |
| S4 | `stat -fc %T /sys/fs/cgroup` | `cgroup2fs` | other |
| S5 | `cat /proc/sys/vm/overcommit_memory; ulimit -v` | `0`/`1`; `unlimited` | `2` or a number |
| S6 | `id -nG; docker info --format '{{.CgroupVersion}} {{.NCPU}} {{.MemTotal}}'; docker compose version` | `docker` group; `2`; v2 | no Docker (§6) |
| S7 | `command -v sbatch apptainer; sinfo -o '%P %l' 2>/dev/null` | empty or a limit | limit < 40 h (drop c100) |
| S8 | `df -B1 ~; df -i ~` | ≥ 100000000000 B, ≥ 1 M inodes | less |
| S9 | `uptime; docker ps --format '{{.Names}}'; ss -ltn \| grep -c ':5432 '` | low load, none, `0` | foreign heavy load |
| T1 (Mac) | `rsync -a -v ~/rein-transfer/ <user>@<server>:rein-transfer/ \| tail -n 2` | "total size is" ≈ 3.3e9 (image ≈ 3 GB est. + bundle ≈ 0.28 GB) | error |
| T2 | `git clone --branch master ~/rein-transfer/rein-master.bundle ~/rein-benchmark && cd ~/rein-benchmark && git merge-base --is-ancestor c61ee72 HEAD && echo frozen-ok` (or clone from origin after manifest R1–R10) | `frozen-ok` | no `frozen-ok` |
| T3 (Mac) | `rsync -a -n -v --exclude-from=$HOME/Desktop/BA/rein-move-excludes.txt ~/Desktop/BA/rein-benchmark/rein-datasets/ <user>@<server>:rein-benchmark/rein-datasets/ > ~/Desktop/BA/rsync-dryrun.txt; grep -c -E 'error-detection\|truncated\|partial\|raha-baran-results-(har\|mercedes)' ~/Desktop/BA/rsync-dryrun.txt` | `0`; the last line of the file shows a total size ≈ 0.58 GB | count not 0 |
| T4 (Mac) | T3's rsync without `-n` | ends cleanly | error |
| T5 | `cd ~/rein-benchmark && sha256sum -c --quiet env/MANIFEST.sha256 && echo ALL_OK` | `ALL_OK` | `FAILED` |
| T6 | `for d in breast_cancer nasa beers bike adult smartfactory soilmoisture; do printf '%s ' $d; find rein-datasets/$d/raha-baran-results-$d/strategy-profiling -type f \| wc -l; done; ls -d rein-datasets/har/raha-baran-results-har 2>&1 \| head -1` | 305, 125, 511, 508, 513, 568, 18103; then "No such file or directory" | any other count |
| T7 | `gunzip -c ~/rein-transfer/rein-image.tar.gz \| docker load` | `Loaded image: rein-benchmark-rein:latest` | error |
| T8 | `docker image inspect -f '{{.Id}} {{.Architecture}}' rein-benchmark-rein:latest` | `sha256:8ccf6a40cb8a… amd64` | other ID |
| U1 | `docker pull postgres:14-alpine && $DC -p reint config --quiet && echo CONFIG_OK` | `CONFIG_OK` | pull fails: run `gunzip -c ~/rein-transfer/postgres-14-alpine-amd64.tar.gz \| docker load` (P0 step 6), then repeat the config check |
| U2 | `REIN_CPUSET=0-9 REIN_MEM=40000000000 $DC -p reint up -d --wait db` | `Healthy` | not healthy |
| U3 | `$DC -p reint run --rm -T rein python3 -c "import os,multiprocessing as m,sitecustomize as s;print(s.__file__,os.cpu_count(),m.Pool()._processes,len(os.sched_getaffinity(0)))" < /dev/null` | `/rein/server_env/sitecustomize.py 10 10 10` | other |
| U4 | `$DC -p reint run --rm -T rein cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.peak < /dev/null` | `40000000000` (page-aligned), a number | missing file |
| U5 | `$DC -p reint run --rm -T rein pip freeze < /dev/null \| diff - env/mac_20261013/pip_freeze.txt && echo SAME` | `SAME` | any diff |
| P2.0a | `cp -a ~/rein-benchmark ~/rein-v4 && cd ~/rein-v4 && mkdir -p logs && sha256sum -c --quiet env/MANIFEST.sha256 && echo COPY_OK` (`cp -a` keeps mtimes; `d8` prints the HoloClean file's mtime) | `COPY_OK` | `FAILED` |
| V4 | `bash server_env/calib.sh v4 > logs/v4.log 2>&1 < /dev/null; tail -n 6 logs/v4.log` | `V4a 20/20`, `V4b 0 changed lines`, `V4c 0 changed lines`, `git status clean`, `c61ee72 diff empty`, `V4 PASS` | `V4 STOP`: no debugging; re-check T5, else Block D on the Mac. `V4 PASS WITH NOTE`: paste the word diff, then go on |
| P2.0 | `cp -a ~/rein-benchmark ~/rein-calib && cd ~/rein-calib && mkdir -p logs results/server && sha256sum -c --quiet env/MANIFEST.sha256 && echo COPY_OK` | `COPY_OK` | `FAILED` |
| V1 | `bash server_env/calib.sh v1 > logs/v1.log 2>&1 < /dev/null; tail -n 2 logs/v1.log` | `V1 PASS 32/32` | any FAIL |
| V3 | `bash server_env/calib.sh v3 breast_cancer nasa beers > logs/v3.log 2>&1 < /dev/null; tail -n 3 logs/v3.log` | bc 317/78, nasa 710/1864, beers 0.9532 | — (informational) |
| V2a | `bash server_env/calib.sh v2 breast_cancer nasa > logs/v2a.log 2>&1 < /dev/null; tail -n 2 logs/v2a.log` | bc 318/89, 305 files; nasa 731/1864, 125 files | any TP/FP or file-count mismatch: stop, no debugging; server Raha becomes a † series |
| V2b | `bash server_env/calib.sh v2 beers soilmoisture bike smartfactory > logs/v2b.log 2>&1 < /dev/null; tail -n 4 logs/v2b.log` | beers F1 0.9469, 511 files; soil 8881/15343, 18 103 files; bike FP 15142, 508 files; smartfactory 386 960 det., 568 files | same rule as V2a |
| V2c | `bash server_env/calib.sh v2 adult > logs/v2c.log 2>&1 < /dev/null; tail -n 2 logs/v2c.log` | 865/5081, 513 files; runtime and peak recorded for V5 | same rule as V2a |
| C4 | `bash server_env/calib.sh c4 > logs/c4.log 2>&1 < /dev/null; tail -n 3 logs/c4.log` | TP/FP = results.csv l. 107/111/117 | mismatch |
| J8 | `bash server_env/calib.sh probe 70000 > logs/j8.log 2>&1 < /dev/null; tail -n 2 logs/j8.log` | `linkage ok`; peak recorded (≈ 39 GB est.) | exception/OOM |
| V5 | `bash server_env/calib.sh v5` | runtime and peak ratios | — (switch rule) |

**Table P3 (server, `~/rein-benchmark`, after `V4 PASS`).** The driver CLI follows spec §2; adjust the flags if the reviewed driver names them differently. No Mac commits on `master` between P3.0 and P3.9; otherwise merge instead of fast-forwarding.

| Step | Command | Expected | Stop if |
|---|---|---|---|
| P3.0 (Mac, then server) | Mac: `git bundle create ~/rein-transfer/rein-master.bundle master && rsync -a -v ~/rein-transfer/rein-master.bundle <user>@<server>:rein-transfer/`. Server: `cd ~/rein-benchmark && git fetch ~/rein-transfer/rein-master.bundle master && git merge --ff-only FETCH_HEAD && git log --oneline -1` | the Mac's driver commit, including `reports/block_d/runs/<date>_mac_core/` | not a fast-forward |
| P3.1 | `mkdir -p logs; git status --porcelain; sha256sum -c --quiet env/MANIFEST.sha256 && echo ALL_OK` | only `ALL_OK` | any status line, or `FAILED` |
| P3.2 | `$BD scripts/blockd_driver.py --flags_dir reports/block_d/flags --datasets breast_cancer nasa bike adult --dry_run --out reports/block_d/runs/<date>_server_dryrun > logs/p3_dry.log 2>&1 < /dev/null; diff reports/block_d/runs/<date>_server_dryrun/dryrun.txt reports/block_d/runs/<date>_mac_dryrun/dryrun.txt && echo DRY_SAME` | `DRY_SAME` | any diff (the data pipeline differs: stop) |
| P3.3 | `$BD scripts/blockd_driver.py --flags_dir reports/block_d/flags --datasets breast_cancer nasa bike adult --check --out reports/block_d/runs/<date>_server_check > logs/p3_check.log 2>&1 < /dev/null; tail -n 5 logs/p3_check.log` | checks 1–4 PASS on four datasets (≈ 10 min) | any FAIL, non-zero exit |
| P3.4 (J9) | `$BD scripts/blockd_driver.py --flags_dir reports/block_d/flags --datasets breast_cancer nasa --out reports/block_d/runs/<date>_server_core > logs/p3_core.log 2>&1 < /dev/null && $BD scripts/blockd_driver.py --flags_dir reports/block_d/flags --datasets breast_cancer nasa --fill median --out reports/block_d/runs/<date>_server_core_median > logs/p3_core_median.log 2>&1 < /dev/null; echo exit $?` | `exit 0` | non-zero exit |
| P3.5 (V4d) | `$BD scripts/blockd_analysis.py --compare reports/block_d/runs/<date>_mac_core reports/block_d/runs/<date>_server_core` | `train_hash`, RF, XGB equal; linear equal (or changed lines counted) | `train_hash`, RF or XGBRegressor differs: the V4 stop rule |
| P3.6 | `$BD scripts/blockd_analysis.py reports/block_d/runs/<date>_server_core reports/block_d/runs/<date>_server_core_median > logs/p3_core_analysis.log 2>&1 < /dev/null; tail -n 20 logs/p3_core_analysis.log` | core concordance and pair verdicts (milestone 1) | error |
| P3.7 (J10) | As P3.4 with `--datasets bike adult` and `_server_ext`, `_server_ext_median` | `exit 0` (≈ 35–45 min) | non-zero exit, OOM |
| P3.8 | Analysis over core + extension (both fills) | four-dataset result (milestone 2) | error |
| P3.9 | `sha256sum -c --quiet env/MANIFEST.sha256 && test -z "$(git status --porcelain reports/block_d/flags)" && git diff --exit-code c61ee72 -- reports/block_d_final_plan_2026-10-09/checks/expected_pair_verdicts.csv && echo FINAL_OK`, then `git add reports/block_d/runs && git commit -m "Block D results (server)" && git tag blockd-final && git bundle create ~/rein-transfer/blockd-final.bundle master blockd-final` | `FINAL_OK`; 1 commit; a bundle | anything but `FINAL_OK` |
| P3.10 (Mac) | `rsync -a <user>@<server>:rein-transfer/blockd-final.bundle ~/rein-transfer/ && git fetch ~/rein-transfer/blockd-final.bundle master && git merge --ff-only FETCH_HEAD && git fetch ~/rein-transfer/blockd-final.bundle refs/tags/blockd-final:refs/tags/blockd-final && git log --oneline -1 blockd-final` | the server's results commit | not a fast-forward |

## 4. Job schedule

**Lanes:**
- **T:** one timed job, 10 physical cores on NUMA node 0, with the db on the same cores.
- **Q:** disjoint 10-core cpusets and separate compose projects, ≤ 400 GB of limits in total.
- With a single NUMA node, Q runs only while T is idle.
- All limits together stay ≤ 90 % of `free -b`.

| Job | Depends on | Where / lane | Wall-clock (est.) | Peak (est.) |
|---|---|---|---|---|
| J0 extension flags (F1), restore (F2–F4), addendum (K10c) | B0–B5 (done) | Mac alone | 15 min | 18 GB |
| J0b Mac rehearsal: `calib.sh v1`, `v4` (V4 baseline) | J0, `server_env/` | Mac, `~/rein-calib-mac` | ≤ 1 h | < 8 GB |
| J0c Mac `--dry_run` + core run (V4d baseline) | reviewed driver | Mac | < 5 min | < 4 GB |
| J1 S1–S9 | — | server | 10 min | — |
| J2 T1–T8, U1–U5 | J0, J0b, J1 | server | 1.5–2 h | — |
| J6a V4 (gate for P3) | J2 | T, first; `~/rein-v4`, `-p reinv4` | ≤ 40 min | < 8 GB |
| J3 V1 | J6a | T | 15 min | < 5 GB |
| J6 V3 | J3 | T | ≤ 10 min | < 8 GB |
| J4 V2a, V2b | J6 | T | 27 min | < 10 GB |
| J5 V2c adult | J4 | T | ≤ 21 min | 23.2 GB |
| J7 C4 | J5 | T | 11 min | 11.6 GB |
| J8 70 000-row probe | J2 | Q, not during T | 5–15 min | 39 GB |
| J9 Block D core: dry-run diff, checks 1–4, core + median, V4d | J6a pass, J0c, P3.0 | Q (`-p reinb`); single NUMA node: T, after J7 and before J12 | ≈ 15 min | < 4 GB |
| J10 Block D extension: bike + adult, both fills | J9 | Q; single NUMA node: T, before J13 | 35–45 min | < 8 GB (limit 16000000000) |
| J12 har r10–r100 † | J7, J8 (single NUMA node: also J9) | T | 1.6–2.5 h | 41 GB |
| J13 mercedes c100 † | J12 (single NUMA node: also J10) | T | 8–25 h (tail 35 h) | 100–210 GB (limit 450000000000; `memory.max` reads 449999998976) |
| J14 mercedes c50, c70 † | J13 finished within 25 h | T | 13 h | 44–102 GB |
| J16a sweep pilot, 1 seed at 640 | J6, Fable review | alone: adult, then smartfactory | ≤ 2 h | adult ≈ 95–105 GB |
| J16 budget sweep | J16a | Q | 6–10 h | per-job limit from J16a |
| J17 Block D exploratory (P6) | J10, J16, `blockd-final` | Q (`$BD`) | < 2 h | < 8 GB |
| J18 har cold (P7) | J12, approval | Q, never beside J12 | 11–64 min | 41 GB |
| J19 har cached × 10 (P7) | J18 | Q | 1.2–2.2 h | 41 GB |

**Not scheduled (idle filler only):**
- J15, the clustering probe at 100 000–200 000 rows (1–2 h; 80/180/320 GB). 8·N² is analytic, and J8 checks it.
- J20, FDX on full mercedes (1–6 h, 25–50 GB). It will likely find no constraints and informs one footnote.

**Calendar (est.; revised 13 Oct, later):**
- **Day 1 (Tue 13 Oct):**
  - Done: B0, the backup, W1–W5, K1–K8.
  - Mac: F1 (bike, then adult) → K10 → F2–F4 → addendum + K10c → F5 → `mac-reference`.
  - S1–S9 on the server. Start the Block D driver.
- **Day 2 (Wed 14 Oct):**
  - Mac: P0 step 4 (manifests + fingerprint), `server_env/` with `calib.sh v4`, its Fable review, and the rehearsal (J0b, V4 baseline).
  - Driver and analysis script, then their Fable review.
  - Bundle and image, then T1–T8 and U1–U5.
- **Day 3 (Thu 15 Oct, earliest Block D):**
  - Mac: `--dry_run` and core run (J0c), commit, bundle.
  - Server: J6a (V4), then P2 (J3–J8, ≈ 2 h serial).
  - Once V4 has passed: P3.0–P3.6 (J9, V4d, milestone 1), then J12.
- **Day 4 (Fri 16 Oct; the realistic J9 day if Docker or the review slips):**
  - Server: J10, the analysis (milestone 2), `blockd-final`, the bundle back, then J13.
  - Mac: the sweep script and the prediction.
  - On a single NUMA node, J12/J13 start after J9/J10, so J13 slips by up to a day.
- **Day 5 (Sat 17 Oct):** sweep review, J16a, then J16 overnight. J16 needs lane Q: a second NUMA node, or J13 finished.
- **Day 6 (Sun 18 Oct):** J17 (server) and figures. J14 only under its rule.
- **Writing is not in this calendar:** P8 alone is 2–3 days (est.), plus the P3 and P5 write-ups.

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Cached run 1 follows listdir order | Flags frozen on the Mac; the sweep replays the Mac order (`--order mac`); V3 |
| Native cold Raha differs | V2 stop rule (no debugging); server-only † series |
| The driver reindexes `clean.csv` and deletes its scratch cache | V2 runs in the `~/rein-calib` folders, serially after V1/V3 (V4 has its own copy, `~/rein-v4`) |
| `Pool()` follows the host core count | `sitecustomize`, U3 (rehearsed on the Mac), documented deviation |
| MemoryError swallowed by a bare `except` | S5; a re-raising linkage wrapper; per-column probe |
| Index > 2^31 at ≥ 70 000 rows | J8 before J12 |
| A worker OOM hangs `pool.map` | Watch `memory.events`; stop after 30 min below 1 core |
| Sweep OOM at high budgets (adult/smartfactory slopes come from truncated caches) | J16a pilot sets the per-job limits |
| Page cache inflates `memory.peak` under a high limit | Sampled anon maximum; limit beside every † peak; no cross-machine fit |
| A killed cold run leaves a truncated cache | Scratch copies; move the cache aside before retrying |
| Results overwritten (`detect_errors.py` appends; `run_all.py` lacks `--out`) | New CSVs under `results/server/` only, except Block D under `reports/block_d/runs/` (the driver refuses `results/`); `rein-calib`; `run_all.py --dry-run` only; backups |
| Block D numbers differ on native x86 (OpenBLAS kernel and thread count, libm `exp`/`log`; D3 near-ties) | One thread count and a pinned `OPENBLAS_CORETYPE` on both machines; V4 against a Mac baseline made with those settings; V4d on the final driver; models `n_jobs=1`; one pass rule; Mac fallback |
| The driver differs between the machines | Code moves only Mac → server, by bundle and fast-forward; the server `dryrun.txt` (with `train_hash` digests) is diffed against the Mac's |
| The server has no step-0 snapshot | The driver is read-only on `rein-datasets/`; `sha256sum -c`, including the 12 live `detections.csv`, before (P3.1) and after (P3.9) |
| V4 reruns rewrite tracked and frozen files (`implied_predictions.py:125`, `measure_fixes.py:275`) | V4 only in `~/rein-v4`; it ends with `git status --porcelain` and the c61ee72 diff |
| A blocked Raha freeze on the Mac (bike/adult run 1 never regenerated warm before) | Stop and report, no retry; the warm-cache runtime (≈ 150 s / ≈ 600 s) shows whether the cache was used |
| Docker `900g` ≈ 966 GB | Bytes |
| Published port 5432 with a password | No `ports:` |
| A rebuild changes the environment | `docker load` only; T8, U5 |
| A clone drops ignored files | K5–K7 and K10 commit what must travel; `rein-datasets/` by rsync, then `sha256sum -c` (T5) and the cache counts (T6) |
| The scratchpad is wiped (`rank.py` and 12 other scripts) | B0 today |
| Cleanup loses provenance | B1–B5 first; the tag; the P0 gate |
| A shared machine skews timings | S9; rerun if foreign load exceeds 0.5 |
| Time limit < 40 h | S7; drop c100 |
| Driver bugs | Synthetic test, Fable, checks 1–4, V4d (Mac core = server core) |
| Scope eats writing time | The ranking; P6/P7 only with spare days |

## 6. Open questions

**Server (admin):**
1. Cores and NUMA layout. This decides whether Block D (lane Q) runs beside P2 or between J7 and J12.
2. Docker or Slurm/Apptainer? With Slurm, `--mem` is in MiB (450 GB = `429153M`), and V1, V2 and V4 are repeated in that runtime. Bind-mount the repo to `/rein` and `rein-datasets/` to `/rein/datasets`, because the Block D scripts hard-code these paths.
3. Time limit, exclusivity, disk quota, Docker Hub access. Without Docker Hub, use the amd64 postgres from P0 step 6.

**Supervisor:**
1. † values in §5.2.5? har in Tables 3/8/10?
2. The budget curve as an RQ2 extension (a Ch. 3 deviation)?
3. Submission date and a cut-off for server numbers (c100 needs ≥ 36 h).
4. How to acknowledge the machine.

**User:**
1. Top budget: 640 (recommended, after the J16a pilot) or 1 % of rows (adult 452)?
2. Pin 10 workers (recommended)?
3. P7: yes or no?
4. mercedes: c100 only, or also c50 and c70 (only if c100 finishes within 25 h)?
5. Keep the Mac tree until submission (recommended; it is the reference and the Block D fallback)?
6. **Answered 13 Oct (later):** Block D runs on the server, gated by V4. The flags stay Mac-frozen; there is no drop rule; the gates are milestones.
7. Cleanup scope: archive untracked leftovers on the Mac, delete only regenerable files and dead refs, keep every script behind a number (K9 only under ASK-7). OK?
8. On a single NUMA node, run Block D (J9/J10) before J12/J13 (recommended)? It delays c100 by about 1 h.
9. The V4 rule: accept linear-only drift with an appendix note (recommended), or treat any diff as a stop (Block D on the Mac)?

## 7. Fable 5.1 review

**Verdict: "ready after fixes."** Each correction was checked against its source before it was applied. 13 are applied, some with corrected details. One remedy is rejected (item 8), and two numbers are corrected (item 2).

| # | Correction | Outcome | Check and change |
|---|---|---|---|
| 1 | Block D on the Mac, not the server | Applied; **superseded 13 Oct (later) by the user** (§2 disagreement 1, §8) | D7 (fits 0.2–11 s; core < 2 min, bike ≈ 15 min, adult ≈ 20 min) and D3 (2 of 45 RF verdicts flip with the seed) confirmed. P3 now runs on the Mac from day 1. V4 is informational, J9/J10/J17 run on the Mac, J11 is optional. Disagreement 1 and the P1 stop rule are rewritten. |
| 2 | T1/T2 fail; transfer design inconsistent | Applied, numbers corrected | openrsync confirmed (`--info=progress2` → "unrecognized option"). Fable's sizes are binary units. In decimal GB (du today): `.git` 0.30, `rein-datasets/` 5.44, tree 8.68. The transfer now follows manifest §5.2: a clone of a bundle or of origin, plus rsync of `rein-datasets/` with the manifest's exclude file. `transfer_exclude.txt` is dropped. Rows 45, 46, 54, `detection_logs/` and `.claude/` are untracked, so a clone leaves them out by construction. T1–T5 became T1–T8. |
| 3 | P0 diff gate wrong | Applied | The manifest deletes no tracked code except K9 (ASK-7). The gate is restated (no `D` line). P0 now says plainly what "remove unnecessary code" means. |
| 4 | Adult at 640 will OOM at 55 GB | Applied | The 59 MB-per-label slope (23 Sep) was measured on the 101-file cache, where 8 of 15 columns got no clustering. The complete cache clusters all columns (29 Sep note), and its cold peak at 20 is 23.2 GB. New est. ≈ 95–105 GB. Pilot J16a added. smartfactory's slope also came from a truncated cache (11 of 19 columns). |
| 5 | The prediction is not blind | Applied, made precise | The 23 Sep runs covered bc and soilmoisture at 5–320 and bike at 20–160; beers and nasa were flat; adult and smartfactory ran on truncated caches. The prediction commit discloses this. |
| 6 | Sorted order ≠ Table 3/10 order | Applied | Checked today: host `os.listdir` ≠ sorted on all seven caches. The whole sweep uses `--order mac`, so the budget-20 slice differs from Table 10 only in its seeds. |
| 7 | Seed after the datawig import | Applied | `detection.py:411` is the labelling loop in the raha 1.26 copy (uv cache). The image pins 1.25, so the line is re-checked there. The rule: seed after all imports, before each `Detection.run()`. |
| 8 | V2/V3/V4 collide in `~/rein-calib` | Problem confirmed; first remedy rejected | `scalability_driver.py` cannot be used for V2: it reindexes `clean.csv` by name (l. 68), and smartfactory's dirty/clean column orders differ (checked today), so the 386 960 expectation would fail. It also deletes the scratch cache in `finally` (l. 162–166), so file counts are unreadable. Applied the second remedy: J3 → J6 → J4 → J5 → J7 serial, with V2 in the calib folders and the caches moved aside. This also removes a collision Fable missed: V1 and V2 both append to `detection_results.csv`. |
| 9 | V2a stop rule stated twice | Applied | One rule, as HPC stop rule 3: any TP/FP or cache-file-count mismatch → stop, no debugging, server-only † series. |
| 10 | Missing P0 steps | Applied, two details corrected | (a) B1–B5 first. (b) The step-9 restore now follows the freeze. The manifest §5.1 still orders it before the freeze, which is a flag for its owner. The dry-run cache count becomes 4, because the backup MANIFEST lists every dataset's `error-detection/detection.dataset`. (c) The Mac's postgres is most likely arm64 (no `platform:` on the db service), so the saved image must be an amd64 pull. It is only needed without Docker Hub. (d) `mkdir -p logs` is in P2.0. (e) U3 is rehearsed on the Mac. (f) rank.py is covered by the manifest's new B0, which copies all 13 scratchpad scripts; it runs today. |
| 11 | `memory.peak` includes page cache | Applied, refined | `memory.stat` has no peak field, so its anon value is sampled during each run. The limit is stated beside every † peak, and no curve is fitted across machines. |
| 12 | Runtime is not a pass criterion | Applied | V2c's runtime and memory bands and the J8 peak are recorded for V5, not gated. |
| 13 | Cuts | Applied | J15 and J20 are idle filler. J14 runs only if c100 finishes within 25 h. P7 stays conditional. The calendar states that writing lies outside it. |
| 14 | Nits | Applied | 450000000000 reads back as 449999998976 (109 863 281 pages of 4096 B); 40000000000 is exact. MANIFEST holds per-file hashes only, and the counts are T6. Lane Q gets `-p reinq1`, `reinq2`, …. P0 now budgets 0.5–1 day for `server_env/`, and Fable reviews it. |

**Also fixed while verifying:**
- **P6 had no input.** P4 wrote only a scores CSV. The sweep now saves the budget-20 flag sets (and bc at 160).
- **`env/order_manifest.json` would be dropped by git.** `*.json` is ignored (`.gitignore` l. 57 then, l. 60 since K5), so it is committed with `-f`.
- **The goal's adult ceiling** (≈ 250 labels) came from the truncated cache too.
- **The Mac dry run of `calib.sh v1`** would have rewritten detection files in the Mac tree after the step-9 restore. It now runs in a rehearsal copy built like the server's.

**Checked and kept as Fable confirmed:** J4 = 1 588 s; V2 = 2 805 s; J7 = 631 s / 11.6 GB; the har and mercedes estimates; J8 = 8 × 70 000² B = 39.2 GB; the V2a/b/c and V3 expected values (Table 3 run 1 rechecked in `results/runs_log.csv`); §9 is only diffed.

**Not verified:** the image size (≈ 3 GB; Docker not run); the Mac postgres architecture; whether the Mac Docker VM has ≥ 10 CPUs for the U3 rehearsal.

## 8. Fable 5.1 review of the move to the server (13 Oct, later)

**Verdict: "ready after fixes."** Fable found three blocking defects and two contradictions between the planning reports. Each item was checked read-only against its source before it was applied. 18 are applied; 6 of them have a detail corrected or a claim downgraded. Item 8 was settled by running the check now. Item 20 lists flags only. One remedy is rejected: the extra image tag in item 17.

| # | Correction | Outcome | Check |
|---|---|---|---|
| 1 | Rerun the addendum after the restore, not before | Applied | Confirmed. The 11 Oct addendum prints `False (disk 291/384 cells)`; the 9 Oct output and the snapshot hold 460/680; `step9_restore.sh` copies those files back. New order: F1 → K10 → F2–F4 → addendum + K10c → F5. |
| 2 | The entrypoint blocks on Postgres | Applied, downgraded | `entrypoint.sh:14–19` waits for Postgres (confirmed). It is not blocking as written: `compose run` starts the db through `depends_on` unless `--no-deps`, which no report used. Chosen: `--no-deps --entrypoint python3` for Block D, V4, P6 and their Mac twins. Detector and freeze runs keep the db. |
| 3 | The thread count confounds V4c | Applied | Confirmed: compose sets no thread variables (`docker-compose.yml:49–59`), and the VM has 10 CPUs. `calib.sh v4` uses the production settings. The Mac rehearsal sets the baseline; a diff there goes to `v4_baseline_mac/`. |
| 4 | V4 order differs between the reports | Applied | J6a first, in `~/rein-v4`; J3 depends on J6a. |
| 5 | Two different V4 fail rules | Applied | One rule: pass / pass with a note (linear-only) / stop. The word diff makes the branch mechanical. User Q9 confirms it. |
| 6 | F1 lacks its order and commands | Applied, detail corrected | `EXPECTATION_TIER` is read at `benchmark.py:511` (not 512). `--n_iterations` defaults to 10 (`detect_errors.py:25`). The bike 21 Sep batch runs from 45 999 to 46 001 (confirmed). An empty GE run writes a 0-byte file (`detectors.py:497–503`). |
| 7 | No stop rule for a refused Raha freeze | Applied | `blockd_freeze_flags.py:73–76, 89–90` exits `NOT FROZEN` (confirmed). Stop, no retry. The thesis says that cell identity cannot be verified. |
| 8 | Add a pre-F1 restore dry run | Checked now, no user step | Run read-only 13 Oct (later): backup intact, inputs unchanged, 2 cache files, the 8 bc/nasa files. The F2 dry run stays. |
| 9 | `env/MANIFEST.sha256` misses the live `detections.csv` | Applied | Confirmed (old l. 86). The 12 files are added after F5, and P3.1/P3.9 check them. |
| 10 | `implied_predictions.py:125` rewrites the frozen file | Applied | Confirmed, as does `measure_fixes.py:275` for `measure_fixes.json`. V4 runs only in `~/rein-v4` and ends with `git status` and the c61ee72 diff. |
| 11 | The Mac core run should be mandatory, and `--dry_run` should print `train_hash` digests | Applied | A Mac core run is < 2 min (D7). It becomes V4d, the only direct test of the "bit-identical" predictions on the final driver. |
| 12 | Pin `OPENBLAS_CORETYPE` from the start | Applied, with a guard | Recorded in P0 step 4. It is pinned only if numpy's and scipy's OpenBLAS agree. The libm source of drift remains (glibc 2.31, ubuntu:20.04). |
| 13 | V4c invocation details | Applied, detail corrected | d2 runs via stdin, plain then `adult` (`d2_impute_stats.py:3`). Its file has nasa + bc (l. 2–32) and adult (l. 33), not "nasa at l. 1". d3–d8 use `-w …/decisions`. bike d5 uses `floor,impute`. d8 prints the mtime in `TZ=Europe/Berlin`, so copies use `cp -a`/`rsync -a`. |
| 14 | `--check` takes minutes on adult, not seconds | Applied, numbers corrected | The spec's 15.9 s RF fit is the stale 6 Oct value. d7 (9 Oct) measures 11 s for adult's three fits, so check 1 is ≈ 4–6 min on adult and ≈ 10 min in total. |
| 15 | P3 has no step table | Applied | §3 table P3 (P3.0–P3.10). |
| 16 | The driver transfer is not `git pull` | Applied, nuance | `git fetch <bundle> master && git merge --ff-only FETCH_HEAD`. Because T2 clones from the bundle path, `git pull --ff-only` would also work once the bundle is overwritten. Results return the same way (P3.10). |
| 17 | Image traceability | `REIN_IMAGE_ID` applied; the image tag rejected | T8 and U5 already pin the ID and the packages, and the plan forbids rebuilds (`docker load` only). |
| 18 | Path rule conflict; `.gitignore` facts | Applied, detail corrected | Block D exception added (`reports/block_d/runs/`). `results.csv` is not ignored; `manifest.json` and `run.log` are re-included (`.gitignore:170–171`); `/reports/block_d/runs/*/inputs/` is added in P3 step 1. `*.json` is l. 60; K5 is already committed (`589840e`), so this is the current line, not a future one. |
| 19 | `os.cpu_count()` reads 10; V4 needs its own project | Applied | `sched_getaffinity` and the thread variables are recorded; `-p reinv4`. |
| 20 | Stale text elsewhere | Flags only | Plan §12 fallbacks (l. 313–315) and the 15 Oct row: record in plan §16, never in §9. `cleanup_manifest` l. 361 (step 0 on the server; it is no longer needed) and its §5.3 names V1–V6, which clash with this plan's V4. The memory notes `server-migration-and-plan`, `block-d-final-plan-v2`, `block-d-execution-facts` and `block-d-not-resource-limited` still say Mac. |

**Planner claims also corrected:**
- The pipeline report's step 1 ordered the addendum before K10 and the restore, which is item 1.
- Its "tracked" for `reports/block_d/runs/` means "not ignored".
- Its `d5 bike impute` is `floor,impute`.

**Not verified:**
- the OpenBLAS architecture the Mac container reports under emulation;
- whether the 1-thread rehearsal reproduces the committed d2–d6 outputs;
- the server's cores and NUMA layout, which decide where J9/J10 go.
