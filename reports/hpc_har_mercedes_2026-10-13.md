# har and mercedes on the 1 TB server: decision report (13 Oct 2026)

Built from four investigator reports (cost, thesis, validity, HPC) of 13 Oct, then revised the same day after a fact-check and an examiner review. Every number used was re-checked against the file named; §11 lists what was corrected. **The recommendation changed from option E to D+.** "est." = estimate, with its derivation. Memory in decimal GB. "l." = line of `thesis.txt` (pdftotext of the current PDF) unless another file is named.

## 1. Answer

**Recommended now: option D+.** Text changes only, no server runs before the 15 Oct freeze. Add a sensitivity line to Table 7 and fix the passages that the server makes inaccurate (§7a). Keep both datasets out of the evaluation tables.

**Later, only if all three hold:**
1. Block D is frozen.
2. The supervisor approves, in writing, a window after the freeze.
3. The caveats of §4 are applied.

Then har may enter as a marked extension (option E′, §3). mercedes stays out of the evaluation tables in every case.

- **Why not now.**
  - Block D gate 1 was due Mon 12 Oct noon (`block_d_final_plan_2026-10-09.md` l. 298, 305). The repo holds no driver (`scripts/` has only `blockd_check_format_only.py` and `blockd_freeze_flags.py`), no core run and no gate-1 entry. §16 of the plan ends on 11 Oct, and the last commit on any branch is 17f416c (11 Oct 16:49).
  - 15 Oct has twice been used as the cut-off for all experiments, not only Block D: the LLM detectors (memory note `thesis-rq-structure.md`) and the five REIN candidate datasets (`reports/rein_candidate_datasets_2026-10-07.md` l. 14).
  - The old fallback (option C) also misses the freeze, because the mercedes cold run alone takes 8–25 h (est., §5).
  - Writing is the real limit: Ch. 1–4, 6, 7 and the abstract are still template text (l. 81–82, 203, 218, 284, 307, 1476, 1487).
- **What D+ buys.**
  - It replaces the weakest current claim. "A comparison of all five configurations is impossible there" (l. 348) is already false, because Figure 3 compares all five on har up to 63 000 rows and on mercedes up to 151 columns.
  - It answers the first examiner question, "does excluding them flatter Raha?", with a measured sensitivity line (§7).
- **har (later, E′):**
  - Tables 3, 8 and 10 get a marked row below a rule.
  - In Table 9, Raha's cell reads "OOM (33.6 GB)", with the server runtime and peak in a footnote.
  - Table 7 stays on seven datasets; the 8-dataset variants are sensitivity lines only.
  - A har mechanism paragraph must carry the §5.2.6 format caveat (§4). Raha does not succeed on har by reading the row, so conclusion 1 stays "on adult".
- **mercedes:** stays out of Tables 3, 8, 9 and 10. Two reasons hold; the earlier "ρ = 1" and "nothing new for RQ1" do not (§4):
  1. **Cost.** The cold run takes 8–25 h and a ten-run cached batch 1.5–5 days (both est., Mac speed).
  2. **Column order.** Raha's labels depend on it: the positional diff is 668 163 cells against 301 972 real errors, and a detector that copies those labels scores F1 0.6225. Raw files would contradict §5.2.5's aligned 0.9998. Aligned files would leave smartfactory as the only unaligned Raha row, which in effect reopens the 25 Sep decision.

  A server c100 point in §5.2.5 is possible only if at least 36 h remain before an agreed cut-off.
- **Block D / RQ3: no change.** The prediction is frozen in c61ee72.

## 2. What the 1 TB machine changes, and what it does not

**Changes**
- The stated exclusion reason goes away. §5.1.1 says Raha does not complete "within the 32 GB" (l. 345–350). har needs ≈ 41 GB and mercedes ≈ 100–210 GB (both est., §5).
- FDX can run on the full mercedes table (§5.2.5 footnote 2: the table "exceeds the memory", l. 1199–1202). It will likely still find no constraints (est.). On 25 % samples it gave "Non SPD" at sparsity ≤ 0.2 and empty output above that (memory note fdx-profiler-limits).
- The image runs natively on x86-64, so server runtimes are not comparable with Table 9 or Figure 3. The Mac ran an amd64 image under emulation on Apple Silicon. The thesis does not say so anywhere: thesis.txt contains no "emulat", "amd64" or "x86".
- Raha's pool size follows the host's CPU count. `multiprocessing.Pool()` is called without an argument (raha/detection.py:188 in the 1.26 copy in the uv cache). The image pins 1.25 (requirements.txt:142), so re-read that file inside the image before citing the line.

**Does not change**
- The 33.6 GB ceiling remains a valid finding for the workstation. The Mac has 34.36 GB of RAM (`hw.memsize` 34 359 738 368). Docker gets all of it (setting `MemoryMiB` = 32768, i.e. 34.36 GB), and 33.6 GB of that is usable by the containers. "On this machine…" in §5.2.5 stays true.
- How Raha grows:
  - In rows it grows quadratically, because of clustering.
  - In columns, profiling grows quadratically and feature generation ≈ columns³. The latter is a single-threaded Python loop over columns × strategies × flagged cells, after `run_strategies` in detection.py.
  - On mercedes the limit becomes time, not memory. More cores speed up profiling only.
- The data defects: mercedes' column order; har's 665 artifact cells and the format fingerprint of its errors (§4).
- Block D: the prediction is frozen (c61ee72) on four datasets. har is a clustering task (excluded 6 Oct), and mercedes has ρ = 1.

## 3. Options

Compute and user time are estimates; compute is at Mac speed.

| Option | Content | Server compute | User time | Risk | Likely examiner view |
|---|---|---|---|---|---|
| A Full inclusion | 9 datasets everywhere; 9-dataset Table 7 as primary | har 1.5–3.2 h + mercedes cold 8–25 h + 10 cached 35–120 h + FDX 1–6 h ≈ 2–6.5 days | 1.5–2 days (~25 passages) | High: misses the freeze; Raha's first place by FG1 hinges on mercedes | "Why does an oracle artifact on one dataset decide your ranking?" |
| B Marked extension, both | Both below a rule in Tables 2/3/8/9/10 and Fig. 2; Table 7 on 7, with 9 as sensitivity | As A; 14.5–46 h ≈ 0.6–1.9 days if mercedes gets 1 cached run and no Table 10 row (har 1.5–3.2 h + mercedes cold 8–25 h + one cached iteration 3.5–12 h + FDX 1–6 h) | ~1.5 days | Medium-high: mercedes timeline + alignment | Transparent; mercedes needs a long caveat |
| C §5.2.5 only | har r100, mercedes c100 as marked server points | har 0.2–1 h, mercedes 8–25 h, calibration 1–2 h | 3–4 h | Low, but misses the freeze (mercedes) | "You had the server; why is har not evaluated?" |
| D No change | — | 0 | 0 | l. 348 stays false (Figure 3 contradicts it) | Same question, weaker answer |
| **D+ (recommended now)** | Text only: §7a edits, Table 7 sensitivity line incl. infeasible = 0, one limitations sentence | 0 | 1–2 h | Low | "Access came two days before the freeze; the limit is measured; the ranking's dependence on memory is stated" |
| E har as B, mercedes as C | Earlier recommendation | har 1.5–3.2 h + mercedes cold 8–25 h + calibration 1–2 h | 1–1.5 days (~47 edits, plus Figure 2 (h), Figure 3 and Table 8's lower panel to redo) | Medium: its precondition (Block D gate 1) is not met, and it needs a post-freeze exception | Server used where it adds evidence |
| **E′ (conditional, after Block D)** | har as B on top of D+; mercedes out (c100 only under the 36 h rule) | har series r10–r100 ≈ 1.4–2 h + har protocol 1.5–3.2 h + calibration 1–2 h | ≈ 1 day | Medium: second machine and §5.2.6 caveat | Acceptable if marked and approved |

## 4. Validity: mercedes' column order, har's artifacts

**mercedes**
- clean.csv ends with `ID,y`; dirty.csv starts with them (checked today). Raha builds its training labels from its own positional dirty-vs-clean diff (`Dataset.get_actual_errors_dictionary`, dataset.py:90–94, detection.py:295).
- Recount today (csv module, stripped strings):
  - The positional diff is **668 163** cells. By column name it is **301 972** (= actual_errors.csv, 18.98 %).
  - All true errors are inside the positional set; 366 191 of its cells are not errors (merc_extras.py).
- A detector that copies Raha's labels scores P 0.452, R 1.0, **F1 0.6225**, FG1 0.858 (computed). On smartfactory the copy scored 0.0358 and the real run 1 0.0360.
- **Raw-file Raha, est. F1 0.62–0.71.** The upper end applies if Raha learns that a 1 in a binary column is an error: all `1` cells plus the other extras give F1 0.714. The HPC report's guess, "near the baseline 0.319", has no support.
- **Error profile (description only, not a reason for exclusion).** 368 of 378 columns are 0/1.
  - 299 448 of 301 972 errors (99.2 %) are floats in 0/1 columns, and 300 291 (99.4 %) are floats in any column.
  - Of the 301 091 errors in 0/1 columns, 99.5 % are floats (recount today, clean aligned by name).
- **Two reasons dropped.**
  - "ρ = 1": beers and soilmoisture also have ρ = 1 and are in Table 3 (Table 2, l. 383–384); they are only excluded from the row level.
  - "Nothing new for RQ1": smartfactory, whose errors are all blanks, is kept. Both arguments would read as cherry-picking.

**The scalability 0.999 does not transfer to the original files.** scalability_driver.py:66–68 reorders clean.csv by name before writing scratch copies, at every fraction including 1.0. §5.2.5 already reports aligned mercedes Raha (FG1 0.9998, l. 1275–1276), so the asymmetry is in the current draft whatever is decided.
- Footnote for §5.2.5: describe only what was done to the files ("clean table reindexed onto the dirty column order, as for the ground truth in Section 5.1.1"). Say nothing about Raha's labels; the 25 Sep decision for nasa/bike/smartfactory stays closed.
- §5.1.1 defect 1 (l. 354–359) names only smartfactory. mercedes has the same column-order difference, and its Table 2 values are the reindexed ones: ε 0.1898 = 301 972 / 1 591 002, against 668 163 positionally. Add "and mercedes" (part of D+).

**har**
- Positional diff = actual_errors.csv, 51 845 = 51 845 (recounted today): Raha's labels are correct.
- 665 `null` gt cells count as errors: 640 `nan` texts from `astype(str)` in `inject_errors`, plus 25 blanks (`reports/gt_flags_bc_har_2026-10-08.md` l. 90–99).
  - Without them, ε is 0.1462 and ρ 0.5556, and clean-profiled falls below dirty-profiled (FG1 0.662 vs 0.667, ibid. l. 106–113).
  - Every profiled-tier claim on har needs this caveat.
- 12 058 of 51 845 errors (23.3 %) sit in Index, and scoring counts every cell.
- **Format fingerprint: the artifact §5.2.6 describes** (l. 1359–1366: "too good to reflect detection ability"; Raha separates injected values "by their length alone"). Recount today, csv module; har's dirty and clean files have the same column order:
  - Length: 19 201 of the 41 345 non-blank error values (46 %) are longer than any clean value in their column. That is 37 % of all 51 845 errors (10 500 errors are blank; the clean maximum lengths are 5/12/12/10/5).
  - Decimals: 19 739 of the 40 705 non-blank numeric errors (48.5 %, `nan` texts excluded) have more decimals than any clean value in their column.
  - Index: 10 030 of 10 030 numeric errors have decimals, in an integer column.
  - z: 9 709 of 10 167 (95 %) have 8–9 decimals; the clean maximum is 7.
  - x: 94.9 % of errors have 8–9 decimals, against 28.8 % of clean cells.
  - y: 89.9 % of errors have 9 decimals, against 4.3 % of clean cells.
  - Consequence: Raha's har score (F1 0.87–0.98, scalability rows) mostly measures this fingerprint, not reading values in context. Any har mechanism paragraph needs the caveat, and conclusion 1 must not say "on adult and har".
  - The fingerprint is **not** a reason to keep har out of Table 7 specifically. bike, which is in Table 3, carries the same full-precision fingerprint: 73.5 % of its non-blank errors are longer than any clean value in their column (recount today; already parked by the robustness session on 2 Oct). The reasons for keeping Table 7 on seven datasets are the single-machine protocol and timing.
- Cache `rein-datasets/har/raha-baran-results-har/strategy-profiling`: 49 files from 20 Aug 16:44–16:46 (OD 13, RVD 10, PVD 25, KBVD 1).
  - A complete cache has **110**: RVD 20 + OD 34 + KBVD 1 + PVD 55. The PVD count comes from the characters in dirty.csv: Index 12, x 12, y 13, z 12, gt 6.
  - The cache is truncated, and Raha would load it silently. Do not transfer it.

## 5. Cost and schedule

Mac speed, 10 workers. The server's speed factor is unknown until C3/C4. The server runs natively, not emulated, so it is likely faster (not measured).

| Quantity | Estimate | Derivation |
|---|---|---|
| har cold run | 11–64 min | Lower: 349.9 s at 49 000 rows (results.csv l. 113) × (70/49)^1.77–2.35 = 660–810 s. Upper: 3 109 s at 63 000 (l. 115) × (70/63)² = 3 840 s. The 948 → 3 109 s jump between 80 % and 90 % was probably memory pressure (not verified), so without a memory limit the lower end is more likely (est.). |
| har peak | ≈ 41 GB | 32.95 GB × (70/63)² = 40.7 GB. The condensed distance matrix alone is 2.45e9 entries × 8 B = 19.6 GB; with linkage's working copy ≈ 39 GB. |
| har cached iteration | 7–13 min | Adult warm iteration on the complete cache, 530–610 s (memory note raha-truncated-caches-adult-smartfactory), × (70 000/45 222)² = 2.4 for rows × 5/15 for columns = 7–8 min. Cross-check: har r70 cold 349.9 s × (70/49)² ≈ 714 s ≈ 12 min. The upper end is better supported. (The earlier base, "adult clustering ≈ 6 min", came from the truncated adult cache, where 8 of 15 columns skipped linkage.) |
| har protocol (cold + fresh batch of 10) | 1.5–3.2 h, most likely 2–3 h | 11–64 min + 10 × 7–13 min |
| har row series r10–r90 (Figure 3 on the server) | ≈ 1.4 h at Mac speed | Sum of the Mac runs in results.csv l. 107–115: 5 116 s |
| mercedes cold run | 8–25 h, most likely 15–25 h (tail ≈ 35 h) | **(a)** 9 132 s at 151 columns (l. 125) × (378/151)^2.0–2.5 = 15.9–25.2 h. A log-log fit over the four points gives exponent 2.21 and 18.3 h. **(b)** Profiling 148 077 strategies at 9.1–22.9/s = 1.8–4.5 h, plus a feature loop of 3.6e11 iterations × 30–100 ns = 3–10 h, plus 0.5–2 h for the rest: 5–17 h in total. **(b) is optimistic:** the memory note scalability-results.md puts the 151-column run's profiling at 16:43–18:41 (≈ 3.5/s for ≈ 24 900 strategies; not re-derivable, since the detection logs have no profiling timestamps). At 3.5/s, profiling alone takes 11.8 h and (b) becomes 15–24 h. Nothing shows that (a) overstates: only the 151-column run hit the limit (33.04 GB, l. 125). The 113-column run peaked at 21.69 GB (l. 119), and the 76 → 113 step already had exponent 2.50 (ln(4591/1704)/ln(113/76)), against 2.37 for 113 → 151. The tail of 35 h needs an exponent of 2.87, above every measured step, so it is a pessimistic bound. |
| mercedes peak | 100–210 GB | 33.04 GB × 2.503^1.27–2.0 |
| mercedes cached iteration | 3.5–12 h | The feature loop reruns every iteration (cost report) |
| mercedes ten-run batch | 35–120 h | 10 × the above |
| mercedes disk | ≥ 100 GB free | The cache is ≈ 7 GB for 148 077 files (the partial cache holds 1.19 GB in 25 262 files). The `detection.dataset`/cache ratio is 4.7–7.4× on six narrow datasets but 0.82× on soilmoisture, the only wide one (129 columns), measured with du/ls on the `raha-baran-results-*` folders. The ratio therefore does not transfer to mercedes; 100 GB is a safe margin either way. |
| FDX full mercedes | 1–6 h, 25–50 GB | 6 sparsity values × 10–60 min (cost report) |

**Profiling rates.** The 25 262 partial files were written 18:11:31–18:57:53 on 14 Sep (2 782 s), which is 9.1/s. The first 8.5 min of that run held 11 702 files, which is 22.9/s.

**Where the investigators disagreed.** On cold runs they gave har 10 min–1.1 h and mercedes 8–40 h. The table covers mercedes up to 25 h (tail 35 h), so 40 h lies outside it. For har, 10 and 66 min fall just outside 11–64 min. The spread comes from whether the Mac's last points were inflated by memory pressure.

**Block D status.** §16 of `block_d_final_plan_2026-10-09.md` (l. 361 ff.) ends on 11 Oct (steps 0 and 2, D6, the addendum). The newest Block D file is the plan itself (11 Oct 16:49); the addendum outputs in `checks/addendum_raha_run1/` are from 16:38. The last commit on any branch is 17f416c (11 Oct 16:49). The repo holds no driver, no core run and no gate-1 entry, and the only repo file newer than 11 Oct 17:00 is this report. Gate 1 was due Mon 12 Oct noon (§12), so Block D is at least one day behind and stays the critical path. Its lever is the plan's own fallback (§12: "core late at the gate → bike and adult dropped"), not the server.

| When | Action |
|---|---|
| Now (13–15 Oct) | Block D only. D+ text edits (1–2 h, est.). S1–S6 read-only server checks (10 min). Send the §9 questions to the supervisor. No server runs. |
| After the Block D freeze, only with a written window from the supervisor | M1–M5, T1–T3, U1–U4, C1–C4 + C6 (user ≈ 2 h, compute ≈ 1–2 h; stop rules §8). Then the har series and har R3/R4 (E′). |
| Only if ≥ 36 h remain before the agreed cut-off | mercedes c100 cold, §5.2.5 only |

## 6. Comparability and calibration

- **Cold Raha should be identical on both machines.** The feature order comes from `random.shuffle` (seeded by the datawig import), `pool.map` keeps order, and NumPy is seeded with 42. Last-bit SIMD float differences remain possible.
- **Cached runs read strategies in `os.listdir` order** (detection.py:150–152), which is filesystem-specific. Order alone moved beers from 0.9469 to 0.9532 and nasa from 0.4297 to 0.4396 (memory notes raha-strategy-order-changes-results, raha-seeded-by-datawig-import).
  - Build har's cache on the server and report run 1 of a fresh cached process there, as on the Mac.
  - Disclose in §5.2.4 that this run 1 depends on the server's file order and cannot be reproduced on the study machine.
- **Calibration** (driver, cold, scratch copies; pass = identical TP/FP):
  - C1 breast_cancer vs its detection_results.csv l. 33 (TP 318, FP 89, 8.5 s).
  - C2 nasa vs l. 32 (731 / 1 864, 5.8 s).
  - C3 adult vs results.csv l. 106 (865 / 5 081, 1 217 s, 23.16 GB).
  - C4 har r10, har r50 and mercedes c10 vs l. 107, 111 and 117.
  - **C5** (cached batch of 10 on the bc/nasa caches that were rsync'ed over) is an identity test **only if** the M3 listing order equals the server's `os.listdir` order. Otherwise it is informational and not part of the stop rule.
  - **C6** re-runs har GE ×3 and HoloClean on the server (seconds each); they must be identical to `har/results/detection_results.csv` l. 2–5. This makes the har row single-machine. It also re-checks the untracked hand-written suite file `expectations_dictionary_local.py`, modified 2 Oct 18:29, after both the 14 Sep har rows and the 26 Sep full-har rows (results.csv l. 11, 26, 41, which matched them).
  - Speed factor = Mac runtime ÷ server runtime, per axis. It is never used to rescale.
- **Workers:** pin 10. `--cpuset-cpus=0-9` does not change `os.cpu_count()` in Python 3.8, so the pool needs an override (e.g. a `sitecustomize.py` patching `os.cpu_count`; untested). Document it as a deviation, and set the BLAS thread variables too.
- **Memory:**
  - Read the container's `memory.peak` (cgroup v2, kernel ≥ 5.19), as on the Mac. `/usr/bin/time -v` is not equivalent.
  - Set `mem_limit` = `memswap_limit`, given in bytes (e.g. 900000000000 = 900 GB). Docker's `900g` suffix is binary and means ≈ 966 GB.
- **Reporting:** server values carry a † (CPU, cores, workers, native x86-64) and get their own series in Figure 3. Add an environment paragraph stating that the Mac runtimes were measured under amd64 emulation.

## 7. Thesis changes

### 7a. D+ (now; ≈ 1–2 h, est.)

- **l. 345–350:**
  - "within the 32 GB available to the container" → "within the 33.6 GB of the study machine".
  - Delete or correct "a comparison of all five configurations is impossible there" (l. 348). Figure 3 compares all five on har up to 63 000 rows and on mercedes up to 151 columns.
- **l. 354–359 (defect 1):** add "and mercedes" (§4).
- **l. 1097:** "killed by the operating system at 32 GB" → 33.6 GB.
- **l. 1103:** "set by Raha's feasibility" → "set by Raha's feasibility within the 33.6 GB of the study machine".
- **l. 1120:** "exceeds 32 GB" → 33.6 GB.
- **l. 1177, Figure 3 label l. 1237:** "31.3 GiB (33.6 GB)" / "31.3 GiB memory limit" → 33.6 GB (thesis convention).
- **l. 1201:** footnote 2, "the full table exceeds the memory" → "exceeds the memory of the VM".
- **l. 1317–1319:** "Only Raha has a limit within the sizes of this study" → "within 33.6 GB"; qualify "which set the evaluation set in Section 5.1.1" the same way.
- **After l. 937, a Table 7 sensitivity paragraph.** State the convention for a configuration that cannot run, then give the values from the table below:
  - With Raha's largest feasible fractions, the order by mean FG1 is unchanged.
  - With Raha's failures scored FG1 0 and last place, the hand-written suite is first by both aggregations: 8 datasets 0.757 vs 0.695 and 1.50 vs 2.88; 9 datasets 0.784 vs 0.617 and 1.44 vs 3.11.
  - Frame it under RQ2: Raha's quality lead depends on the memory available.
  - The primary Table 7 and l. 918, 927, 930, 932 and 936 stay as they are.
- **One limitations / future-work sentence:** a 1 TB server became available two days before the freeze. har (≈ 41 GB, est.) and mercedes (≈ 100–210 GB, est.) would fit there. It was not used, in order to keep the single-machine protocol.

### 7b. E′ only (har after Block D, approved window)

- **§5.1.1 / Table 2:**
  - Move har into the evaluation block, marked, with a footnote on the 665 cells and the second machine.
  - mercedes stays under a renamed header ("Scalability experiment only").
- **§5.1.2:** no change (har ρ − ρ̂ = +0.0083 is inside the stated range).
- **§5.2.1:**
  - l. 529 "all seven" → eight.
  - l. 533–534 "six of the seven" → six of eight.
  - l. 536 "Raha leads on adult … six of the seven" → "adult and har … seven of eight".
  - l. 538–539 "(on soilmoisture it flags nothing)" → "on soilmoisture and har".
  - l. 803 "remaining six datasets" → seven.
  - Add Figure 2 panel (h).
  - Add one mechanism paragraph: outliers inside legal ranges, hand-written recall 0.432 (har detection_results.csv l. 4), Raha F1 0.87–0.98 and FG1 0.975–0.996 across 10–90 % rows (results.csv l. 107–115). It must carry the §5.2.6 format caveat with the §4 numbers.
  - **Conclusion 1 (l. 943–947) stays "as Raha does on adult".**
  - Table 7 primary stays on seven datasets.
- **§5.2.2 / Table 8:**
  - l. 985 "five datasets with ρ < 1" → six.
  - Add a har row (row F1 / FG1, har detection_results.csv l. 2–5): dirty 0.423 / −0.736, clean 0.440 / −0.618, hand 0.689 / 0.426, HoloClean 0.000 / undefined, Raha from the server; baseline 0.718.
  - Statements that become false, because HoloClean flags nothing on har:
    - the heading "HoloClean flags every clean row." (l. 1006);
    - "flags every clean row on all five datasets" and "exactly 0.500 on four of them" (l. 1008);
    - "every clean row of every dataset" (l. 1018).
  - Recompute "Raha … from 0% to 95%" (l. 1020–1021) and Table 8's lower panel.
- **§5.2.3 / Table 9:**
  - Add a har row: expectations 10 / 10 / 6 (from the full-size GE logs), FDs 4, DCs 0, GE 0.15–0.23 s, HoloClean 0.93 s.
  - Raha's cell reads **"OOM (33.6 GB)"**, with a footnote giving the server time and peak. Table 9 is RQ2 cost on the study machine.
  - Check the runtime notes (l. 1043–1051) and l. 1086–1091 ("from 6 seconds on nasa to 20 minutes on adult", "two to eight times faster"), which stay true if Table 9 keeps OOM.
  - l. 1063 "six of the seven" → six of eight.
  - l. 1065–1075: add the effort estimate for writing har's hand-written suite.
  - Add "0.03 % of har".
  - l. 1094–1104: both datasets fail within 33.6 GB; on the server har completes with X GB.
- **§5.2.4 / Table 10:**
  - Add a har row (ten cached runs on the server), with the file-order disclosure from §6.
  - l. 1146–1148 "complete cache, verified by counting": the har cache must hold 110 files.
  - l. 1152: recount "the other five datasets".
  - Re-verify "run 1 equals a standalone run" (l. 1144) on the server.
- **§5.2.5:**
  - l. 1167 "seven evaluated" → eight.
  - Show the har row series r10–r100 on the server as **its own series** with its own marker, not as a single point on top of the Mac's OOM marker.
  - Footnote 1 (l. 1195 "ran alone"): state whether the server was shared, and its load.
  - Keep l. 1295–1296 ("as the run approaches the memory limit") only if the server's r90/r80 ratio is lower than the Mac's 3.3; otherwise delete it.
  - Re-word the REIN comparisons in l. 1296–1299 (3.5 h) and l. 1320–1323 (50 000-row recommendation) as relative to hardware.
  - Add the "aligned scratch copies" footnote for mercedes (§4).
- **Ch. 3 deviations (currently a stub).**
  - Add the second machine (spec, workers, native).
  - Change Block D's scope from "4 of 7 datasets" to "4 of 8". That wording is planned in memory note proposal-rq-and-success-criterion.md; it is not in thesis.txt.
  - Say that Block D's selection criteria were applied to the seven datasets before har was added. har has an activity label (`gt`), so expect "why not classification?". Answer: REIN defines har as a clustering task, and clustering was excluded. c61ee72 stays untouched.
  - Citation: the examiner reports that REIN cites har wrongly and that the source is Stisen et al. 2015, UCI dataset 344 (not verified here).
- **(A/B only):**
  - mercedes rows in Tables 3, 9, 10 and Figure 2 (i).
  - The column-order text of §4.
  - A HoloClean FDX re-run.
  - "258 expectations on soilmoisture" → 751 on mercedes.

**Provisional ranking.** Columns show mean FG1 (negative or undefined = 0) / mean rank by F1. Verified by running `rank.py` on `results/runs_log.csv` and the har/mercedes `detection_results.csv`, extended today with the infeasible variants.
- Raha's har/mercedes values are not full-table results: har uses 90 % of the rows (results.csv l. 115), mercedes 40 % of the columns, aligned (l. 125).
- In the "infeasible = 0" columns, Raha gets F1 0 and FG1 0 and is placed last (5). If it instead shares the places with HoloClean's F1 0 on har, its rank is 2.81 (8 datasets) and 3.00 (9).

| Configuration | 7 (Table 7) | 8 = +har, largest fraction | 8, har Raha infeasible = 0 | 9 provisional | 9, mercedes Raha = copy of its labels | 9, mercedes Raha = 0 | 9, both infeasible = 0 |
|---|---|---|---|---|---|---|---|
| Raha | **0.794** / 2.57 | **0.817** / 2.38 | 0.695 / 2.88 | **0.837** / 2.33 | **0.821** / 2.33 | 0.726 / 2.61 | 0.617 / 3.11 |
| GE hand-written | 0.739 / **1.57** | 0.757 / **1.63** | **0.757** / **1.50** | 0.784 / **1.56** | 0.784 / **1.56** | **0.784** / **1.56** | **0.784** / **1.44** |
| GE clean-profiled | 0.557 / 3.00 | 0.573 / 3.00 | 0.573 / 2.88 | 0.509 / 3.06 | 0.509 / 3.06 | 0.509 / 2.94 | 0.509 / 2.83 |
| HoloClean | 0.506 / 3.86 | 0.443 / 4.00 | 0.443 / 3.88 | 0.394 / 4.11 | 0.394 / 4.11 | 0.394 / 4.06 | 0.394 / 3.89 |
| GE dirty-profiled | 0.378 / 4.00 | 0.413 / 4.00 | 0.413 / 3.88 | 0.367 / 3.94 | 0.367 / 3.94 | 0.367 / 3.83 | 0.367 / 3.72 |

- **Largest fractions:** the top two stay as in Table 7 (Raha first by FG1, hand-written first by rank). The agreement on the last three weakens to a tie (HoloClean and dirty-profiled both at 4.00).
- **Infeasible = 0:** the hand-written suite leads by both measures, so the finding "disagree on the top two" (l. 932–937) disappears. With nine datasets, clean-profiled also ranks ahead of Raha by mean rank.
- **With mercedes:** Raha's first place by FG1 depends on how mercedes is handled.

## 8. Runbook skeleton (E′ only; one command at a time)

- **Mac:**
  - M1 image architecture = amd64.
  - M2 fingerprint (cpu_count, NumPy config, pip freeze).
  - M3 listdir order of the bc and nasa caches.
  - M4 sha256 of dirty/clean for har, mercedes, adult, nasa, bc.
  - M5 `docker save | gzip`.
- **Server, read-only:**
  - S1 `uname -m` (stop unless x86_64), kernel, `nproc`, `free -g`, `lscpu`.
  - S2 `cgroup2fs`.
  - S3 Docker/Compose versions.
  - S4 ≥ 100 GB free.
  - S5 load, port 5432, Slurm.
  - **S6** `/proc/sys/vm/overcommit_memory` and `ulimit -v`. With overcommit = 2 or a ulimit, NumPy raises MemoryError instead of being killed, and Raha's bare `except: pass` around `linkage` (detection.py:238–250) swallows it. Raha still prints "A hierarchical clustering model is built", so the column silently goes without clustering.
- **Transfer:**
  - T1 `rsync`, excluding `reports/block_d/`, `*/error-detection/`, both `raha-baran-results-{har,mercedes}/` and `__pycache__`. The untracked `rein/auxiliaries/expectations_dictionary_local.py` must arrive.
  - T2 `docker load`.
  - T3 `sha256sum -c`.
- **Setup:**
  - U1 server-only compose (no published port, `mem_limit` in bytes, 10-worker override).
  - U2 start the db. Raha-only runs need a reachable Postgres: `run_detectors` and the driver call `db_table_exists_postgresql` → `psycopg2.connect` (datasets.py:785, 810).
  - U3 diff the fingerprint.
  - U4 check that `memory.peak` is readable.
- **Calibration:** C1–C4 and C6 (§6), with C5 only under its condition. Any TP/FP mismatch in a cold run means stop; do not debug.
- **Pre-check before R3:** a 5-min synthetic `linkage(method="average", metric="cosine")` test at 70 000 rows inside the image (SciPy 1.7.1, requirements.txt:152). The condensed matrix then has 2.45e9 entries, above 2^31; the 63 000-row run had 1.98e9. 64-bit index handling in SciPy 1.7.1 average linkage is not verified, and any failure would be swallowed (S6).
- **Production:**
  - R1 back up har/mercedes `detection_results.csv`, `results/runs_log.csv` and `reports/scalability/results.csv`.
  - R2 driver har rows r10–r100 as a server series. Pass `--out` (required) pointing to a **new server CSV**, never `results.csv`, because the plots keep the last row per fraction.
  - R3 har cold run in the real folder, `--n_iterations 1` (Table 9 footnote runtime). The log must not say "I just load". **Accept only if** the cache holds exactly 110 files (RVD 20, OD 34, KBVD 1, PVD 55), a separate per-column linkage probe (as on 23 Sep) shows clusters for all five columns, and stderr has no MemoryError. Abort after 3 h (≈ 3× the upper estimate).
  - R4 fresh `--n_iterations 10`; the log says "I just load". Run 1 → Table 3, all ten → Table 10, row level → Table 8.
  - R5 driver mercedes cols 1.0, aligned (§5.2.5), only under the 36 h rule.
  - Copy results back; never copy server caches into the Mac folders.
- **Results hygiene:**
  - Do not use `reports/scalability/run_all.py` beyond `--dry-run`. It does not pass `--out`, which the driver now requires, so every run would exit with code 2 and append an `exit_2` status row to results.csv. It also retries `oom_killed` fractions.
  - `scripts/build_detection_report.py` takes the latest row per detector, which after a batch is iteration 10, not run 1.
  - Figure 2 and Table 7 come from `results/runs_log.csv`, which has no har row. Merge run 1 only, after a backup.

**Stop rules.**
1. No server work until Block D gate 1 has passed and the extension runs (bike, adult) have started or been dropped.
2. From the first SSH login to C1 and C2 passing: at most 3 h of user time, otherwise stay with D+.
3. Any mismatch in a cold calibration run: stop, do not debug.
4. The har cold run is accepted only under the R3 conditions above.
5. Agree one cut-off date for server numbers with the supervisor. Start mercedes c100 only if at least 36 h remain before it.

## 9. Open questions

1. Supervisor: was the access meant for including har/mercedes, or for the scalability section and future work?
2. Supervisor: may second-machine results enter Tables 3, 8 and 10 as † rows, or only §5.2.5? Is a window after the 15 Oct freeze acceptable, and until when? The freeze has so far been applied to all experiments, so E′ needs an explicit exception.
3. Server: x86_64? Docker + Compose with docker-group access, or Apptainer/Slurm only? Job time limit? Shared or exclusive? How should the machine be acknowledged in the thesis?
4. Block D: gate 1 is overdue. Apply the plan's fallback (bike and adult dropped)?
5. Workers: pin to 10 (recommended, comparable) or use all cores (faster profiling, different memory)?
6. Proposal to the supervisor: mercedes for scalability only; har's Raha score with the §5.2.6 caveat; Table 7's primary ranking stays on seven datasets. Confirm.
7. har's 665 cells: footnote only, ground truth unchanged (recommended). Confirm.

## 10. What an examiner would ask if har and mercedes stay out (D+)

- **"You had a 1 TB machine; why not use it?"** Access came two days before the freeze, the protocol uses one machine, and §5.2.5 measures the limit.
- **"Does excluding them flatter Raha?"** Point to the infeasible = 0 sensitivity line (§7).
- **"Isn't 'comparison impossible' contradicted by Figure 3?"** Yes; it is fixed in D+ (l. 348).
- **"Does §5.2.6's artifact apply to har?"** Yes; give the §4 numbers. It also applies to bike, which is already in Table 3.
- **"Why are the mercedes copies aligned?"** They use the same reindexing as the ground truth in §5.1.1.

## 11. Verification (13 Oct, after fact-check and examiner review)

Every correction below was re-checked against the primary source before it was applied.

**Corrected numbers**
- mercedes floats: "99.4 % … in 0/1 columns" → 99.2 % (299 448 / 301 972). 99.4 % (300 291) is floats in any column. Recount with the csv module, clean aligned by name.
- har lengths: "46 % of error values" → 46 % of non-blank errors (19 201 / 41 345), 37 % of all 51 845.
- mercedes note (a): only the 151-column run hit the limit (33.04 GB, l. 125). The 113-column run peaked at 21.69 GB (l. 119), and the 76 → 113 exponent is 2.50. The claim "(a) likely overstates" is removed, and the range is now 8–25 h, most likely 15–25 h.
- Block D: the newest file is 11 Oct 16:49 (the plan), not 16:13. The addendum outputs are from 16:38 (`stat`).
- Profiling rate: 9.2/s → 9.1/s (18:11:31–18:57:53 = 2 782 s); 22.9/s for the first 8.5 min (file mtimes).
- Investigator ranges: the claim that the table "covers" 40 h for mercedes and 10–66 min for har is corrected.
- mercedes disk: the "5–6×" ratio is replaced by measured 4.7–7.4× (narrow datasets) and 0.82× (soilmoisture).
- Option B: "≈ 1–1.5 days" → 14.5–46 h (0.6–1.9 days), the sum of its own parts.
- Thesis wording in §7:
  - "4 of 7" comes from a memory note, not from thesis.txt.
  - The actual wording is "(on soilmoisture it flags nothing)", l. 538–539.
  - The heading at l. 1006 was added.
- §7 "Raha 0.81–0.98" was the recall range; F1 is 0.872–0.977 and FG1 0.975–0.996.
- Mac memory: 34.36 GB physical, all of it given to Docker (setting `MemoryMiB` = 32768), 33.6 GB usable by the containers.
- `mem_limit` is given in bytes; Docker's `900g` means ≈ 966 GB.

**Caveats added**
- har cached iteration: the base was the truncated adult cache. It is now 7–13 min, and the protocol 1.5–3.2 h.
- mercedes (b): the 3.5/s profiling rate comes from a memory note only.
- C5 is not a pass/fail test unless the listing orders match.
- The Pool line is cited from the 1.26 copy; the image pins 1.25.

**Examiner points: applied**
- Recommendation changed from E to D+ now and E′ later (point 1): verified that the gate is overdue, that no driver or later commit exists, that the 15 Oct cut-off has been applied twice, and that the chapters are template text.
- Infeasible = 0 sensitivity (point 3): recomputed with rank.py.
- Table 7 stays on seven in §7 (point 4).
- mercedes reasons (point 5): ρ = 1 and RQ1 reasons dropped; "and mercedes" added for defect 1; Table 2's ε confirms it is reindexed.
- Table 9 "OOM (33.6 GB)" and the missed passages (point 6).
- S6, the linkage pre-check and the R3 acceptance criteria (point 7): verified the bare except at detection.py:238–250, 2.45e9 > 2^31 and SciPy 1.7.1 at requirements.txt:152.
- C5 and C6 (point 8): verified the listdir use and the suite file's mtime of 2 Oct 18:29.
- Figure 3 as a separate server series (point 9): verified the r10–r90 sum of 5 116 s and l. 1295–1296.
- Missed passages (point 10): verified the 110-file cache count from dirty.csv characters.
- Number fixes (point 11).
- D+ (point 12), stop rules (point 13), supervisor questions (point 14), examiner questions (point 15).

**Examiner points: applied with changes**
- Point 2: the har fingerprint is confirmed (decimals recount 19 739 / 40 705, examiner 19 741). The conclusion-1 edit is deleted and the caveat added. The fingerprint is **not** used as a reason to keep har out of Table 7, because bike in Table 3 carries the same one (73.5 %, recount today).
- Point 11: the claim "a driver run without `--out` appends to results.csv" is outdated. The driver now requires `--out` (scalability_driver.py:113), and the real hazard is `run_all.py`, which does not pass it. Also: 299 449 → 299 448.

**Not verified:** the har citation (Stisen et al. 2015, UCI 344); 64-bit index handling in SciPy 1.7.1 linkage; the 3.5/s profiling rate of the 151-column run.
