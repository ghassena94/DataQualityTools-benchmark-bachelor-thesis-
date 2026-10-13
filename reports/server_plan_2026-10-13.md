# Server plan for the 1 TB machine (13 Oct 2026)

Lead plan built from three planner reports (examiner value, rigor, compute) and `reports/hpc_har_mercedes_2026-10-13.md`. The 15 Oct freeze is dropped. **Revised the same day after the Fable 5.1 review (§7).**

**Conventions:**
- est. = estimate at Mac speed: amd64 under emulation, 10 workers.
- Memory is in decimal GB; limits are in bytes.
- † = measured on the server. Every † peak is reported with its memory limit.
- Pass criteria are TP/FP counts and file counts, never runtimes or peaks.
- Block D §9 and `expected_pair_verdicts.csv` (c61ee72) are never edited.

## 1. Goal

**What the plan delivers:**
- **RQ3, the critical path (Mac).** Block D as pre-registered: core bc/nasa, then the bike/adult extension. Compute is under 1 h and < 8 GB (D7), so it needs no server and starts on day 1. The thesis has no RQ3 result yet.
- **RQ2, amount of human input (server).** A Raha label-budget curve: 5–640 tuples × 10 explicit seeds × 7 datasets, in the Mac file order. The thesis currently has one budget (l. 510, 1387). bike above ≈ 500 labels needs more than 33.6 GB; adult's ceiling of ≈ 250 was measured on its truncated cache and is likely lower (est.).
- **RQ2, stability (server).** The sweep's budget-20 slice gives Table 10 an independent-seed row: same file order, other seeds.
- **RQ2, scaling (server).** † points where Fig. 3 has OOM or skipped runs: har 100 %; mercedes 100 % (aligned), then 50/70 % if time allows. The 1 TB row ceiling follows from 8·N², checked at 70 000 rows.
- **RQ1, optional (server).** har as a marked 8th dataset, with supervisor approval.
- **Method.** An environment paragraph: both machines, the emulation, and which number comes from where.
- **Clean migration.** The server gets only the tracked repo plus `rein-datasets/` (≈ 0.9 GB). Nothing that backs a reported number is lost.

**Not doing:**
- Re-running the benchmark to replace Mac numbers. Cached Raha run 1 follows `os.listdir` order, so Tables 3/7/8/10, Fig. 2 and the Block D reference would move.
- Running Block D or regenerating its flags on the server (a core replication is optional), or touching §9, the primary tests or the dataset set.
- mercedes in Tables 3/7/8/9/10, or Raha on raw mercedes files (668 163 positional labels vs 301 972 errors).
- Full Raha on upsampled har.
- Beers FDX regeneration, tuning, LLM detectors, new datasets.
- Speed-factor rescaling, or a full native Fig. 3 replication (unless the P2 switch rule fires).
- Transferring the har, mercedes or `.truncated-*` caches, or rebuilding the image.
- The 100 000–200 000-row clustering probe and FDX on full mercedes (idle filler only, §4).

## 2. Phases

**Order:**
1. P0 on the Mac. Its step 0 (B0) runs today.
2. P3 runs on the Mac from day 1, in parallel with everything below.
3. P1 → P2 on the server.
4. P5's timed jobs after P2; P4 after P2 and its pilot.
5. P6 after `blockd-final` and P4 → P7 (optional) → P8.

**Value rank:** P3 is the critical path. Among the server phases: P4 > P5 > P6 > P7. P5 starts early because it needs little user time.

**Planner disagreements, resolved:**
1. **Where Block D runs** (examiner: either machine + Mac cross-check; rigor: server only if V4 passes; compute: server). **Decision (revised after Fable 5.1):** the Mac, from day 1. A server replication of the core is optional and informational. **Why:**
   - Compute is < 1 h and < 8 GB (D7: fits 0.2–11 s).
   - The flags and Tables 3/9/10 are Mac-made.
   - On the server, RQ3 would wait for ≥ 1 day of bring-up.
   - It would also add a near-tie risk: D3 shows 2 of 45 core verdicts flipping with the RF seed, and the plan had no rule for a failed cross-check.
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
0. **Today, first:** manifest B0 (row 68). It copies the 13 scratchpad scripts into `reports/hpc_har_mercedes_2026-10-13/`, including `rank.py` (the Table 7 ranking and HPC §7 sensitivity table). They live under `/private/tmp`, which is session temp.
1. **Backup:** manifest B1–B5 (a bundle of all refs, a tar of the untracked files). Run them before any freeze or tidy step.
2. **Freeze the Block D extension flags** (plan step 7, moved forward). Warm run 1 depends on the Mac's listdir order, so this cannot wait for the server.
   - bike and adult: Raha run 1, warm.
   - adult HoloClean: regenerated (D8).
   - bike GE hand-written and HoloClean: from the 18 Sep files.
   - five 0-byte GE files.
   - Append all of them to `reports/block_d/flags/MANIFEST.csv` and rerun `checks/addendum_raha_run1/run_addendum.py`.
   - **Then the step-9 restore (ASK-2).** The runs above append rows to bike/adult `detection_results.csv`, and the 1.80 GB snapshot is not migrated, so this is possible only here.
     - First the dry run `bash reports/block_d/step9_restore.sh`. It should report "Raha cache files that differ: 4" (bike/adult `detection.dataset` join bc/nasa).
     - Then `--apply`, without `--cache`.
     - Then the dry run again → "other live files: none".
3. **Tidy and commit:** manifest W1–W5, then G1 and K1–K10 in the manifest's order. K10 commits the extension flags. Then tag `mac-reference`.
4. **Manifests:**
   - `env/MANIFEST.sha256` (`shasum -a 256`): the manifest §5.1 step 3 list (27 inputs + the suite file + 20 633 cache files), plus each dataset's `results/detection_results.csv` and `constraints/` files. Per-file hashes only. Cache completeness is a separate count check (T6).
   - `env/order_manifest.json`: the listdir of the seven `strategy-profiling` folders, taken inside the container. Commit it with `git add -f`, because `*.json` is ignored (`.gitignore` l. 57).
   - `env/mac_20261013/`: architecture, `pip freeze`, threadpoolctl, `os.cpu_count`.
5. **Write `server_env/`. Fable 5.1 reviews it before use.**
   - `docker-compose.server.yml` at the repo root: `image:` without `build:`, no `ports:`, cpuset and memory from `REIN_CPUSET`/`REIN_MEM`, `PYTHONPATH=/rein/server_env`, thread variables = 10.
   - `sitecustomize.py` (overrides `os.cpu_count`).
   - `calib.sh`: modes v1–v5, c4 and probe. Each lane has its own `-p` project. It also samples `memory.stat` anon.
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
   - Never run these in the Mac tree: V1 rewrites `detections.csv` and appends to `detection_results.csv`.
8. **Migrate by copy** (T1–T8). The Mac tree stays the reference, and the Block D machine, until submission.

**Gate:**
- Manifest B3 prints `3`, and the B5 tar holds as many files as the B4 list.
- After `--apply`, the step-9 dry run prints "other live files: none".
- The new flag MANIFEST rows match:
  - bike: GE hand 24247/0, HoloClean 25134/173845, Raha 30861/15138;
  - adult: HoloClean 1677/663530, Raha 865/5081;
  - five empty sets.
- `git ls-tree -r --name-only mac-reference` lists every COMMIT/PROMOTE file of manifest §3.
- `git diff --name-status 17f416c mac-reference` has no `D` line, except K9's file if ASK-7 = delete. Every other line is `A` or `M`.
- Rehearsal: the checksums pass, U3 prints `/rein/server_env/sitecustomize.py 10 10 10`, and `calib.sh v1` passes.

**Cost:**
- Compute est. 15 min: bike 150 s, adult 600 s at ≈ 18 GB, run alone.
- User est. 3–4 h for steps 0–4 and 6–8, plus ≈ 0.5–1 day (est.) to write and review `server_env/`.

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

**Stop rule:** at most 3 h of user time from login to V2a passing. Otherwise pause the server track and ask the admin. P3 is unaffected.

**Thesis:** environment facts.

### P2 Calibration and migration verification

**Goal:** the server reproduces the Mac where it must.
- Everything runs in the byte copy `~/rein-calib`.
- Jobs run one at a time in lane T: J3 → J6 → J4 → J5 → J7.
- Only J8 may run beside them.

**Checks (in run order):**

| Check | What it runs | If it fails |
|---|---|---|
| V1 | GE ×3 tiers and HoloClean on the stored DCs, 7 datasets + har | Server used for cost only. |
| V3 | Mac order replayed (cached Raha, bc/nasa/beers) | Informational. |
| V4 | Block D manifest, plus reruns of d2–d6 and the addendum | Informational: Block D is reported from the Mac. A pass allows the optional server replication. |
| V2 | Raha cold, 7 datasets. Each runs in its `~/rein-calib` folder with the cache moved aside (`strategy-profiling.mac`), after V1/V3/V4. | Any TP/FP or cache-file-count mismatch: stop, no debugging. Server Raha becomes a server-only † series, noted in §5.2.4. |
| C4 | Driver points | — |
| J8 | Linkage at 70 000 rows (2.45e9 > 2^31 entries) | No har r100. |
| V5 | Speed factor and peak ratios, from all runs above | — |

**Why V2 does not use `scalability_driver.py`:**
- It reindexes `clean.csv` by column name (l. 68). That changes Raha's positional labels on smartfactory, whose clean column order differs from the dirty one.
- It deletes its scratch folder with the new cache (l. 162–166), so the file counts could not be read.

**Switch rule:** Table 9 and Fig. 3 stay Mac-primary unless V5 changes a qualitative claim: tool order, order-of-magnitude gaps, growth class, or Raha's failing fraction at 33.6 GB.

**Gate:** V1 and V2a pass on TP/FP and file counts.

**Cost:** compute est. 1.5–2 h serial (V2 = 2 805 s of summed cold runtimes). User est. 2 h.

**Thesis:**
- environment paragraph (§5.1);
- Table 9 speed-factor footnote;
- §5.2.4 file-order sentence.

### P3 Block D as pre-registered (RQ3), on the Mac

**Goal:** plan v2.1 steps 3–9; the fallback "drop bike/adult" is void. It runs where the flags were frozen.

**Steps:**
1. From day 1: `scripts/blockd_driver.py` from `checks/decisions/mini_driver.py`, with `--fill median`, the D6 nasa diagnostic, checks 1–4 and `--dry_run`.
2. The analysis script, tested on a synthetic `results.csv`.
3. Fable 5.1 reviews both; log the fixes in §15.
4. `--dry_run` reprints the committed verdicts.
5. Checks 1–4.
6. Core + median runs, then the core analysis (gate 1).
7. Extension runs and analysis.
8. Step 9: the step-9 dry run still prints "other live files: none" (the restore ran in P0). Then tag `blockd-final`.
9. Optional, after V4: rerun the core on the server as a replication note. It is informational; the Mac numbers are reported.

**Gate:**
- Checks 1–4 pass on four datasets.
- `git diff c61ee72 HEAD -- reports/block_d_final_plan_2026-10-09/checks/expected_pair_verdicts.csv` is empty, and §9 is unchanged.

**Cost:** compute (D7): core < 2 min, bike ≈ 15 min, adult ≈ 20 min, < 8 GB est. User est. 2 days of scripts + 1 day of writing.

**Thesis:**
- new §5.3: concordance table and pair-verdict figure;
- Ch. 6 trade-off;
- threats: the D5 markers and dependence.

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
2. Copy P4's saved budget-20 flag sets (plus bc at 160) to the Mac. Run them through the frozen driver there.
3. Write to `results/blockd_exploratory_<date>.csv`, labelled "exploratory".

**Gate:** the driver is unchanged since `blockd-final`.

**Cost:** compute est. < 2 h (Mac, < 8 GB); user 0.5 day.

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

## 3. Step table, P1 and P2

**How to run:**
- One step at a time; paste the output before going on.
- Server repo: `~/rein-benchmark`; calibration copy: `~/rein-calib`.
- Set `DC='docker compose -f docker-compose.server.yml'` once per shell.
- Lane T uses `-p reint`. Each lane Q job gets its own project (`-p reinq1`, `-p reinq2`, …), so each has its own db.
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
| P2.0 | `cp -a ~/rein-benchmark ~/rein-calib && cd ~/rein-calib && mkdir -p logs results/server && sha256sum -c --quiet env/MANIFEST.sha256 && echo COPY_OK` | `COPY_OK` | `FAILED` |
| V1 | `bash server_env/calib.sh v1 > logs/v1.log 2>&1 < /dev/null; tail -n 2 logs/v1.log` | `V1 PASS 32/32` | any FAIL |
| V3 | `bash server_env/calib.sh v3 breast_cancer nasa beers > logs/v3.log 2>&1 < /dev/null; tail -n 3 logs/v3.log` | bc 317/78, nasa 710/1864, beers 0.9532 | — (informational) |
| V4 | `bash server_env/calib.sh v4 > logs/v4.log 2>&1 < /dev/null; tail -n 2 logs/v4.log` | `V4 PASS` | — (informational; Block D is reported from the Mac) |
| V2a | `bash server_env/calib.sh v2 breast_cancer nasa > logs/v2a.log 2>&1 < /dev/null; tail -n 2 logs/v2a.log` | bc 318/89, 305 files; nasa 731/1864, 125 files | any TP/FP or file-count mismatch: stop, no debugging; server Raha becomes a † series |
| V2b | `bash server_env/calib.sh v2 beers soilmoisture bike smartfactory > logs/v2b.log 2>&1 < /dev/null; tail -n 4 logs/v2b.log` | beers F1 0.9469, 511 files; soil 8881/15343, 18 103 files; bike FP 15142, 508 files; smartfactory 386 960 det., 568 files | same rule as V2a |
| V2c | `bash server_env/calib.sh v2 adult > logs/v2c.log 2>&1 < /dev/null; tail -n 2 logs/v2c.log` | 865/5081, 513 files; runtime and peak recorded for V5 | same rule as V2a |
| C4 | `bash server_env/calib.sh c4 > logs/c4.log 2>&1 < /dev/null; tail -n 3 logs/c4.log` | TP/FP = results.csv l. 107/111/117 | mismatch |
| J8 | `bash server_env/calib.sh probe 70000 > logs/j8.log 2>&1 < /dev/null; tail -n 2 logs/j8.log` | `linkage ok`; peak recorded (≈ 39 GB est.) | exception/OOM |
| V5 | `bash server_env/calib.sh v5` | runtime and peak ratios | — (switch rule) |

## 4. Job schedule

**Lanes:**
- **T:** one timed job, 10 physical cores on NUMA node 0, with the db on the same cores.
- **Q:** disjoint 10-core cpusets and separate compose projects, ≤ 400 GB of limits in total.
- With a single NUMA node, Q runs only while T is idle.
- All limits together stay ≤ 90 % of `free -b`.

| Job | Depends on | Where / lane | Wall-clock (est.) | Peak (est.) |
|---|---|---|---|---|
| J0 extension flags + step-9 restore | B0–B5 | Mac alone | 15 min | 18 GB |
| J1 S1–S9 | — | server | 10 min | — |
| J2 T1–T8, U1–U5 | J0, J1 | server | 1.5–2 h | — |
| J3 V1 | J2 | T | 15 min | < 5 GB |
| J6 V3, V4 | J3 | T | 40 min | < 8 GB |
| J4 V2a, V2b | J6 | T | 27 min | < 10 GB |
| J5 V2c adult | J4 | T | ≤ 21 min | 23.2 GB |
| J7 C4 | J5 | T | 11 min | 11.6 GB |
| J8 70 000-row probe | J2 | Q, not during T | 5–15 min | 39 GB |
| J9 Block D core | driver | Mac | < 2 min | < 4 GB |
| J10 Block D extension | J9 | Mac | 35 min | < 8 GB |
| J11 Block D core replication (optional) | J6, J9 | Q | < 2 min | < 4 GB |
| J12 har r10–r100 † | J7, J8 | T | 1.6–2.5 h | 41 GB |
| J13 mercedes c100 † | J12 | T | 8–25 h (tail 35 h) | 100–210 GB (limit 450000000000; `memory.max` reads 449999998976) |
| J14 mercedes c50, c70 † | J13 finished within 25 h | T | 13 h | 44–102 GB |
| J16a sweep pilot, 1 seed at 640 | J6, Fable review | alone: adult, then smartfactory | ≤ 2 h | adult ≈ 95–105 GB |
| J16 budget sweep | J16a | Q | 6–10 h | per-job limit from J16a |
| J17 Block D exploratory | J10, J16 | Mac | < 2 h | < 8 GB |
| J18 har cold (P7) | J12, approval | Q, never beside J12 | 11–64 min | 41 GB |
| J19 har cached × 10 (P7) | J18 | Q | 1.2–2.2 h | 41 GB |

**Not scheduled (idle filler only):**
- J15, the clustering probe at 100 000–200 000 rows (1–2 h; 80/180/320 GB). 8·N² is analytic, and J8 checks it.
- J20, FDX on full mercedes (1–6 h, 25–50 GB). It will likely find no constraints and informs one footnote.

**Calendar (est.):**
- **Day 1:**
  - B0 first, then P0 steps 1–4.
  - S1–S9 on the server.
  - Start the Block D driver.
- **Day 2:**
  - Driver and analysis script.
  - `server_env/`, its Fable review and the Mac rehearsal.
  - Bundle and image, then T1–T8 and U1–U5.
- **Day 3:**
  - Server: P2 (J3–J8, ≈ 2 h serial), then J12 → J13 unattended.
  - Mac: Block D review, checks 1–4, core runs, gate 1.
- **Day 4:**
  - Mac: Block D extension, analysis, `blockd-final`.
  - Sweep script and prediction.
- **Day 5:** sweep review, J16a, then J16 overnight. J16 needs lane Q: a second NUMA node, or J13 finished.
- **Day 6:** J17 (Mac) and figures. J14 only under its rule.
- **Writing is not in this calendar:** P8 alone is 2–3 days (est.), plus the P3 and P5 write-ups.

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Cached run 1 follows listdir order | Flags frozen on the Mac; the sweep replays the Mac order (`--order mac`); V3 |
| Native cold Raha differs | V2 stop rule (no debugging); server-only † series |
| The driver reindexes `clean.csv` and deletes its scratch cache | V2 runs in the `~/rein-calib` folders, serially after V1/V3/V4 |
| `Pool()` follows the host core count | `sitecustomize`, U3 (rehearsed on the Mac), documented deviation |
| MemoryError swallowed by a bare `except` | S5; a re-raising linkage wrapper; per-column probe |
| Index > 2^31 at ≥ 70 000 rows | J8 before J12 |
| A worker OOM hangs `pool.map` | Watch `memory.events`; stop after 30 min below 1 core |
| Sweep OOM at high budgets (adult/smartfactory slopes come from truncated caches) | J16a pilot sets the per-job limits |
| Page cache inflates `memory.peak` under a high limit | Sampled anon maximum; limit beside every † peak; no cross-machine fit |
| A killed cold run leaves a truncated cache | Scratch copies; move the cache aside before retrying |
| Results overwritten (`detect_errors.py` appends; `run_all.py` lacks `--out`) | New CSVs under `results/server/` only; `rein-calib`; `run_all.py --dry-run` only; backups |
| Docker `900g` ≈ 966 GB | Bytes |
| Published port 5432 with a password | No `ports:` |
| A rebuild changes the environment | `docker load` only; T8, U5 |
| A clone drops ignored files | K5–K7 and K10 commit what must travel; `rein-datasets/` by rsync, then `sha256sum -c` (T5) and the cache counts (T6) |
| The scratchpad is wiped (`rank.py` and 12 other scripts) | B0 today |
| Cleanup loses provenance | B1–B5 first; the tag; the P0 gate |
| A shared machine skews timings | S9; rerun if foreign load exceeds 0.5 |
| Time limit < 40 h | S7; drop c100 |
| Driver bugs | Synthetic test, Fable, checks 1–4 |
| Scope eats writing time | The ranking; P6/P7 only with spare days |

## 6. Open questions

**Server (admin):**
1. Cores and NUMA layout.
2. Docker or Slurm/Apptainer? With Slurm, `--mem` is in MiB (450 GB = `429153M`), and V1–V2 are repeated in that runtime.
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
5. Keep the Mac tree until submission (recommended; it is also the Block D machine)?
6. Block D on the Mac (recommended), with an optional server replication?
7. Cleanup scope: archive untracked leftovers on the Mac, delete only regenerable files and dead refs, keep every script behind a number (K9 only under ASK-7). OK?

## 7. Fable 5.1 review

**Verdict: "ready after fixes."** Each correction was checked against its source before it was applied. 13 are applied, some with corrected details. One remedy is rejected (item 8), and two numbers are corrected (item 2).

| # | Correction | Outcome | Check and change |
|---|---|---|---|
| 1 | Block D on the Mac, not the server | Applied | D7 (fits 0.2–11 s; core < 2 min, bike ≈ 15 min, adult ≈ 20 min) and D3 (2 of 45 RF verdicts flip with the seed) confirmed. P3 now runs on the Mac from day 1. V4 is informational, J9/J10/J17 run on the Mac, J11 is optional. Disagreement 1 and the P1 stop rule are rewritten. |
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
- **`env/order_manifest.json` would be dropped by git.** `*.json` is ignored (`.gitignore` l. 57), so it is committed with `-f`.
- **The goal's adult ceiling** (≈ 250 labels) came from the truncated cache too.
- **The Mac dry run of `calib.sh v1`** would have rewritten detection files in the Mac tree after the step-9 restore. It now runs in a rehearsal copy built like the server's.

**Checked and kept as Fable confirmed:** J4 = 1 588 s; V2 = 2 805 s; J7 = 631 s / 11.6 GB; the har and mercedes estimates; J8 = 8 × 70 000² B = 39.2 GB; the V2a/b/c and V3 expected values (Table 3 run 1 rechecked in `results/runs_log.csv`); §9 is only diffed.

**Not verified:** the image size (≈ 3 GB; Docker not run); the Mac postgres architecture; whether the Mac Docker VM has ≥ 10 CPUs for the U3 rehearsal.
