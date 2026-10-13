# Is clean.csv a real ground truth? smartfactory, mercedes, soilmoisture, har

Date: 2026-10-07. Repo files were only read; nothing under REPO was changed.
DL = `/Users/ghassen.aicha@caronsale.de/Desktop/BA/REIN DATASETS`. Scripts are in SCRATCH (`sf_*.py`, `me_*.py`, `sm_*.py`, `har_*.py`).
"Measured" means computed with pandas on the downloaded original and on `REPO/rein-datasets/<ds>/clean.csv`. "Inference" is marked as such.

## Summary

| dataset | original used by REIN (measured) | clean.csv vs original | real issues already in clean.csv (measured) | verdict |
|---|---|---|---|---|
| smartfactory | Kaggle inIT-OWL, **HRSS_anomalous_standard.csv** (one of 4 files) | transformed: `Timestamp` dropped, headers lowercased, **1,828 non-integer cells (1,288 rows) rounded** to integers, rounding half away from zero | 160 exact duplicate records; 16,644 rows (70.4 %) identical to the previous row; 121 feature vectors with conflicting labels (847 rows); 15 negative power/voltage cells; 5,670 rows (24 %) are documented anomalies | **(b)** raw source assumed clean, plus a lossy rounding step |
| mercedes | Kaggle competition `train.csv` (from 3 GitHub mirrors with the same git blob) | **identical**, only the column order differs (`ID`, `y` moved to the end); 0 differing cells | 0 MVs; 12 constant columns; 56 duplicate binary columns; 298 rows whose 376 features repeat an earlier row (217 groups, y spread up to 58.6); y = 265.32 lies 13.0 σ out (13 y values > 4 σ) | **(b)** raw source assumed clean |
| soilmoisture | GitHub felixriese `soilmoisture_dataset.csv` (= Zenodo v1.0.0, same sha256) | **identical up to formatting**: datetime turned into Unix seconds (UTC), 125 bands rounded to 9 decimals (max abs diff 5.0e-10), 73 `x.0` changed to `x` | none found: 0 NaN, 0 duplicates, 0 constant columns, 0 cells > 4 σ, reflectance 0.032-0.301; 3 rows were already removed by the authors (index 46, 47, 199) | **(b)** assumed clean, but with **no detectable real errors** (closest of the four to a real ground truth) |
| har | **NOT Anguita 2013.** It is UCI 344 *Heterogeneity Activity Recognition* (Stisen et al., SenSys 2015), `Phones_accelerometer.csv`, rows 14999-84998 | transformed: 70,000-row slice (user a, phone nexus4_1, 0.54 % of the file); 5 of 10 columns dropped; x and y formatted to 9 decimals (max abs diff 5e-10); Index and gt identical, original order kept | 665 labels are `null` (HHAR's "no activity" class), which pandas reads as NaN, so the ground truth has 665 missing labels (0.95 %); otherwise 0 duplicate rows and 1 cell > 4 σ | **(c)** wrong citation, and the 665 `null` labels end up in actual_errors.csv |

None of the four is (a) a verified ground truth. In every case REIN took the published file as clean. Three of them were also reformatted or sliced, and smartfactory was rounded in a way that changes its values.

---

## 1. smartfactory

### Download (measured)
- URL: `https://www.kaggle.com/api/v1/datasets/download/inIT-OWL/high-storage-system-data-for-energy-optimization`. No login was needed: HTTP 200 with a redirect to a signed storage.googleapis.com URL.
- `DL/smartfactory/original/smartfactory_kaggle.zip`: 1,127,297 B, sha256 `764c173a2fcdfcda7e06bacb594194fc954d2da55d7bf37260e31c9b79a9ffe1`.
- Contents (file dates 2019-10-02):
  - `HRSS_anomalous_standard.csv`: 1,939,822 B, sha256 `0d69fa66…62aa4`, 23,645 × 20
  - `HRSS_anomalous_optimized.csv`: 1,638,517 B, sha256 `3d89abb6…b533`, 19,634 × 20
  - `HRSS_normal_standard.csv`: 2,114,036 B, sha256 `a14a648b…8cb3`, 25,907 × 20
  - `HRSS_normal_optimized.csv`: 1,770,780 B, sha256 `5c30d801…fcf`, 21,329 × 20
- The Kaggle description was saved as `kaggle_dataset_metadata.json`. It says "HRSS_anomalous_standard.csv contains runs with failures and not optimized" and that the *Label* column marks the rows with anomalies.

### Alignment (measured)
- Only `HRSS_anomalous_standard.csv` has 23,645 rows, which matches clean.csv and REIN Table 4. Row order is the same.
- `clean.csv` is that file with three changes:
  1. the `Timestamp` column is dropped;
  2. the headers are lowercased (`Labels` becomes `labels`);
  3. **every one of the 1,828 non-integer cells (1,288 rows) is rounded to an integer**, half away from zero (29269.5 → 29270, -71.5 → -72; checked on all cells: clean equals sign(x)·floor(|x|+0.5)). Example: 13841.6611570248 → 13842. clean.csv has 0 non-integer cells.
- Classification: **transformed (lossy)**. The rounding changes 1,828 original values. The labels are unchanged (17,975 × 0, 5,670 × 1).

### Real issues in the original that are now "clean" (measured)
- **Duplicates.**
  - 160 exact duplicate records, including the same Timestamp, all inside the same run. These are double-logged samples.
  - Once Timestamp is dropped, 16,644 of 23,645 rows (70.4 %) equal the previous row (sample-and-hold logging), and 16,523 rows duplicate an earlier row in all 19 columns.
- **Label ambiguity.** 121 distinct feature vectors carry both label 0 and label 1. They cover 847 rows.
- **Impossible-looking values.** 15 negative cells in power or voltage columns, where every other power/voltage column has minimum 0:
  - `o_w_blo_voltage`: 7 cells, minimum -113
  - `o_w_bhl_voltage`: 7 cells, minimum -22
  - `o_w_bhl_power`: 1 cell, -4315
  - 14 of the 15 sit in label-1 (anomaly) rows. One (row 20337, voltage -13) is labeled 0 and sits right before a label-1 block, which looks like an imprecise label boundary.
- **Documented anomalies inside the ground truth.** 5,670 rows (24 %) are machine failures by design (label 1, one anomaly segment per run, 106 runs). By the benchmark's own outlier rule (> 4 σ), clean.csv already holds 1,226 outlier cells in 648 rows. Most are `o_w_hr_voltage` (611) and `o_w_hl_voltage` (598) peaks, and 435 of those rows are labeled 0. Any outlier detector that flags them counts as a false positive.
- **No MVs.** 0 NaN in the original.

### Inference: the anomalies look synthetic
- Non-integer values occur only in the two anomalous files (1,828 and 1,727 cells). Both normal files have 0.
- The fractional parts cluster at .2, .4, .6 and .8 (928 of 1,828 cells), and also include values like .6611570248 (= 80/121).
- 17,899 of 17,975 label-0 rows and 4,069 of 5,670 label-1 rows appear verbatim in `HRSS_normal_standard.csv`.
- So the "anomalous" file looks like normal runs with an altered segment per run. REIN's rounding partly erases exactly those altered values.

### Verdict
**(b) Raw source taken as clean by assumption, after a lossy rounding.**
- Known real issues: 160 duplicate records (certain), 847 rows with ambiguous labels, 15 negative power/voltage cells, and 5,670 documented anomaly rows that clean.csv treats as correct data.
- The 1,828 rounded cells mean clean.csv is not even byte- or value-faithful to the source.

---

## 2. mercedes

### Download (measured)
- The Kaggle competition API without credentials returns **401**: `https://www.kaggle.com/api/v1/competitions/data/download/mercedes-benz-greener-manufacturing/train.csv.zip`. The competition data needs a login plus acceptance of the rules.
- Mirror used: `https://raw.githubusercontent.com/subhadipml/Mercedes-Benz-Greener-Manufacturing/HEAD/train.csv`, saved to `DL/mercedes/original/train.csv`.
  - 3,220,873 B, sha256 `6d6016d51b25bf4b112640786f85f41e88c3740baf82663d636a237f8965ea8f`.
- Cross-check: three independent GitHub repos (subhadipml, Suvojit-tapadar, manishnanwani) hold the same git blob `5e1916458066d19b7f9b124994c78430e7a25daa`. A second download from manishnanwani (`train_mirror2_manishnanwani.csv`) has the same sha256.
- Shape is 4,209 × 378. REIN's "4210" is the line count including the header.
- Caveat: this was not checked byte-for-byte against Kaggle itself. For that, the user must download it manually from https://www.kaggle.com/c/mercedes-benz-greener-manufacturing/data while logged in.

### Alignment (measured)
- Same 378 columns and same row order. clean.csv only moves `ID` and `y` from the front to the end.
- After reordering the columns, a string-level comparison of every cell gives **0 differences**.
- Classification: **identical (column order only)**.

### Real issues in the original (measured)
- **Missing values:** 0 NaN.
- **Constant columns:** 12 (X11, X93, X107, X233, X235, X268, X289, X290, X293, X297, X330, X347).
- **Duplicate columns:** 56 binary columns duplicate an earlier column (45 of them among the 356 non-constant binary columns).
- **Near-constant columns:**
  - 18 binary columns have exactly one minority value, and 44 have at most 5.
  - `X4` is 4,205 × 'd', with a, b, c appearing only 2, 1 and 1 times.
- **Duplicate configurations:** 298 rows repeat an earlier row's 376 features (excluding ID and y), in 217 groups covering 515 rows. Their y differs (median spread 5.34 s, maximum 58.56 s). This is natural measurement noise or unobserved factors, not a cell error, but it caps the achievable regression accuracy.
- **Target outlier:** y = 265.32 is 13.0 σ above the mean (next highest: 169.91). 13 y values are more than 4 σ out, the same threshold the benchmark's injector uses.

### Verdict
**(b) Raw competition data taken as clean, unchanged.**
- No cell-level errors are documented. Its structural defects are constant and duplicate columns, plus one extreme target outlier (265.32) that a detector would rightly flag but the ground truth counts as a false positive.

---

## 3. soilmoisture

### Download (measured)
- GitHub: `https://raw.githubusercontent.com/felixriese/hyperspectral-soilmoisture-dataset/c6710683a9/soilmoisture_dataset.csv`, saved to `DL/soilmoisture/original/soilmoisture_dataset.csv`.
  - 1,696,782 B, sha256 `ca62b37cc0c7549fdf966382cffac7b0fd701ee9b6d8cbf04f806da96dd1f42f`.
  - The file was committed only once (`657d5d0`, 2018-04-24, "Initial commit"), so it is unchanged since publication.
- Zenodo record 1227837 (v1.0.0, 2018-04-24): `zenodo_hyperspectral-soilmoisture-dataset-v1.0.0.zip`.
  - 752,766 B. Its md5 `bc27ce82a36feac20e23ab2f7997ce7a` matches the checksum Zenodo publishes. sha256 `3b749ef7…1c1660`.
  - The CSV inside has the **same sha256** as the GitHub file.

### Alignment (measured)
- Same shape (679 × 129), same columns and order, same row order.
- Three differences:
  1. `datetime` "2017-05-23 14:06:17" became the Unix epoch 1495548377. This matches the timestamp read as UTC for all 679 rows; read as Europe/Berlin it would be off by 7,200 s.
  2. The 125 spectral bands are rounded to 9 decimals: all 84,875 cells equal `round(orig, 9)`, max abs diff 5.0e-10, max relative diff 1.2e-8.
  3. 4 `soil_moisture` and 69 `soil_temperature` values lost a trailing `.0`; they are numerically equal.
- Classification: **identical up to formatting** (precision loss below 1e-9).

### Real issues in the original (measured)
- 0 NaN, 0 duplicate rows, 0 duplicate spectra, 0 duplicate timestamps, 0 constant columns.
- Reflectance lies in [0.0323, 0.3009]: no negative values and none above 1.
- 0 cells beyond 4 σ (spectra, soil_moisture, soil_temperature). soil_moisture is 25.5-42.5 %, temperature 26.4-47.1 °C.
- **Not errors, but worth knowing:**
  - The file consists of about 29 blocks with a 2-minute cadence, from 5 days in May 2017, stored in non-chronological order. The big jumps in soil_moisture (for example 25.56 → 42.5) happen at block boundaries.
  - Index values 46, 47 and 199 are missing, so the authors removed 3 rows before publishing. Inference: some curation took place, but it is not documented.

### Verdict
**(b) Assumed clean, but no real errors were detected.**
- This is a curated research dataset (KIT, Zenodo DOI) with no detectable defects. It is the closest of the four to a trustworthy ground truth, though nobody independently verified it.

---

## 4. har

### Download (measured)
- `https://archive.ics.uci.edu/static/public/344/heterogeneity+activity+recognition.zip`, saved to `DL/har/original/heterogeneity+activity+recognition.zip`.
  - 822,098,071 B, sha256 `8c9f8dd5f50074feaad2c5cec5d927a4fc8366324de26079629a3de3aef0e124`.
- It contains `Activity recognition exp.zip` (777,127,275 B, sha256 `d4c0c53b…46582`) and `Still exp.zip` (not extracted).
- Extracted to `DL/har/original/Activity recognition exp/`:
  - `Phones_accelerometer.csv`: 1,291,856,387 B, sha256 `d56abf2b26077cd6661100812eec9bf8d6bf109685c617e2697ea8482610307c`, 13,062,475 data rows
  - `Watch_accelerometer.csv`: sha256 `509ace75…74f0`
  - `readme.txt`
- Note: DL/har now takes 3.0 GB. The inner zip and the watch file can be deleted if space matters.

### Which source it really is (measured)
- Local har: columns `Index,x,y,z,gt`; labels `stand`, `sit`, `null`; vector magnitude 9.34-10.75 (m/s², gravity).
- In `Phones_accelerometer.csv`, the line `14999,…,-5.767761,0.37147522,8.16629,a,nexus4,nexus4_1,stand` is file row 14,999 (0-based). Comparing rows 14,999-84,998 (70,000 rows) with clean.csv:
  - `Index`: identical, including its non-monotonic original order (2,292 backward steps in both).
  - `gt`: identical (40,164 stand, 29,171 sit, 665 null).
  - `x`, `y`: equal after rounding to 9 decimals (max abs diff 5e-10; 2 cells show half-away-from-zero rounding). `z` max abs diff is 1.8e-15.
  - The slice contains a single user (`a`), model `nexus4` and device `nexus4_1`.
  - Dropped columns: Arrival_Time, Creation_Time, User, Model, Device.
- **So the local har is a contiguous 70,000-row slice of HHAR (Stisen et al., "Smart Devices are Different", SenSys 2015; UCI id 344).** It covers 0.54 % of the phone-accelerometer file, 1 of 9 users, 1 of 8 phones and 2 of 6 activities.
- REIN's reference [4] (Anguita et al. 2013) is UCI id 240, "Human Activity Recognition Using Smartphones": 10,299 instances according to the UCI API. According to its documentation it has 561 engineered features, upper-case labels (WALKING, SITTING, …) and accelerations in g. None of that matches the local file.
- **The citation is wrong. The right reference is Stisen et al. 2015 / UCI HHAR.** REIN Table 4's "70000 × 4, 3 num + 1 cat" matches x, y, z, gt with Index left out.

### Real issues in the source slice (measured)
- **665 `null` labels (0.95 %).** HHAR uses `null` as its "no activity" class. They form one contiguous block (Index 55163-55827) between the stand and sit segments, and their mean x, y, z equals the stand posture, so this is an unlabeled transition.
  - The benchmark reads clean.csv with pandas defaults (`rein/datasets.py:82`, `rein/models.py:431` with `.dropna()`), so these 665 labels become **NaN, that is, missing values in the ground truth**.
  - In dirty.csv, exactly those 665 rows hold `nan` (640) or `''` (25). `nan` appears nowhere else in dirty.csv.
  - All 665 cells are listed in `actual_errors.csv`. They make up 24 % of the 2,752 "errors" in the gt column, and they come from a text artifact (`null` → `nan`), not from injection. That part is an inference about the generator; the counts are measured.
- 0 duplicate rows (ignoring Index), 0 duplicate Creation_Time values. The 3,005 repeated (x, y, z) triples are sensor quantization, not errors.
- Only 1 cell is beyond 4 σ, and magnitudes are physically plausible for static postures.
- The dropped Creation_Time column has a 36-hour clock jump (5 gaps > 1 s). It does not affect clean.csv.

### Verdict
**(c) Something else.**
- The dataset is mis-cited: it is HHAR (Stisen 2015), not Anguita 2013.
- Apart from that, it is a raw slice taken as clean (case b), with 665 source labels that act as missing values and are counted as injected errors.

---

## Side observations (outside the question, not investigated further)
- **soilmoisture:** the authors' README reads the file with `index_col=0`. REIN keeps both `index` and `datetime` as features (`excluded_attribs: []`), and dirty.csv injects errors into them (204 and 203 cells).
- **mercedes and smartfactory:** dirty.csv differs from clean.csv as text in far more cells than the error rate suggests (668,163 cells for mercedes, 388,997 for smartfactory, at string level). Inference: this is float formatting (`0` vs `0.0`) rather than errors. It is known from earlier audits and was not re-checked here.
