# Soccer (REIN [35], European Soccer Database): download, reconstruction, real errors, fit

Date: 7 Oct 2026. Nothing under REPO was touched. Scripts are in `SCRATCH/soccer/` (explore1-3.py, profile.py, profile2.py, candidates.py, samples.py, wr.py).

## 0. Verdict

**Recommendation: case study only, not in the evaluation set and not in Block D.**
Use the numbers below as a ground-truth finding (C1 / threats to validity). REIN's soccer `clean.csv` is a raw scraped table. It still carries measurable real errors. REIN's own rule for soccer (FD `player_name -> birthday`) is false on that clean table.
Do not add the dataset before the 15 Oct freeze. The reasons are in section 6.

## 1. Download (verified)

| item | value |
|---|---|
| URL used | `https://www.kaggle.com/api/v1/datasets/download/hugomathien/soccer`. No credentials were needed: HTTP 200 after a redirect to a signed `storage.googleapis.com/kaggle-data-sets/63/589/bundle/archive.zip` |
| local zip | `DL/soccer/soccer_kaggle.zip`, 34,297,253 B, sha256 `5a59c60f417faf2a7b2b57af9e6220da97ff0eaa6bedeea465848e1c2bb60cdb` |
| extracted | `DL/soccer/database.sqlite`, 313,090,048 B (zip entry dated 2019-09-19), sha256 `4df8569777d59fdd690754b1cc8ca1f7989baf65f2eaddd0f1368285f11139a9` |
| tables (rows) | Player 11,060; Player_Attributes 183,978 (42 cols); Match 25,979; Team 299; Team_Attributes 1,458; League 11; Country 11 |

**REIN author repos (checked via the GitHub API, recursive trees):** rein-benchmark, SAGED, AutoCure, ReClean, RTClean, DiffClean, D3Bench, data_cleaning_with_latent_operators, DiffSelect, DVBench, XAI2Clean, Data-quality-Dashboard, DataLens, Haipipe and SEED.
- None of them ships a soccer `clean.csv` or `dirty.csv`. SEED's "soccer" hits are unrelated Wikipedia league tables.
- SAGED only names soccer in `scripts/exp_scalability.py` and in its README ("Soccer (scalability)").
- A GitHub code search for the merged header and for "soccer dirty.csv clean.csv" returned nothing.
- **So REIN's dirty soccer file (error rate 0.27) is not public. Its injected errors cannot be reproduced.**

## 2. Reconstruction of REIN's 180,228 x 44 table (verified, exact)

```python
m = pd.merge(Player, Player_Attributes, on=['player_api_id', 'player_fifa_api_id'])  # inner: 183,766 x 47
rein = m.dropna().drop(columns=['id_y', 'attacking_work_rate', 'defensive_work_rate'])  # 180,228 x 44
```

- **Rows: 180,228, exact.** The double-key join drops 212 Player_Attributes rows of 9 players whose `player_fifa_api_id` differs from the Player table. `dropna` then removes 3,538 rows.
- **Columns: 44, exact. The split is 40 numeric + 4 categorical, also exact.**
  - Categorical: `player_name`, `birthday`, `date`, `preferred_foot`.
  - Numeric: `id_x`, `player_api_id`, `player_fifa_api_id`, `height`, `weight`, `overall_rating`, `potential` and 33 skill attributes.
- **REIN's own code points the same way.** `rein/detectors.py` (soccer NADEEF config) uses the column `id_x`, which only exists after a pandas merge with Player on the left. Its FDs are `player_name -> birthday` and `id_x -> player_name`. Its patterns cover the 35 ratings, `weight`, `id_x`, `birthday`, `date` and `preferred_foot`, and nothing for the work-rate columns.
- **The order matters:** the columns must be dropped after `dropna`. Dropping them before gives 181,139 rows.
- **Alternatives that do not fit:**
  - A join on `player_api_id` only gives 180,354 x 48.
  - `Player_Attributes.dropna()` gives 180,354.
  - `PA.dropna().drop_duplicates([fifa_id, date])` also gives 180,228, but it is a different row set (72 rows differ) and does not explain the columns.
- **What remains unexplained:**
  - **The error rate 0.27 belongs to REIN's injected dirty file, which we do not have.**
  - REIN's NADEEF patterns expect integers (`^\d+$`) and `m/d/yyyy` dates. The raw data written by pandas gives `67.0` and `2016-02-18 00:00:00`: 0 of 180,228 dates match REIN's regex. So REIN's clean.csv was post-processed (cast to int, dates reformatted), or NADEEF flagged every date and rating cell. This cannot be verified.
  - Table 4 lists the error types as "Implicit MVs, rule violations, outliers, MVs". The dictionary lists `[missing_values, outliers, rule_violation, typos]`. The two lists do not match.
- Derived file: `DL/soccer/derived/soccer_rein_reconstructed.csv` (34.7 MB, ratings cast to int, raw date format, sha256 `95d011bc...189b`).

## 3. Profile: real errors (verified, measured)

### 3a. In the REIN 44-column table (what REIN treated as clean)

| check | rows | cells | confidence |
|---|---|---|---|
| Explicit NULLs | 0 | 0 | all removed by `dropna` |
| Exact duplicate rows; duplicates on `(id_x, date)` or `(fifa_id, date)` | 0 | 0 | none |
| Snapshot identical to an earlier one of the same player except `date` | 45,541 | – | not an error: the rating did not change |
| Ratings outside [1, 99] | 0 | 0 | none (min 1, max 98) |
| **Age at snapshot < 16** (min 7.8 years). 2,886 of the 2,894 rows are on the placeholder date 2007-02-22, which every one of the 10,410 players has | 2,894 | 2,894 | high: impossible timestamp |
| **`player_name` with a ",NN" suffix** (e.g. "Alberto Luque,21"), 55 players | 617 | 617 | high: scraping artifact |
| **`potential < overall_rating`** (gap 1-16, 528 players; 427 of the rows are in 2007) | 1,022 | 2,044 | medium: it is unclear which of the two cells is wrong |
| Isolated `preferred_foot` flip A,B,A | 37 | 37 | medium |
| Isolated `overall_rating` / `potential` spike (>= 10 from both neighbours, which agree within 3) | 12 / 18 | 30 | medium |
| Players whose foot changes at all | 1,094 players (978 switch once) | 4,300 minority-foot rows | low: one switch may be a genuine update |
| **REIN's FD `player_name -> birthday` violated** | 145 names, 5,551 rows | – | **the rule is false**: these are homonyms, i.e. distinct people (`(name, birthday)` is unique in Player) |
| `id_x ->` name / birthday / height / weight / fifa_id | 0 | 0 | the FDs hold |
| Height 157.5-208.3 cm (inch-converted), weight 117-243 lb, BMI 17.9-30.9 | 0 | 0 | plausible |
| \|z\| > 4 per column | – | 3,343 | not errors: 2,641 of them are goalkeeper attributes. The 14,416 goalkeeper rows make gk_* bimodal; the rest are ID ranges and top players |

- **High confidence alone:** 3,501 rows (1.94 %), 3,511 cells (0.044 % of 7.93 M).
- **High + medium:** 4,575 rows (2.54 %), 5,621 cells (0.071 %).
- Cell list: `derived/soccer_rein_real_error_candidates.csv`.

### 3b. Real errors that REIN's preprocessing threw away (raw Player_Attributes)

| issue | rows / cells |
|---|---|
| All 35 ratings NULL: placeholder rows that duplicate a populated row with the same `(player_api_id, date)` (835 groups; 736 of them on 2007) | 836 rows |
| Only the 7 newer attributes NULL (volleys, curve, agility, balance, jumping, vision, sliding_tackle) | 1,877 rows / 13,139 cells. Structural MNAR, all in 2007-2010; absent in early FIFA versions |
| **Work-rate junk** | **6,981 rows with ratings, 1,154 players, 1,135 of whom have junk in every snapshot**. Details below the table |
| FD `player_api_id -> player_fifa_api_id` violated: entity-link error, PA attaches another player's FIFA id (e.g. "Alex" 150396 carries Miguel Rosa's 192635); 7 FIFA ids map to two players | 9 players, 212 mismatching rows |

Work-rate junk in detail:
- `attacking_work_rate`: NULL 2,394, 'None' 3,639, and split fragments 'norm' 348, 'y' 106, 'le' 104, 'stoc' 89.
- `defensive_work_rate`: '_0' 2,394, 'o' 1,550, digits '0'-'9' 2,232, and split fragments 'ormal', 'es', 'ean', 'tocky'.
- The fragments are one token ("normal", "yes", "lean", "stocky") split across two columns. This is a real column-shift error.

Cell list: `derived/soccer_raw_dropped_error_candidates.csv` (7,884 distinct rows). Per-check counts: `derived/soccer_profile_summary.csv`.

## 4. Ground truth

- **No clean version of this data exists anywhere. The Kaggle file is a raw scrape (sofifa), and it carries the errors listed in section 3.**
- If REIN used the reconstructed table as `clean.csv`, that is the only reading consistent with the paper ("injecting errors into real-world datasets"). Consequences:
  - At least 1.9 % of rows (2.5 % with medium confidence) carry real errors that are labelled clean. A detector that finds them is charged false positives.
  - REIN's preprocessing silently removed the most interesting real errors: the junk and implicit-missing work rates, the placeholder duplicates and the entity-link errors.
  - REIN's NADEEF FD `player_name -> birthday` fires on 5,551 clean rows by construction.
  - The REIN soccer F1 values (Raha 0.98, NADEEF 0.93, ED2 0.83) therefore measure detection of injected errors only, on a "clean" base that is not clean.
- To use the real errors as ground truth, we would have to define the truth ourselves:
  - The true value is known only for the name suffix (strip it).
  - It is unknown for junk work rates, wrong dates and potential < overall. Which cell is wrong in potential < overall is also ambiguous.
  - That gives a detection-only ground truth defined by the same rules a hand-written GE suite would encode. This is circular for GE.

## 5. Fit for this benchmark

### Size versus cost

The cost of the full table (180,228 x 44, 7.9 M cells) is computed or inferred from the earlier measurements:

- **Raha.** Clustering needs about 8·n² B per column: 260 GB at full size, against the measured row ceiling of about 60-63k rows at 31 GB.
  - At 10k rows this is 0.8 GB, at 5k rows 0.2 GB.
  - Strategy profiling grows with columns. 44 columns lies between mercedes 38 (433 s, 5.7 GB) and 76 (11.5 GB), but at 2-2.4x more rows. **A 10k x 44 run is plausibly 10-20 GB and ~1 h. This is an extrapolation, not measured; it needs one probe.**
  - REIN itself: Raha and ED2 "stopped working at a data fraction of 50%", and HoloClean "is terminated with 90%".
- **GE:** linear in rows; fine even at full size.
- **HoloClean:** inferred to be fine at 10k. FDX on 44 columns may need `--sample_frac`.

### ML task (Block D)

- `overall_rating` regression is well posed. OLS on the 33 skills gives in-sample R² 0.78, and 0.84 with `potential`.
- But every player appears about 17 times (median 17, max 56), so splits must be grouped by player.
- The Block D design is already fixed (4 datasets, gates on 11 and 15 Oct). **Soccer cannot join it.**

### What is new

These error types are not yet covered:
- real token-type implicit missing values (`None`, `_0`, `o`)
- column-split fragments
- placeholder duplicates on `(player, date)`
- entity-link (FK) errors
- impossible temporal values
- natural cross-column rules (potential >= overall)

But almost all of these are in the columns and rows that REIN dropped. They have no true values, so they would need our own detection-only ground truth.

### Samples

Measured real-error candidate rows kept by each sample design:

| sample | rows | high | high + medium |
|---|---|---|---|
| random 10k | 10,000 | 176 | 245 |
| 580 players, all snapshots | 10,190 | 181 | 261 |
| earliest snapshot per player | 10,410 | 2,931 | 3,155 |
| latest snapshot per player | 10,410 | 55 | 55 |

A sample is the only feasible form. A player-grouped sample keeps the temporal and entity checks.

## 6. Integration effort before 15 Oct, and the reasons for the recommendation

Effort per option (estimates, inference):
- **A. REIN-like:** a sample as clean.csv, our own injected errors, a dictionary entry, a 44-column hand-written GE suite, FDX DCs and 5 configuration runs.
  - About 1.5-2.5 working days, plus a Raha memory probe.
  - It adds only synthetic error types we already cover. Its clean.csv knowingly carries ~2 % real-error rows (a new C1 defect). Scale is already covered by har, adult and mercedes.
- **B. Real-error ground truth on a sample:** keep the work-rate columns and label the rule-defined errors.
  - About 2-3 days. It is circular for GE, the ground truth is ambiguous, and the risk is high.
- **C. Case study:** about 0.5 day of writing. All numbers are in this report.

**Recommendation: C. Exclude soccer from the evaluation set and from Block D.** Reasons:
1. REIN's dirty file is not public, so nothing would be comparable to REIN.
2. The full size is infeasible for Raha (REIN itself failed at 50 %), and scale is already studied.
3. A sample with injected errors adds no new error type.
4. The real errors have no true values, so a ground truth would be self-defined.
5. Block D is fixed, and the freeze is 8 days away with a gate on 11 Oct.

The case study supports two thesis points:
- REIN's soccer ground truth has real errors labelled clean: at least 1.94 % of rows at high confidence.
- REIN's preprocessing hid the dataset's genuine errors (6,981 junk work-rate rows, 836 placeholder duplicates, 212 entity-link errors), and its own FD is false on the clean data.
