# Cleanup and migration manifest (13 Oct 2026)

**What this is:** one decision list for moving `rein-benchmark` from the Mac to the 1 TB server. It merges five read-only audits (ours vs upstream, scripts and `rein/`, `reports/`, git layout, data and sizes). Where the audits disagreed I checked the source myself. Each such case is marked "overruled" or "downgraded" in the table.

**Nothing has been changed yet.** Written today and not committed: this file, `reports/server_plan_2026-10-13.md` (row 67), `reports/hpc_har_mercedes_2026-10-13.md` (row 32), and 13 analysis scripts that exist only in the session scratchpad under `/private/tmp` (row 68). The scratchpad can be wiped, so B0 copies them into the repo first.

**Fable 5.1 review applied (13 Oct).** The verdict and the changes are listed in §7.

**Verdicts:**
- **KEEP:** stays as it is.
- **COMMIT:** add to git at its current path.
- **PROMOTE → target:** move or copy to the target, then commit.
- **ARCHIVE:** stays on the Mac only. It is never committed or migrated. Ignored items stay where they are. Untracked-but-not-ignored items move to `~/Desktop/BA/rein-archive-2026-10-13/`.
- **DELETE:** removed after the backup (Phase 0). Only regenerable leftovers and superseded git refs get this verdict.
- **ASK:** you decide. The default is given.

Sizes are in decimal GB/MB.

---

## 1. Summary

| Verdict | Rows | What |
|---|---|---|
| KEEP | 15 | All upstream REIN code, our merged fixes, Block D (frozen, in place), datasets and the 7 complete Raha caches |
| COMMIT | 19 | Report and figure scripts, `runs_log.csv`, Fig. 2–5 code and data, experiment reports, the server plan, evidence folders, and (after ASK-3) the bike/adult flag sets |
| PROMOTE | 4 | `raha_cache_check.py` and `show_raha_rows.py` → `scripts/`; GE memory records → `results/memory_records/`; 13 scratchpad analysis scripts → `reports/hpc_har_mercedes_2026-10-13/` |
| ARCHIVE | 18 | Block D step-0 backup, Raha `error-detection/`, truncated or partial caches, knowledge-base, logs, old backups and renders |
| DELETE | 7 | `__pycache__`, `.DS_Store`, `vec.npy`/`vocab.npy`, `reports/Untitled`, the thirsty-borg worktree, the stash, 8 dead local branches (remote copies after your OK) |
| ASK | 6 rows (12 decisions in §6) | Suites file, OpenRefine generator, `keep_corrected_raha_rows.py`, robustness `runs/`, candidate survey, `KNOWN_ISSUES.md` |

| Payload | Size | How |
|---|---|---|
| **Migrated** | **≈ 0.94 GB** | git clone ≈ 0.33 GB (pack 0.28 + checkout 0.05) plus rsync of `rein-datasets/`: 20 825 files, 0.584 GB of file data (rsync's "total size"; ≈ 0.66 GB on disk), plus 0.024 GB of `reports/robustness/runs/` if ASK-5 = migrate. The Docker image travels separately; its size is measured at M5. |
| **Archived** (stays on the Mac) | **≈ 7.6 GB** | Raha `error-detection/` 2.36, Block D backup 1.80, mercedes partial cache 1.26, truncated caches 1.12, knowledge-base 1.00, rest ≈ 0.07 |
| **Deleted** | **≈ 0.05 GB** | thirsty-borg worktree 0.047, `__pycache__` 0.002, scratch < 0.001; plus the stash and 8 local branches (all kept in the bundle) |

The Mac repo is 8.68 GB today. It is the archive, so do not delete it before the thesis is submitted.

---

## 2. Target repo layout after cleanup (what `git clone` gives on the server)

```
rein-benchmark/
├── Dockerfile  docker-compose.yml  DOCKER.md  entrypoint.sh  init-db.sql
├── requirements.txt  setup.py  README.md  .gitignore (edited)  .dockerignore (edited)
├── rein/                              upstream + our fixes (unchanged)
│   └── auxiliaries/  expectations_dictionary_local.py (new, ASK-1)  memory_probe.py (new)
├── cleaners/  tools/                  upstream + merged tool fixes (unchanged)
├── scripts/
│   ├── generate_fd_rules.py  fds_to_dcs.py  dc_ablation.py
│   ├── scalability_driver.py  robustness_driver.py
│   ├── blockd_freeze_flags.py  blockd_check_format_only.py   (+ blockd_driver.py next)
│   ├── build_detection_report.py  cell_detection_results.py  plot_cell_detection.py   (new)
│   ├── ge_tier_sweep.py  measure_memory.py                                            (new)
│   ├── raha_cache_check.py  show_raha_rows.py                         (new, from reports/)
│   └── detect_errors.py … create_dirty.py  generate_openrefine_clusters.py (ASK-7)
├── results/
│   ├── runs_log.csv                                                   (new)
│   └── memory_records/ memory_records.jsonl  memory_records_summary.json  (new)
├── detectionGraphs/Cell-level-Detection/panel_*.pdf                   (new, Fig. 2)
├── datasets/                          empty mount point (kept)
├── reports/
│   ├── block_d/  flags/ logs/ step0_backup.sh step9_restore.sh      (frozen; flags/{bike,adult}/ added by K10 if ASK-3)
│   ├── block_d_final_plan_2026-10-09.md + block_d_final_plan_2026-10-09/   (unchanged)
│   ├── block_d_plan_review_2026-10-09.md  block_d_driver_spec_2026-10-06.md
│   ├── rein_downstream_protocol_2026-10-07.md  tuning_pilot_2026-10-06/
│   ├── scalability/  run_all.py plot.py plot_panels.py results.csv db_mem.csv fig_scalability.pdf
│   ├── robustness/   8 scripts, results.csv mechanism.csv 5×*.txt 4×fig_*.pdf  (runs/ via rsync if ASK-5)
│   ├── scalability_2026-09-27.md  robustness_final_2026-10-02.md  hpc_har_mercedes_2026-10-13.md
│   ├── hpc_har_mercedes_2026-10-13/  hpc/ harmerc/ edit/   13 analysis scripts (new, from the scratchpad)
│   ├── server_plan_2026-10-13.md                                          (new)
│   ├── verification_2026-09-18/  verification_2026-09-24/  raha_label_oracle_verification_2026-09-24.md
│   ├── gt_flags_bc_har_2026-10-08(.md)  rein_candidate_datasets_2026-10-07(.md) (ASK-9)
│   ├── detection_results_GE_holoclean_raha.pdf  row_level_results_GE_holoclean_raha.csv
│   └── cleanup_manifest_2026-10-13.md
└── rein-datasets/                     NOT in git; rsync, ≈ 0.66 GB after excludes
```

**Why the campaign code stays under `reports/` (ASK-4):** moving it to `experiments/` means editing about 41 `reports/...` literals in 11 scripts, plus 5 reports, the runbook and memory notes. The Block D paths are frozen anyway, so nothing gets cleaner by moving half of `reports/`.

---

## 3. Manifest

### A. Tracked code: upstream REIN plus our merged changes

| # | Path | Verdict | Reason | Evidence |
|---|---|---|---|---|
| 1 | `rein/` (`benchmark`, `detectors`, `datasets`, `cleaners`, `models`, `auxiliaries/{configurations, detectors_dictionary, dataset_metrics, expectations_profiler, expectations_dictionary}`) | KEEP | Ground-truth alignment, FG1, GE tiers. Every table depends on these. | `git diff HEAD` is empty. `detectors.py:665` raises on the old tier names. |
| 2 | `cleaners/`, `tools/`, including our August fixes (CPClean, Picket, dBoost utils, ed2 datasets, HoloClean `detect/`, Profiler `learner.py`) | KEEP | Upstream code. Our fixes are already merged (PR #15). The HoloClean patches are needed for runs with 0 DCs (har, mercedes). | Audit 1 #8–9. `cleaners/FAHES/Results/DMV_dirty.csv` is identical to b389550. |
| 3 | `Dockerfile`, `docker-compose.yml`, `DOCKER.md`, `entrypoint.sh`, `init-db.sql`, `requirements.txt`, `setup.py`, `README.md` | KEEP | The server gets its own uncommitted compose override (runbook U1). | compose l. 42 `platform: linux/amd64`; l. 69 `./rein-datasets:/rein/datasets` |
| 4 | `.gitignore` | KEEP, edit (K5) | The `reports` line is upstream (b389550). It silently ignores every new Block D output. | `git log -S reports -- .gitignore` |
| 5 | `.dockerignore` | KEEP, edit (K8, optional) | `COPY . /rein` also copies `knowledge-base/`, `reports/block_d/backup_*`, `detection_logs/` and `.claude/` on a Mac rebuild. | Only 5 entries today |
| 6 | `scripts/{generate_fd_rules, fds_to_dcs, dc_ablation}.py` | KEEP | Table 6, Table 9 and every HoloClean row. The `--multiplier` comment at `generate_fd_rules.py:26` is wrong; fix it in K8. | `transformer.py:293` divides the value by the column count |
| 7 | `scripts/{scalability, robustness}_driver.py` | KEEP | §5.2.5, §5.2.6, runbook R2 | `--out` is required (`scalability_driver.py:113`) |
| 8 | `scripts/{blockd_freeze_flags, blockd_check_format_only}.py` | KEEP | Block D steps 2 and 7, and D6 | They `exec` `measure_fixes.py` by its `/rein` path |
| 9 | `scripts/{detect_errors, repair_errors, train_model, test_robustness, test_scalability, create_dirty}.py` | KEEP | Upstream. We changed one log label. | aa8b450 |
| 10 | `scripts/generate_openrefine_clusters.py` | **ASK-7** (default KEEP) | Our August fix for an upstream tool. No thesis number depends on it. | Referenced at `rein/cleaners.py:1018`, `rein/detectors.py:1664`, `README.md:228` |
| 11 | `reports/block_d/{flags, logs, step0_backup.sh, step9_restore.sh}`, `reports/block_d_final_plan_2026-10-09.md` + folder, `reports/block_d_plan_review_2026-10-09.md` | KEEP in place, never move | Frozen prediction c61ee72; paths are hard-coded. | `blockd_freeze_flags.py:29,33`; `blockd_check_format_only.py:16,28`; `mini_driver.py:22` |

### B. Untracked code and results outside `reports/`

| # | Path | Verdict | Reason | Evidence |
|---|---|---|---|---|
| 12 | `rein/auxiliaries/expectations_dictionary_local.py` (17 KB) | **ASK-1** (default COMMIT, K1) | The only copy of 8 of the 9 hand-written suites (594 rules). A clone without it scores hand_written 0 on 8 datasets and raises no error. Its mtime is 2 Oct 18:29, after every Sep run (HPC report l. 148). The current file is shown to reproduce the Sep runs only for bc and nasa: the 11 Oct replay in `flags/MANIFEST.csv` is "identical". The 29 Sep `ge_tier_sweep` ran before that mtime, so it is no evidence for this version. The ASK-3 freeze replays bike and adult; server check C6 replays har. | sha256 `5705a516…fb05`. `expectations_dictionary.py:48–55` wraps the import in `except ImportError: pass`; `detectors.py:673–680` runs an empty suite; `measure_fixes.py:57` loads the file by path. |
| 13 | `results/runs_log.csv` | COMMIT (K2) | Tables 3 and 7, Fig. 2, the Table 6 row. Step 9 restores this file. | Identical to the backup copy (sha256 `97ba268c…`) |
| 14 | `scripts/build_detection_report.py` | COMMIT (K2), add a docstring note (K8) | Produced the report that `runs_log.csv` was parsed from. It takes the **latest** row per detector, which is iteration 10 after a batch (7 of 35 values differ). | 1 Oct audit |
| 15 | `scripts/cell_detection_results.py` | COMMIT (K2), fix the name in the docstring (K8) | Parsed the PDF into `runs_log.csv`. Needs pdfplumber, so it runs on the host only. | The docstring still says `log_detection_results.py` |
| 16 | `scripts/plot_cell_detection.py` | COMMIT (K2) | Draws the Fig. 2 panels | Writes to `detectionGraphs/Cell-level-Detection` |
| 17 | `scripts/ge_tier_sweep.py` | COMMIT (K2) | Used on 14 Sep and 29 Sep; suits server check C6 | Read-only re-run of the 3 GE tiers |
| 18 | `rein/auxiliaries/memory_probe.py`, `scripts/measure_memory.py` | COMMIT (K3) | Behind the §5.2.3 claim "profiled GE < 8 MB, follows rows". Audit 4's ARCHIVE is overruled because this backs a thesis sentence. | `measure_memory.py:352` defaults its output to `detection_logs/memory_records.jsonl` |
| 19 | `detection_logs/memory_records.jsonl`, `memory_records_summary.json` (54 KB) | PROMOTE (copy) → `results/memory_records/` (K3, `-f` for the `.json`) | The data behind §5.2.3. It still uses the old tier names generic/oracle; say so in the commit message. | Written 14 Sep 15:18 |
| 20 | `detectionGraphs/Cell-level-Detection/panel_*.pdf` (7) | COMMIT (K2) | Fig. 2 | — |
| 21 | `detectionGraphs/Cell-level-Detection/panel_*.png` (7) + `before_smartfactory_fix_20260929/` | ARCHIVE (move out, W1) | The PNGs can be regenerated; the old panel is superseded. | — |
| 22 | `results/runs_log.before_*` (6 files) | ARCHIVE (move out, W1) | Backups taken before the 27 and 29 Sep fixes | — |
| 23 | `detection_logs/` (the other 652 files; 654 with row 19) | ARCHIVE (stays, ignored; in the tar) | Provenance of the Table 9 cold runtimes and the 29 Sep batch. The folder is recreated automatically. | `configurations.py:73` |

### C. `reports/` (ignored, except row 11)

| # | Path | Verdict | Reason | Evidence |
|---|---|---|---|---|
| 24 | `reports/raha_cache_check.py` | PROMOTE → `scripts/` (K4) | Acceptance check R3 (har must have 110 files). Its paths are relative to the repo root, so no edit is needed. | l. 13, 22 |
| 25 | `reports/show_raha_rows.py` | PROMOTE → `scripts/` (K4) | Mean ± sd for Table 10. Read-only. | l. 5 |
| 26 | `reports/keep_corrected_raha_rows.py` | **ASK-6** (default ARCHIVE) | With `--apply` it rewrites `detection_results.csv` and `runs_log.csv`. It could merge har run 1 (R4). Its backup path is hard-coded to `reports/scalability/backup`. | l. 52; dry run by default |
| 27 | `reports/scalability/{run_all.py, plot.py, plot_panels.py, results.csv, db_mem.csv, fig_scalability.pdf}` | COMMIT in place (K6, `-f`); fix `--out` in `run_all.py` (K8) | Fig. 3, §5.2.5, "up to 0.2 GB". Checks C3/C4 compare against `results.csv` l. 107–117. | `run_all.py` l. 130–133 calls the driver without `--out`, so every run exits with code 2 (runbook l. 282) |
| 28 | `reports/scalability/{progress.py, run_all.log, rerun_mercedes_c40_raha.csv, fig_scalability.png, panels/, backup/}` | ARCHIVE | A viewer, a log, the 40 % row (already merged), and figures that can be regenerated. Memory rule: never sweep `backup/`. | Audit 3 said DELETE for the PNG and `panels/`; downgraded to ARCHIVE. |
| 29 | `reports/robustness/`: 8 scripts + `results.csv`, `mechanism.csv`, 5 `*.txt`, 4 `fig_*.pdf` | COMMIT in place (K6, `-f`) | Fig. 4 and 5, §5.2.6, "Raha average of 6 runs" (thesis l. 1445) | 3 scripts hard-code `/rein/reports/robustness/runs` |
| 30 | `reports/robustness/runs/` (160 runs, 640 files, 24 MB) | **ASK-5** (default MIGRATE by rsync; it stays on the Mac and in the tar too) | The only input from which §5.2.6 can be recomputed: `mechanism.py`, `holo_replicate.py` and the three `raha_*.py` read it. The 3 Oct verification recomputed the 60 knob-1 runs from it. | `mechanism.py:9` hard-codes `reports/robustness/runs` |
| 31 | `reports/robustness/{backup_20261003, backup_20261003_knob2, fig_*.png}` | ARCHIVE | Superseded versions; the PNGs can be regenerated. | — |
| 32 | `reports/{scalability_2026-09-27, robustness_final_2026-10-02, hpc_har_mercedes_2026-10-13, rein_downstream_protocol_2026-10-07}.md` | COMMIT in place (K7, `-f`) | Campaign records, the server runbook, and the basis of plan §10 | — |
| 33 | `reports/block_d_driver_spec_2026-10-06.md` | COMMIT in place (K7) | Superseded, but the tracked plan cites it (l. 7, l. 338), so committing keeps that link working. Audit 3's ARCHIVE is overruled. | plan l. 7 |
| 34 | `reports/tuning_pilot_2026-10-06/` (11 files) | COMMIT in place (K7, `-f`) | Evidence for "no tuning" | plan l. 151 |
| 35 | `reports/verification_2026-09-18/` | COMMIT in place (K7) | The 30-row bit-identical rerun behind §5.2.4. Audit 1's ARCHIVE is overruled because this backs a thesis claim. | — |
| 36 | `reports/raha_label_oracle_verification_2026-09-24.md` + `verification_2026-09-24/` | COMMIT in place (K7, `-f` for `results.json`) | The Table 3 rows that are ground-truth artifacts | — |
| 37 | `reports/gt_flags_bc_har_2026-10-08.md` + folder | COMMIT in place (K7) | Ground-truth checks for bc and har, cited at HPC report l. 89. `{bc,har}_experiments.py` hard-code the Mac repo path; say so in the commit message. | Audit 4 |
| 38 | `reports/detection_results_GE_holoclean_raha.pdf` | COMMIT in place (K7) | Named as `source` in 33 rows of `runs_log.csv` | The column holds the file name only |
| 39 | `reports/row_level_results_GE_holoclean_raha.csv` | COMMIT in place (K7); see ASK-8 | Source of Table 8 for 29 of 30 rows. The adult Raha row (F1 0.0023, 15 Sep, truncated cache) is stale. The thesis value 0.226/0.866 (l. 976) is Raha run 1 in `adult/results/detection_results.csv` (28 Sep 17:53: row_F1 0.2262, row_FG1 0.8663). The file also uses the old tier names. | Checked today |
| 40 | `reports/rein_candidate_datasets_2026-10-07.md` + folder | **ASK-9** (default COMMIT in place) | Survey of candidate datasets. Relevant again now that the freeze is dropped. | — |
| 41 | `reports/detection_results_GE_holoclean_raha.before_beers_20260927.pdf`, `detection_results_*.html` (2) | ARCHIVE | Superseded renders | — |
| 42 | `reports/handoff_*.md` (3) | ARCHIVE | Closed session handoffs | — |
| 43 | `reports/robustness_section.tex`, `robustness_section_short.tex`, `robustness_appendix.tex` | ARCHIVE (ASK-11) | Thesis text belongs in the thesis sources | — |
| 44 | `reports/{rerun_raha_smartfactory.sh, rerun_raha_smartfactory_20260929.log, adult_raha_*.log (2), smartfactory_standalone_cached_20261001.log}` | ARCHIVE | Provenance of Table 10 and of "run 1 = standalone run" | — |
| 45 | `reports/tier_rename_backup_20260927/` | ARCHIVE, never migrate | Its `scalability_*.py` copies write to the live results with the old tier names. Audit 1 said DELETE for the `.py` files; downgraded to ARCHIVE. | — |
| 46 | `reports/block_d/backup_20261011/` (1.80 GB) | ARCHIVE in place; do not move or rename | Step-0 snapshot. 10 live bc/nasa files differ from it today. Copy only `INPUTS.sha256` and `MANIFEST.sha256` to the server. | `step9_restore.sh` l. 9. Read-only `shasum -c` today: inputs 0 failures, 10 FAILED (see ASK-2). |
| 47 | `reports/Untitled`, `reports/scalability/__pycache__/`, `.DS_Store` (4 in the repo; the one in `rein-datasets/` is excluded from the rsync) | DELETE (W2) | Scratch. `Untitled` holds one line: "pip install pdfplumber". | — |

### D. `rein-datasets/` (ignored, 5.44 GB)

| # | Path | Verdict | Reason | Evidence |
|---|---|---|---|---|
| 48 | Per dataset: `clean/dirty/actual_errors.csv`, `error_rate.json`, FD files, `constraints/`, `results/`, `<tool>/detections.csv`, `embeddings/`, `clusters/`, dboost cfg | KEEP, migrate (rsync) | Inputs, ground truth, the human input of Table 9, and the Table 9/10 rows. Whether `embeddings/` exists decides load vs retrain. | `INPUTS.sha256`: OK today. `datasets.py:537–540`. |
| 49 | Complete Raha caches `raha-baran-results-<ds>/strategy-profiling/`: bc 305, nasa 125, beers 511, bike 508, adult 513, smartfactory 568, soilmoisture 18 103 (20 633 files) | KEEP, migrate | Saves the cold runs (adult alone: 1 217 s, 23.2 GB). The server's `os.listdir` order may differ (see ASK-3). | Counted today; runbook l. 139, 147 |
| 50 | `*/raha-baran-results-*/error-detection/` (2.36 GB) | ARCHIVE (excluded from the transfer) | Written at the end of every run and never read. Runbook T1 excludes it. | Audit 5 |
| 51 | `{adult,smartfactory}/raha-baran-results-*.truncated-2026-08-20` (1.12 GB) | ARCHIVE, never migrate | Evidence for the truncated-cache finding | Memory note |
| 52 | `har/raha-baran-results-har/` (49 of 110 files) | ARCHIVE, never migrate | Raha would load this partial cache without a warning. R3 rebuilds it cold. | Runbook R3 |
| 53 | `mercedes/raha-baran-results-mercedes/strategy-profiling.partial-25262-20260915` (1.26 GB) | ARCHIVE, never migrate | Evidence for the §5.2.5 profiling rates | — |

### E. Other ignored items at the top level

| # | Path | Verdict | Reason | Evidence |
|---|---|---|---|---|
| 54 | `knowledge-base/` (1.00 GB) | ARCHIVE, do not migrate | KATARA only. The symlink `cleaners/katara/knowledge-base` dangles harmlessly. | `detectors.py:1393` |
| 55 | `REIN.pdf`, `.claude/settings.local.json` | ARCHIVE | A copy of the paper; Mac-specific permissions | — |
| 56 | `KNOWN_ISSUES.md` | **ASK-10** (default ARCHIVE) | Tool status notes from 18 Jul | Ignored on purpose (`.gitignore`) |
| 57 | `tools/error-generator/errorgenerator.egg-info/` | ARCHIVE (leave in place, not migrated) | Metadata from `pip -e`; the image has its own copy. Deleting it gains nothing. | — |
| 58 | `datasets/` (empty) | KEEP | Mount-point context. Audit 1's DELETE is overruled. | compose l. 69 |
| 59 | `vec.npy`, `vocab.npy` | DELETE (W2) | Picket output written to the working directory | `.gitignore` comment |
| 60 | 66 `__pycache__/` folders (1.8 MB, including cpython-314 files from the host) | DELETE (W2) | Regenerated automatically | — |
| 61 | `.claude/worktrees/thirsty-borg-cbfa47` + branch `claude/thirsty-borg-cbfa47` (47 MB) | DELETE after the tar (W4) | 6 untracked Docker drafts from May, superseded by the 20 Aug Docker setup. The drafts are in the tar. | `git worktree list`: b8a0727, no own commits |

### F. Git refs

| # | Ref | Verdict | Reason | Evidence |
|---|---|---|---|---|
| 62 | `stash@{0}` (24 Aug) | DELETE after the bundle (W3) | Its only unique content is the old FG1 formula, which must not be used. | Audit 4; memory note fg1-is-arithmetic-mean |
| 63 | Local `docs/docker-setup`, `feat/Gain-metrics`, `feat/dataset_metrics`, `feat/fd-to-dc-converter`, `feat/row-level_metrics`, `fix-tools`, `fix/katara-holoclean-docker`, `greatExpectations` | DELETE (W5, `-d` only) | All are ancestors of HEAD and of origin/master | Audit 4 |
| 64 | `feat/experiment-drivers` (4 unpushed commits, including c61ee72) | KEEP until it is merged through the cleanup PR, then DELETE | — | `git rev-list origin/master..HEAD` = 4 |
| 65 | Local `master` (734ae25, 66 behind) and `dev` (310589c) | KEEP, fast-forward | — | Audit 4 |
| 66 | On origin: the 8 dead branches + `feat/experiment-drivers` + `chore/server-migration` | DELETE after the merge, **with your OK** (ASK-12) | — | — |

### G. Added by the Fable 5.1 review

| # | Path | Verdict | Reason | Evidence |
|---|---|---|---|---|
| 67 | `reports/server_plan_2026-10-13.md` (20.9 KB, 13 Oct 10:58) | COMMIT in place (K7, `-f`) | The phase plan for the server. Its §3 T1 is superseded by §5.2 here; say so in the K7 commit message. | Ignored by `.gitignore:27` |
| 68 | Session scratchpad `/private/tmp/claude-503/-Users-ghassen-aicha-caronsale-de-Desktop-BA-rein-benchmark/d9f4049c-b04f-4455-9df8-79fe39ad7968/scratchpad/{hpc,harmerc,edit}/*.py` (13 files: `hpc/{rank,cache_census,posdiff}`, `harmerc/{cachenames,fingerprint,merc_extras,posdiff,suite_check}`, `edit/{har_dec,len_all,merc_float,rank_sens,recount}`) | PROMOTE (copy, B0) → `reports/hpc_har_mercedes_2026-10-13/{hpc,harmerc,edit}/`, commit in K7 (`-f`) | The analysis behind the HPC report: `rank.py` = Table 7 ranking and the §7 provisional/infeasible table (HPC l. 232, 340); `merc_extras.py` is cited at HPC l. 73. The server plan P0 step 2 says to commit `rank.py`. The subfolders stay because the two `posdiff.py` differ. `rank.py`, `rank_sens.py`, `fingerprint.py`, `merc_extras.py`, `harmerc/posdiff.py` and `suite_check.py` hard-code Mac paths; say so in the commit message. | Not in the repo, the bundle or the B4 tar list without B0 |
| 69 | Block D step-7 outputs on the Mac (if ASK-3 = yes): `reports/block_d/flags/{bike,adult}/*.csv` (10 files), the new rows in `flags/MANIFEST.csv`, the step-7 logs under `reports/block_d/logs/`, the re-run outputs in `checks/addendum_raha_run1/` | COMMIT (K10), before R1 | Without a commit the server clone has no extension flags. The new flag files are ignored today. | `git check-ignore -v reports/block_d/flags/bike/raha.csv` → `.gitignore:27` |

---

## 4. Git plan (run from `~/Desktop/BA/rein-benchmark`, one command at a time)

### Phase 0: backup (B0 copies 13 scripts into an ignored folder of the repo; B1–B5 only create files outside it)

| Step | Command | Expect | Stop if |
|---|---|---|---|
| B0 | `S=/private/tmp/claude-503/-Users-ghassen-aicha-caronsale-de-Desktop-BA-rein-benchmark/d9f4049c-b04f-4455-9df8-79fe39ad7968/scratchpad && mkdir -p reports/hpc_har_mercedes_2026-10-13 && cp -Rp "$S/hpc" "$S/harmerc" "$S/edit" reports/hpc_har_mercedes_2026-10-13/ && find reports/hpc_har_mercedes_2026-10-13 -type f -name '*.py' \| wc -l` | `13` | "No such file" (the scratchpad is gone; then row 68 is lost) or a different count |
| B1 | `git remote -v` | origin = `https://github.com/ghassena94/DataQualityTools-benchmark-bachelor-thesis-.git` | anything else |
| B2 | `git bundle create ~/Desktop/BA/rein-backup-2026-10-13.bundle --all` | About 0.28 GB | error |
| B3 | `git bundle verify ~/Desktop/BA/rein-backup-2026-10-13.bundle && git bundle list-heads ~/Desktop/BA/rein-backup-2026-10-13.bundle \| grep -c -e refs/stash -e feat/experiment-drivers` | "is okay", then `3` | fewer than 3 |
| B4 | `{ git -c core.quotepath=off ls-files --others --exclude-standard; git -c core.quotepath=off ls-files --others --ignored --exclude-standard \| grep -v -e '^rein-datasets/' -e '^knowledge-base/' -e '^reports/block_d/backup_20261011/' -e '__pycache__/' -e '\.pyc$' -e '^\.claude/' -e '\.DS_Store$' -e '^vec\.npy$' -e '^vocab\.npy$'; git -C .claude/worktrees/thirsty-borg-cbfa47 ls-files --others --exclude-standard \| sed 's\|^\|.claude/worktrees/thirsty-borg-cbfa47/\|'; } > ~/Desktop/BA/rein-untracked-2026-10-13.list; wc -l < ~/Desktop/BA/rein-untracked-2026-10-13.list` | `1529` = 1516 (recounted read-only 13 Oct 11:07, this file and the server plan included) + 13 from B0 | lower than 1529. If higher, files were written since (e.g. new `detection_logs/`); continue and use B4's number in B5. |
| B5 | `tar -czf ~/Desktop/BA/rein-untracked-2026-10-13.tgz -T ~/Desktop/BA/rein-untracked-2026-10-13.list && tar -tzf ~/Desktop/BA/rein-untracked-2026-10-13.tgz \| wc -l` | The same number as B4 (`1529`); ≈ 0.04 GB before compression | any "Cannot stat", or a number other than B4's |

**What the tar holds:** every untracked or ignored file outside the excluded paths. That includes `detection_logs/` (654 files, 4.5 MB), `reports/robustness/runs/` (640 files, 23.6 MB), all of `reports/` except the step-0 backup, and the 6 worktree drafts. These two folders alone are 1 294 of the 1 516 counted paths. **Not in the tar:** row 46 (step-0 backup), rows 48–53 (`rein-datasets/`), row 54 (`knowledge-base/`), `.claude/` apart from the worktree drafts, `__pycache__`, `.pyc`, `.DS_Store`, `vec.npy`, `vocab.npy`. They stay in place in the Mac repo.

### Phase 1: local tidy (after B5)

| Step | Command | Expect | Stop if |
|---|---|---|---|
| W1 | `mkdir -p ~/Desktop/BA/rein-archive-2026-10-13/results ~/Desktop/BA/rein-archive-2026-10-13/detectionGraphs && mv results/runs_log.before_* ~/Desktop/BA/rein-archive-2026-10-13/results/ && mv detectionGraphs/Cell-level-Detection/panel_*.png detectionGraphs/Cell-level-Detection/before_smartfactory_fix_20260929 ~/Desktop/BA/rein-archive-2026-10-13/detectionGraphs/` | No output | any error |
| W2a | `find . \( -path ./rein-datasets -o -path ./.claude \) -prune -o \( -name __pycache__ -type d -o -name .DS_Store \) -print \| wc -l` (preview) | `70` (66 `__pycache__` + 4 `.DS_Store`, checked today) | a different count |
| W2b | `find . \( -path ./rein-datasets -o -path ./.claude \) -prune -o \( -name __pycache__ -type d -prune -o -name .DS_Store \) -exec rm -rf {} + && rm -f vec.npy vocab.npy reports/Untitled` | No output; the W2a preview then prints `0` | any error |
| W3 | `git stash drop stash@{0}` | `Dropped stash@{0} (fad54bb…)` | a different hash |
| W4 | `git worktree remove --force .claude/worktrees/thirsty-borg-cbfa47` | No output | error |
| W5 | `git branch -d claude/thirsty-borg-cbfa47 docs/docker-setup feat/Gain-metrics feat/dataset_metrics feat/fd-to-dc-converter feat/row-level_metrics fix-tools fix/katara-holoclean-docker greatExpectations` | 9 × "Deleted branch" | any "not fully merged" (never switch to `-D`) |

### Phase 2: the cleanup branch and its commits (local, reversible)

| Step | Command | Expect |
|---|---|---|
| G1 | `git rev-parse --short HEAD && git switch -c chore/server-migration` | `17f416c`, then "Switched to a new branch" |
| K1 (ASK-1 = commit) | `git add rein/auxiliaries/expectations_dictionary_local.py && git commit -m "Track the hand-written GE suites for all nine datasets" -m "File mtime 2 Oct 18:29, after the Sep runs. The 11 Oct Block D replay (reports/block_d/flags/MANIFEST.csv) is identical for breast_cancer and nasa; the other datasets are not re-checked against this version yet."` | 1 file changed |
| K2 | `git add results/runs_log.csv detectionGraphs/Cell-level-Detection/panel_*.pdf scripts/build_detection_report.py scripts/cell_detection_results.py scripts/plot_cell_detection.py scripts/ge_tier_sweep.py && git commit -m "Track the Table 3 runs log, the Figure 2 panels and the report scripts"` | 12 files |
| K3 | `mkdir -p results/memory_records && cp -p detection_logs/memory_records.jsonl detection_logs/memory_records_summary.json results/memory_records/ && git add -f results/memory_records rein/auxiliaries/memory_probe.py scripts/measure_memory.py && git commit -m "Track the GE memory probe and the 14 Sep records behind 5.2.3 (old tier names inside)"` | 4 files |
| K4 | `mv reports/raha_cache_check.py reports/show_raha_rows.py scripts/ && git add scripts/raha_cache_check.py scripts/show_raha_rows.py && git commit -m "Add the Raha cache check and run summary helpers to scripts/"` | 2 files |
| K5 | `.gitignore` edit (diff below), then `git commit -am "Stop ignoring new Block D outputs"` | 1 file |
| K6 | `git add -f reports/scalability/{run_all.py,plot.py,plot_panels.py,results.csv,db_mem.csv,fig_scalability.pdf} reports/robustness/{run_all.sh,run_knob2.sh,plot.py,mechanism.py,holo_replicate.py,raha_labels.py,raha_seed_check.py,raha_strategy_check.py,results.csv,mechanism.csv,raha_labels_cleanstyle.txt,raha_seed_check_asis.txt,raha_seed_check_cleanstyle.txt,raha_strategy_check_asis.txt,raha_strategy_check_cleanstyle.txt} reports/robustness/fig_*.pdf && git commit -m "Track the scalability and robustness campaign code and data in place"` | 25 files |
| K7 | `git add -f reports/{scalability_2026-09-27,robustness_final_2026-10-02,hpc_har_mercedes_2026-10-13,rein_downstream_protocol_2026-10-07,block_d_driver_spec_2026-10-06,raha_label_oracle_verification_2026-09-24,gt_flags_bc_har_2026-10-08,cleanup_manifest_2026-10-13,server_plan_2026-10-13}.md reports/{tuning_pilot_2026-10-06,verification_2026-09-18,verification_2026-09-24,gt_flags_bc_har_2026-10-08,hpc_har_mercedes_2026-10-13}/ reports/detection_results_GE_holoclean_raha.pdf reports/row_level_results_GE_holoclean_raha.csv && git commit -m "Track experiment reports, the server plan and runbook, the HPC analysis scripts and verification evidence" -m "The transfer recipe in cleanup_manifest_2026-10-13.md 5.2 (git clone + rsync of rein-datasets/) supersedes T1 in hpc_har_mercedes_2026-10-13.md 8 and in server_plan_2026-10-13.md 3. hpc_har_mercedes_2026-10-13/ and gt_flags_bc_har_2026-10-08/ scripts hard-code Mac paths."` (add `reports/rein_candidate_datasets_2026-10-07.md reports/rein_candidate_datasets_2026-10-07/` if ASK-9 = commit) | 47 files (56 with the survey); none named `.DS_Store` or under `__pycache__` (`-f` would add them; re-run W2b first if Finder recreated one) |
| K8 | Small fixes, each diff shown before committing: `run_all.py` passes `--out` (required unless `--dry-run`); `generate_fd_rules.py:26` comment; `cell_detection_results.py` docstring name; `build_detection_report.py` latest-row note; `.dockerignore` adds `knowledge-base`, `reports/block_d/backup_*`, `detection_logs`, `.claude`; `expectations_dictionary.py:48–50` comment ("Suites kept outside the repository … if … exists" is false after K1) | 6 files |
| K9 (ASK-7 = delete only) | `git rm scripts/generate_openrefine_clusters.py`, then edit the 3 references | 4 files |
| Check | `git status --short` | Empty |

**K5 diff:**
- Replace `.gitignore` l. 27 (`reports`) with these 4 lines:
  ```
  /reports/*
  !/reports/block_d/
  !/reports/block_d_final_plan_2026-10-09/
  /reports/block_d/backup_*/
  ```
- Append at the end of the file, after `*.json` and `*.log`, otherwise those two rules win:
  ```
  !/reports/block_d/**/*.log
  !/reports/block_d/**/*.json
  !/reports/block_d_final_plan_2026-10-09/**/*.log
  !/reports/block_d_final_plan_2026-10-09/**/*.json
  ```
  Without the last two lines, new `.json`/`.log` files under the plan folder stay ignored (scratch-repo simulation). Files already tracked there, such as `checks/addendum_raha_run1/measure_fixes.json`, are not affected either way. Files under `backup_*/` stay ignored, because their parent folder is excluded.

**K5 checks:**
- `git check-ignore -q reports/block_d/new.csv; echo $?` → `1`
- `git check-ignore -q reports/block_d/logs/new.log; echo $?` → `1`
- `git check-ignore -q reports/block_d/flags/bike/raha.csv; echo $?` → `1`
- `git check-ignore -q reports/block_d_final_plan_2026-10-09/checks/new.json; echo $?` → `1`
- `git check-ignore -q reports/block_d_final_plan_2026-10-09/checks/new.log; echo $?` → `1`
- `git check-ignore -q reports/block_d/backup_20261011/INPUTS.sha256; echo $?` → `0`
- `git check-ignore -q reports/block_d/backup_20261011/x.json; echo $?` → `0`
- `git check-ignore -q reports/server_plan_2026-10-13.md; echo $?` → `0` (still needs `-f` in K7)

### Phase 2b: Block D extension freeze and step-9 restore (on the Mac, after K9, before Phase 3)

Order matters. Step 7 on bike/adult overwrites `{greatExpectations,holoclean,raha}/detections.csv`, appends to `detection_results.csv` and `iou.csv`, and rewrites `_all_constraints.txt` (`step0_backup.sh` l. 3–6). The restore must therefore come after the freeze; otherwise the rsync'd `rein-datasets/` and `build_detection_report.py` (latest row) carry step-7 state.

| Step | Command | Expect | Stop if |
|---|---|---|---|
| F1 (ASK-3 = yes) | Block D plan step 7 for bike and adult (Raha run 1 warm, adult HoloClean regenerated per D8, GE tiers), each set frozen with `python3 scripts/blockd_freeze_flags.py <ds> <config>` in the rein container | Every freeze passes checks 1–3; 10 new files in `reports/block_d/flags/{bike,adult}/`; 10 new rows in `MANIFEST.csv`; then re-run `checks/addendum_raha_run1/run_addendum.py` | any REFUSED or check failure |
| K10a (ASK-3 = yes) | `git add reports/block_d reports/block_d_final_plan_2026-10-09 && git status --short` | 10 `A` flag files under `flags/{bike,adult}/`, `M` `flags/MANIFEST.csv`, `A` step-7 logs, `M` addendum outputs; nothing under `backup_20261011/` | any path under `backup_20261011/` |
| K10b | `git commit -m "Block D step 7: freeze the bike and adult flag sets on the Mac (Raha run 1 depends on the Mac's listdir order)"` | 1 commit | error |
| K10 check | `git ls-files reports/block_d/flags \| wc -l` | `21` (MANIFEST + 10 core + 10 extension) | other |
| F2 (ASK-2 = yes) | `bash reports/block_d/step9_restore.sh` | "backup intact? yes", "inputs unchanged? yes", Raha cache files that differ: `4` (`2` if ASK-3 = no; only `error-detection/detection.dataset`, which is not migrated), the 8 bc/nasa files plus the bike/adult files step 7 touched | "no" on either of the first two lines |
| F3 | `bash reports/block_d/step9_restore.sh --apply` | "restored; check: …" | error |
| F4 | `bash reports/block_d/step9_restore.sh` | Raha cache files: `4` (or `2`), other live files: `none` | any other live file |
| F5 | `git status --short` | Empty (the restore rewrites `results/runs_log.csv` with an identical copy) | any line |

### Phase 3: remote (**each command needs your OK**; everything above is local; start only after Phase 2b, so that K10 is on the branch)

| Step | Command | Expect |
|---|---|---|
| R1 | `git push -u origin chore/server-migration` | New branch on origin |
| R2 | `gh pr create --repo ghassena94/DataQualityTools-benchmark-bachelor-thesis- --base master --head chore/server-migration --title "Server migration: Block D freeze, thesis evidence, cleanup"` | A PR URL on **ghassena94** (without `--repo`, gh can target the mohamedyd parent) |
| R3 | `gh pr merge <N> --repo ghassena94/DataQualityTools-benchmark-bachelor-thesis- --merge` | Merged. **Never** `--squash` or `--rebase`: c61ee72 must stay in master's history. |
| R4 | `git fetch origin && git merge-base --is-ancestor c61ee72 origin/master && echo frozen-ok` | `frozen-ok`; **stop** if it does not print |
| R5 | `git switch master && git merge --ff-only origin/master` | "Fast-forward" |
| R6 | `git push origin master:dev` | `310589c..<merge> master -> dev` |
| R7 | `git push origin --delete docs/docker-setup feat/Gain-metrics feat/dataset_metrics feat/fd-to-dc-converter feat/row-level_metrics fix-tools fix/katara-holoclean-docker greatExpectations feat/experiment-drivers chore/server-migration` | 10 × `[deleted]` |
| R8 | `git branch -d feat/experiment-drivers chore/server-migration` | 2 × "Deleted branch" |
| R9 (optional) | `git tag blockd-prediction-frozen c61ee72 && git push origin blockd-prediction-frozen` | New tag |
| R10 | `git ls-remote --heads origin` | Exactly `dev` and `master`, same SHA |

**Fallback without touching GitHub** (after K10/F5):
1. `git switch master && git merge --ff-only origin/master` → "Fast-forward" `734ae25..c52c769`. Local `master` is 66 commits behind `origin/master`, and `git merge-base --is-ancestor origin/master HEAD` is false; without this step the merge below builds a master without c52c769 (PR #15) that can never be pushed fast-forward. The trees of c52c769 and 6978997 are identical, so the next merge is clean.
2. `git merge --no-ff chore/server-migration`
3. `git merge-base --is-ancestor c61ee72 master && git merge-base --is-ancestor origin/master master && echo ok` → `ok`
4. `git bundle create ~/Desktop/BA/rein-master-2026-10-13.bundle master`
5. Copy the bundle to the server and `git clone rein-master-2026-10-13.bundle rein-benchmark` there.

---

## 5. Migration recipe

### 5.1 On the Mac, before the transfer

1. Phase 2b is done, in this order: freeze bike/adult (F1, ASK-3) → K10 commit → `step9_restore.sh` dry run (F2) → `--apply` (F3) → dry run again, "other live files: none" (F4). Never restore before the freeze.
2. Run the runbook Mac steps M1–M5 (`hpc_har_mercedes_2026-10-13.md` §8):
   - M1: compose already forces `linux/amd64`, so the image runs on an x86_64 server.
   - M5: `docker save` the image shown by `docker compose images`, plus `postgres:14-alpine` if the server cannot pull from Docker Hub.
3. Build the checksum manifest, after F4 (expect `20661` = 27 inputs + 1 suite file + 20 633 cache files):
   ```
   { shasum -a 256 rein-datasets/*/clean.csv rein-datasets/*/dirty.csv rein-datasets/*/actual_errors.csv rein/auxiliaries/expectations_dictionary_local.py; for d in breast_cancer nasa beers bike adult smartfactory soilmoisture; do find rein-datasets/$d/raha-baran-results-$d/strategy-profiling -type f -print0 | xargs -0 shasum -a 256; done; } > ~/Desktop/BA/rein-move-2026-10-13.sha256; wc -l < ~/Desktop/BA/rein-move-2026-10-13.sha256
   ```

### 5.2 What travels how

| Channel | Content | Size |
|---|---|---|
| `git clone --branch master` | Everything tracked after Phase 2/3: code, Block D plan, flags and checks, campaign code and data, reports, `runs_log.csv`, Fig. 2 PDFs, the suites file (ASK-1) | ≈ 0.33 GB |
| rsync | `rein-datasets/` with the exclude list below | 0.584 GB file data (≈ 0.66 GB on disk), 20 825 files |
| rsync (conditional) | `reports/robustness/runs/` if ASK-5 = migrate (the default; 640 files, 0.024 GB); `expectations_dictionary_local.py` if ASK-1 = keep untracked | < 0.03 GB |
| rsync | `~/Desktop/BA/rein-move-2026-10-13.sha256` and `reports/block_d/backup_20261011/{INPUTS,MANIFEST}.sha256` → server `~/rein-checksums/` | < 3 MB |
| `docker save` / `docker load` (M5/T2) | The Mac's amd64 image, so pip resolution is identical. Fallback: `docker compose build` on the server, then the U3 fingerprint diff. If the server only has Apptainer: `apptainer build rein.sif docker-archive://<tar>`. | Measured at M5 |
| Rebuilt on the server | Postgres container and volume (`init-db.sql`; Raha-only runs need it too, runbook U2); `__pycache__` and egg-info; `detection_logs/`; Raha caches for **har** (R3 cold run, accepted only at exactly 110 files) and **mercedes** (only if it is run); the server-only compose override (U1: no published 5432 port, `mem_limit`, worker count; Raha's `Pool()` follows `os.cpu_count`) | — |
| Never | Rows 45, 46, 50–54; `tier_rename_backup` | ≈ 7.6 GB |

**Exclude file `~/Desktop/BA/rein-move-excludes.txt`** (anchored at the rsync source `rein-datasets/`):
```
.DS_Store
__pycache__/
/*/raha-baran-results-*/error-detection/
/*/raha-baran-results-*.truncated-*/
/har/raha-baran-results-har/
/mercedes/raha-baran-results-mercedes/
```

**Transfer:**
- **This recipe (git clone, then rsync of `rein-datasets/`) supersedes the two other transfer recipes.** HPC runbook §8 T1 (l. 264) rsyncs the repo *excluding `reports/block_d/`*, which would drop the frozen flags that V4 and the C-checks need. Server plan §3 T1 (l. 284) rsyncs `./` (≈ 4 GB) with `server_env/transfer_exclude.txt`, which does not exist, and uses `--info=progress2`.
- The Mac's rsync is openrsync (protocol 29): no `--info=progress2`, so use `-v`.
- Clone on the server first, so that the target folder exists.
- **Dry run:**
  ```
  rsync -a -n -v --exclude-from=$HOME/Desktop/BA/rein-move-excludes.txt ~/Desktop/BA/rein-benchmark/rein-datasets/ USER@HOST:SERVER_DIR/rein-benchmark/rein-datasets/ > ~/Desktop/BA/rsync-dryrun.txt; grep -c -E 'error-detection|truncated|partial|raha-baran-results-(har|mercedes)' ~/Desktop/BA/rsync-dryrun.txt
  ```
  - Expect: `0`, and "total size is" ≈ 584 000 000 bytes in the last lines.
  - **Stop** if the count is not 0.
- If the dry run is clean, run the same command without `-n`.
- ASK-5 = migrate (default), after the clone: `rsync -a -v ~/Desktop/BA/rein-benchmark/reports/robustness/runs/ USER@HOST:SERVER_DIR/rein-benchmark/reports/robustness/runs/`. Expect no error and "total size is" ≈ 23 600 000 bytes; on the server `find reports/robustness/runs -type f | wc -l` → `640`.

### 5.3 Checks on the server, from `SERVER_DIR/rein-benchmark`

| Step | Command | Expect |
|---|---|---|
| V1 | `git rev-parse HEAD && git merge-base --is-ancestor c61ee72 HEAD && echo frozen-ok` | The same SHA as the Mac's `origin/master`, then `frozen-ok` |
| V2 | `sha256sum -c ~/rein-checksums/rein-move-2026-10-13.sha256 \| grep -vc ': OK$'` | `0` (20 661 OK lines) |
| V3 | `sha256sum -c ~/rein-checksums/INPUTS.sha256 \| grep -vc ': OK$'` | `0` (12 files) |
| V4 | `docker compose run --rm rein python3 scripts/raha_cache_check.py` | 7 rows, all `complete` |
| V5 | `ls rein-datasets/har/raha-baran-results-har 2>&1 \| head -1` | "No such file or directory" |
| V6 | `docker image inspect --format '{{.Id}}' <image>` | The same ID as on the Mac (only if the image was loaded, not rebuilt) |
| then | Runbook S1–S6, U1–U4, C1–C4 + C6 (C5 only if the M3 listing order equals the server's) | As specified in the runbook |

**Before any Block D step 0 on the server:** `step0_backup.sh` and `step9_restore.sh` hard-code `backup_20261011`. Give the server snapshot its own name first.

---

## 6. ASK list (your decisions)

| # | Decision | Default | Why it matters |
|---|---|---|---|
| ASK-1 | Commit `expectations_dictionary_local.py`, or keep it untracked? | **Commit** (K1) | Without it, hand_written silently scores 0 on 8 datasets. Keep it untracked only if the suites must stay out of the public fork; then rsync it and check sha256 `5705a516…fb05`. |
| ASK-2 | Run the step-9 restore before the move? | **Yes**, after the ASK-3 freeze: dry run, then `--apply`, then dry run (F2–F4) | 8 bc/nasa files hold step-2 regenerations (`detection_results.csv` has 3 extra rows), and `build_detection_report.py` would report them. The frozen flags are in git and are not touched. |
| ASK-3 | Freeze the bike/adult Block D flag sets (step 7, including Raha run 1) on the Mac before the move? | **Yes**, as Phase 2b: F1, then commit K10, then the restore (F2–F4), all before R1 | Cached Raha reads strategies in `os.listdir` order, and the server's order will likely differ. That order alone moved beers 0.9469 → 0.9532. Run on the Mac, Raha costs about 150 s on bike and about 600 s / 18 GB on adult. Otherwise server Raha becomes a new series (†) and check 1 fails for bike/adult Raha. Without K10 the clone lacks the new flags (ignored today). |
| ASK-4 | Campaign code: keep it under `reports/` or move it to `experiments/`? | **Keep in place** | Moving means about 41 path edits in 11 files, plus 5 reports and memory notes |
| ASK-5 | Robustness `runs/` (24 MB): archive only, or migrate as well? | **Migrate** (rsync, §5.2); it stays on the Mac and in the tar anyway | The only input from which §5.2.6 can be recomputed (`mechanism.py:9` and the `raha_*.py` hard-code it). Archive only if the server will never re-run those checks. |
| ASK-6 | `keep_corrected_raha_rows.py`: archive, or move to `scripts/`? | **Archive** | Needed only to merge har run 1 into `runs_log.csv` (R4). Moving it means editing the backup path at l. 52. |
| ASK-7 | Delete `generate_openrefine_clusters.py`? | **Keep** | No thesis use. Deleting it means 3 reference edits. |
| ASK-8 | `row_level_results` CSV: leave the stale adult Raha row with a note, or patch it to 0.2262/0.8663? | **Leave + note** | The thesis already prints the correct 28 Sep values |
| ASK-9 | Candidate-dataset survey: commit or archive? | **Commit** | Back in scope now that the freeze is dropped |
| ASK-10 | `KNOWN_ISSUES.md`: archive or commit? | **Archive** | Ignored on purpose today |
| ASK-11 | Where do the `.tex` drafts belong (the thesis LaTeX project)? | Archive | — |
| ASK-12 | The remote actions R1–R10 (push, PR, merge commit, fast-forward `dev`, delete 10 remote branches, optional tag)? | Ask per step | The fallback (bundle clone) needs no GitHub change |

**Side notes:**
- The memory note `scalability-results.md` is out of date on unknown GE tiers: `detectors.py:665` now raises.
- Do not run `reports/scalability/run_all.py` beyond `--dry-run` until K8 is in.
- Server plan P0 step 2 tags `mac-reference`; this manifest creates no such tag. If you want it: `git tag mac-reference` right after K10.
- Server plan P0 step 4 writes `env/order_manifest.json`; `*.json` (`.gitignore:57`) ignores it, so it needs `git add -f`.

---

## 7. Fable 5.1 review (13 Oct)

**Verdict:** ready after fixes. Nothing in the DELETE or ARCHIVE rows loses thesis or Block D material. Every correction was checked against the source, read-only, and all 10 were accepted: 7 as given; 6 and 10 with one wrong detail corrected; 9 with part of its evidence rejected.

| # | Correction | Result | What changed |
|---|---|---|---|
| 1 | `server_plan_2026-10-13.md` has no verdict | Accepted. 20 918 B, 10:58, `git check-ignore -v` → `.gitignore:27`, not in K7. | Row 67; K7; line 5 |
| 2 | Scratchpad analysis code is nowhere | Accepted. 13 files under `/private/tmp/…/scratchpad/{hpc,harmerc,edit}`; HPC l. 73, 232, 340 and server plan l. 62 cite them. The target keeps the subfolders because `hpc/posdiff.py` and `harmerc/posdiff.py` differ. The copy is moved up to B0, because `/private/tmp` can be wiped and B0 also gets them into the tar. | Row 68; B0; K7 |
| 3a | ASK-3 outputs have no commit | Accepted. `reports/block_d/flags/bike/raha.csv` is ignored (`.gitignore:27`). | Row 69; K10 + check (21 flag files) |
| 3b | Restore before freeze is wrong | Accepted (`step0_backup.sh` l. 3–6, `step9_restore.sh` l. 22–32). Expected cache diffs become 4 (bike/adult `detection.dataset`), or 2 without ASK-3. | Phase 2b F1 → K10 → F2–F5; §5.1 step 1; ASK-2/3 |
| 4 | B4 count is stale | Accepted. Recount = 1516 (diff to the earlier list: this file and the server plan). With B0: 1529. | B4/B5 expectations and stop rules |
| 5 | The fallback merges onto a stale master | Accepted. `master` 734ae25 is 66 behind `origin/master` c52c769, and `origin/master` is not an ancestor of HEAD. The trees of c52c769 and 6978997 are identical, so the merge is clean. | Fallback step 1 (`--ff-only`) + ancestry check |
| 6 | K5 still ignores new `.json`/`.log` in the plan folder | Accepted, verified by my own scratch-repo simulation. **Wrong detail:** the addendum re-run would *not* leave `measure_fixes.json` untracked; that file and the other addendum outputs are tracked already (`git ls-files`), so changes to them show up anyway. The rule matters only for new files. | K5 diff + 5 more checks |
| 7 | Three transfer recipes disagree | Accepted. HPC l. 264 excludes `reports/block_d/`; server plan l. 284 uses a missing `server_env/transfer_exclude.txt` (no `server_env/` exists). | Supersede note in §5.2; K7 message |
| 8 | Phase 0 "not in the tar" sentence is false | Accepted. `detection_logs/` 654 + `robustness/runs/` 640 = 1 294 of 1 516; the tar is 0.036 GB before compression. | Sentence rewritten; B5 size; row 23 (652 + 2 records = 654) |
| 9 | K1/K8: suites comment, mtime note | Comment fix accepted (`expectations_dictionary.py:48–50`). Mtime 2 Oct 18:29 confirmed. **Evidence rejected in part:** the 29 Sep `ge_tier_sweep` predates that mtime, so it cannot show that this version reproduces the Sep runs. Only the 11 Oct bc/nasa replay ("identical", after the mtime) does. No hand-written run on another dataset postdates the mtime (latest `detection_results.csv` rows: 14–16 Sep). | Row 12; K1 message; K8 = 6 files |
| 10 | ASK-5: migrate, not only archive | Accepted. **Wrong detail:** the 3 Oct verification recomputed the 60 knob-1 runs from `runs/`, not all 160 (memory note robustness-experiment). | Row 30; ASK-5 default = migrate; rsync command in §5.2; payload +0.024 GB |

**Also re-checked here, no change:** W2a count 70 (66 `__pycache__` + 4 `.DS_Store`), 0 tracked; the stash is `fad54bb`; all 9 local branches are in `git branch --merged origin/master`; the worktree has 6 untracked drafts and 0 own commits; K2 = 12, K6 = 25 and the old K7 = 33 files exist; the rsync payload is 20 825 files / 0.584 GB; the checksum manifest is 27 + 1 + 20 633 = 20 661.

**Own edits beyond the review:** W2b is written out in full, with `-prune`, so `find` does not descend into folders it is deleting. Two side notes in §6 cover the `mac-reference` tag and `env/order_manifest.json`.

**Counts after the review:** KEEP 15, COMMIT 19, PROMOTE 4, ARCHIVE 18, DELETE 7, ASK 6 rows. K7 = 47 files (56 with the survey), K8 = 6, new K10. Migrated ≈ 0.94 GB.
