# Is `clean.csv` a real ground truth? adult, breast_cancer, nasa, bike, beers

Date: 7 Oct 2026. REPO was only read. Downloads went to `DL/<ds>/original/` (plus one Kaggle mirror for adult in `DL/adult/kaggle_mirror/`).
Analysis scripts are in `SCRATCH/gt_existing_A/*.py` and use `SCRATCH/venv/bin/python` (pandas 3.0.6).
All numbers come from runs. Anything marked **[inference]** is a judgement, not a measurement.

## Short answer

| ds | How clean.csv relates to the original | Real errors still in clean.csv, treated as correct (measured) | Verdict |
|---|---|---|---|
| adult | **transformed**: UCI `adult.test` + `adult.data` (test rows first), 3,620 rows with `?` dropped, `.` removed from test labels, income recoded `<=50K→1`, `>50K→0`, `Trinadad&Tobago→Trinadad-Tobago` (26 cells), hyphens in column names → underscores. Reproduced cell-for-cell (45,222 × 15). | 47 redundant exact-duplicate rows (91 rows in duplicate groups); 5 feature-identical pairs with opposite labels (10 rows); 229 `capital_gain = 99999` top-code sentinels; 1 Husband/Female and 1 Wife/Male. No `?` left: the missing values were removed, not kept. | (b) raw source taken as clean, after list-wise deletion |
| breast_cancer | **identical** to `breast-cancer-wisconsin.data` (699 × 11, 0 cell differences). Only additions: a header and a pandas index column `Unnamed: 0`. | 16 `?` in Bare Nuclei (2.3 %) are kept as "clean" values; 8 exact-duplicate rows including the ID; 46 IDs repeated (100 rows), 39 with differing rows and 4 with conflicting class. | (b) raw source taken as clean, with known real errors |
| nasa | **identical up to formatting** to `airfoil_self_noise.dat` (1,503 × 6; all 9,018 cells numerically equal). Only header added and floats re-printed (`800`→`800.0`). | None measurable: 0 missing, 0 duplicate rows, 0 duplicate input vectors, all values inside the physical ranges. | (b) raw source taken as clean; no known real errors |
| bike | **transformed**: `hour.csv` (17,379 × 17). 16 columns are numerically identical (2,476 cells only re-printed, e.g. `0`→`0.0`). **`dteday` is broken**: the date was parsed with minutes in place of months, then stored as hours since 1970 in UTC+1. | 22 rows with hum = 0 (2011-03-10, while it rained); 24 rows with atemp stuck at 0.2424 (2012-08-17, temp 0.62–0.86); 2,180 rows with windspeed = 0 (12.5 %, suspected disguised missing values **[inference]**); 165 hourly rows missing altogether. cnt = casual + registered holds in all 17,379 rows. | (b) raw source taken as clean, plus one corrupted column (c) |
| beers | **identical up to formatting/join** to Hould's Kaggle "craft-cans" data: `beers.csv` joined with `breweries.csv`, whitespace stripped, numbers re-printed (cell-identical to Raha's `clean.csv`). | 1,005 empty ibu, 62 empty abv, 5 empty style; 33 duplicate beer listings (same values, different id); 7 breweries under 2 brewery_ids (e.g. `St Paul`/`St. Paul`, `Menominee`/`Menominie`). | (c) **not manually verified**: it is the dataset curator's own scripted cleanup. The dirty file was generated in code from that clean data. |

Where a published dirty version exists (verified):
- Only beers has one at a source outside REIN. Raha's GitHub `datasets/beers/dirty.csv` is byte-identical to `REPO/rein-datasets/beers/dirty.csv` (sha256 `7110bf49…0a1f68`).
- UCI and Kaggle publish only the single raw table for adult, breast_cancer, nasa and bike. Their dirty versions exist only inside REIN.

---

## 1. Downloads (provenance)

All downloads were made without credentials on 7 Oct 2026. The Kaggle API URL redirected to a signed GCS link and worked without a login.

| ds | URL | file | bytes | sha256 |
|---|---|---|---|---|
| adult | https://archive.ics.uci.edu/static/public/2/adult.zip | adult.zip | 620,237 | 7537312dd56c2b98035880805ce99e68183a30ee468aa5329d6df0fbb3cc21bb |
| | (unzipped) | adult.data | 3,974,305 | 5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d |
| | (unzipped) | adult.test | 2,003,153 | a2a9044bc167a35b2361efbabec64e89d69ce82d9790d2980119aac5fd7e9c05 |
| adult (mirror) | https://www.kaggle.com/api/v1/datasets/download/wenruliu/adult-income-dataset | adult.csv | 5,326,368 | 1f13ee2bf9d7c66098429281ab91fa1b51cbabd3b805cc365b3c6b44491ea2c0 |
| breast_cancer | https://archive.ics.uci.edu/static/public/15/breast+cancer+wisconsin+original.zip | breast_cancer_wisconsin_original.zip | 86,541 | 3f91e49bceb30c0de8ea988344357236f26ed8bd536415ac594226015b6fd84d |
| | (unzipped) | breast-cancer-wisconsin.data | 19,889 | 402c585309c399237740f635ef9919dc512cca12cbeb20de5e563a4593f22b64 |
| nasa | https://archive.ics.uci.edu/static/public/291/airfoil+self+noise.zip | airfoil_self_noise.zip | 60,126 | 5c7767ba53ad827d3f48ba1eb9434117f4892df8f10bc4c99e118a9e8a7ae07c |
| | (unzipped) | airfoil_self_noise.dat | 59,984 | 74c75fd71783f1e6b71f8a622b993dc592897a97cd689c5090a07147a1b097b3 |
| bike | https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip | bike_sharing_dataset.zip | 279,992 | b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401 |
| | (unzipped) | hour.csv | 1,156,736 | e03de4ee4ef4dc376ac6e04bf829673c6269e8eba5c60fa121640fa2f829504f |
| beers | https://www.kaggle.com/api/v1/datasets/download/nickhould/craft-cans | kaggle_craft_cans.zip | 55,121 | abbf3682f3a2cc278f9bb0899b2d7fd0f2cc14a5d84cc951823b9a213f06e1ca |
| | (unzipped) | beers.csv | 159,533 | cdbe1d9eeaad5ac2fe92510ffd45f41885820c100d27a17e0360c91a4cf6e93d |
| | (unzipped) | breweries.csv | 23,063 | 1301c2f6fbea34bc574d68eed51f8ba35e130881b8d33fe75d2c4bed4d8f1195 |
| | https://raw.githubusercontent.com/nickhould/craft-beers-dataset/master/data/processed/beers.csv | hould_github_processed_beers.csv | 159,533 | cdbe1d9e… (byte-identical to Kaggle beers.csv) |
| | https://raw.githubusercontent.com/BigDaMa/raha/master/datasets/beers/clean.csv | raha_clean.csv | 233,019 | 373227df59ad197e154dd5149125789e415019535c7223355e9486ee1b3b93de |
| | https://raw.githubusercontent.com/BigDaMa/raha/master/datasets/beers/dirty.csv | raha_dirty.csv | 255,295 | 7110bf4931a9445a1675e544d6c996817c739136239f8a2b02e088c7ec0a1f68 |

REPO files (for reference):

| file | bytes | sha256 |
|---|---|---|
| adult/clean.csv | 4,820,094 | d01a55df…782a0c |
| breast_cancer/clean.csv | 23,464 | a4feaca5…d37 |
| nasa/clean.csv | 62,487 | e0fbc276…ae6 |
| bike/clean.csv | 1,223,640 | c21fa868…80 |
| beers/clean.csv | 235,430 | 7f3391a5…340 |
| beers/dirty.csv | 255,295 | 7110bf49…a1f68 (= Raha dirty) |

`rein-datasets/` is not tracked by git in REPO (`git ls-files` returns nothing), so git history cannot show where these files came from.

---

## 2. adult [23]

### Alignment (verified)
- UCI: `adult.data` has 32,561 rows and `adult.test` has 16,281 (its first line, a comment, was skipped), 48,842 rows in total.
- `REPO/adult/clean.csv` has 45,222 rows × 15 columns. REIN Table 4 says 45,223 because it counts the header.
- clean.csv is reproduced **exactly** (45,222 × 15, every cell equal) by this recipe:
  1. Concatenate **adult.test first, then adult.data**. The Kaggle mirror `wenruliu/adult-income-dataset/adult.csv` uses this same order. It equals UCI test+train cell-for-cell (732,630 / 732,630) once the test-label `.` is removed. Its column names use hyphens (`educational-num`, `gender`), so REIN probably took this mirror **[inference]**.
  2. Drop every row that has a `?` (3,620 rows). The `?` counts are workclass 2,799, occupation 2,809, native_country 857.
  3. Recode income `<=50K → 1` and `>50K → 0`. The **positive class (1) is the low-income class**, which reverses the usual coding. Class shares: 34,014 × 1 and 11,208 × 0.
  4. Replace `Trinadad&Tobago` with `Trinadad-Tobago` (26 cells).
  5. Rename columns, replacing hyphens with underscores.
- **Category: transformed** (row deletion, label recoding, one value rewrite, column rename).

### Real errors from the source that sit inside clean.csv (measured on clean.csv)
| issue | count |
|---|---|
| `?` (missing) | 0. The 3,620 incomplete rows (7.4 % of 48,842) were **deleted**, not kept. |
| exact duplicate rows (all 15 columns, incl. fnlwgt) | 47 redundant copies; 91 rows sit in duplicate groups (44 groups) |
| same 14 features, opposite income | 5 groups / 10 rows (label noise or true ties) |
| `capital_gain = 99999` (census top-code sentinel, not a real amount) | 229 |
| `relationship=Husband` & `gender=Female` / `Wife` & `Male` | 1 / 1 |
| top-coded `age = 90` / `hours_per_week = 99` | 46 / 123 (likely censoring, not errors **[inference]**) |
| education ↔ educational_num FD | 0 violations |

The REIN-injected errors are 1,701 income flips. The duplicate and conflicting-label rows above are counted as correct in the ground truth.

---

## 3. breast_cancer [15]

### Alignment (verified)
- UCI `breast-cancer-wisconsin.data` has 699 rows × 11 columns, with no header.
- `REPO/breast_cancer/clean.csv` has 699 rows × 12 columns. The extra first column is `Unnamed: 0`, a pandas row index 0..698. REIN Table 4 reports 700 × 12, which counts the header and this index column.
- Positional comparison of the 11 real columns: **0 differing cells**. The order and string formatting are identical.
- **Category: identical** (plus a header and an index column).

### Real errors from the source that sit inside clean.csv
| issue | count |
|---|---|
| `?` in Bare Nuclei (the original missing-value marker) | **16 cells, still present in clean.csv** (2.3 % of rows) |
| how the dirty file treats those 16 cells | 13 stay `?` in dirty.csv, so the GT calls them "clean, no error". The other 3 were changed (`1`, `??`, empty), so the GT counts an error whose "correct value" is `?`. |
| exact duplicate rows (all 11 columns incl. Sample code number) | 8 (8 pairs; 3 of them on adjacent lines: 207/208, 560/561, 683/684) |
| Sample code number not unique | 46 IDs repeated, 100 rows; 39 repeated IDs have differing rows; 4 IDs carry both classes (2 and 4) |
| same 9 features with conflicting class | 0 |
| values outside 1..10 | 0 |

The 236 duplicate feature vectors (ignoring ID) are **not** errors. The features are 1–10 scores and many benign samples are all 1s **[inference]**.

Side finding (verified, outside this question): `actual_errors.csv` counts 47 injected errors in the index column `Unnamed: 0` and 60 in `Sample code number`. `datasets_dictionary.py` has no `excluded_attribs` for breast_cancer. So the GT and the models both treat a row index and a patient ID as data.

---

## 4. nasa [52]

### Alignment (verified)
- UCI `airfoil_self_noise.dat` is tab-separated with no header: 1,503 rows × 6 columns.
- clean.csv has 1,503 rows × 6 columns plus a header. REIN Table 4 says 1,504 because it counts the header.
- All 9,018 cells are numerically equal (max |diff| = 0) in the same row order. 2,171 cells differ only as strings because of float re-printing: frequency `800`→`800.0` (1,503), angle `0`→`0.0` (537), SPL `119.540`→`119.54` (131).
- **Category: identical up to formatting.**

### Real errors from the source
| check | result |
|---|---|
| missing values | 0 |
| exact duplicate rows | 0 (original and clean) |
| duplicate input vectors (5 features) | 0, so no conflicting targets |
| frequency domain | the 21 standard 1/3-octave centre frequencies (200–20,000 Hz) |
| ranges | angle 0–22.2, chord 0.0254–0.3048, velocity 31.7–71.3 (4 values), thickness 0.0004–0.058, SPL 103.4–141.0. All plausible. |

No real error was found with these checks. Measurement noise is inherent but cannot be quantified without the NASA report.

The string difference between dirty.csv (`800`) and clean.csv (`800.0`) does **not** enter `actual_errors.csv`: frequency has 138 errors, not 1,503. It affects only tools that diff strings themselves, such as Raha (see memory: raha-labels-from-positional-diff).

---

## 5. bike [16]

### Alignment (verified)
- UCI `hour.csv` and clean.csv both have 17,379 rows × 17 columns, with the same columns, the same order, and `instant` 1..17,379 in both.
- The 16 non-date columns are numerically identical. 2,476 cells differ only in print format (`0`→`0.0` and `1`→`1.0` in temp 1, atemp 3, hum 292, windspeed 2,180).
- **`dteday` is a corrupted transformation.** Original `2011-01-01` became `359399.01666666666`. Decoding (value × 3600 s since 1970-01-01, +1 h) gives, for all 17,379 rows:
  - the year equals the true year;
  - the **month is always January**;
  - the **minute equals the true month**;
  - the day equals the true day.

  So the date was parsed with a minute directive in place of the month (`%M` instead of `%m`) and converted to epoch hours in UTC+1 **[the exact call is an inference; the mapping is verified]**.

  The encoding is still one-to-one (731 dates → 731 values), but it is not monotone in time. 2011-02-01 encodes to Jan 1 + 2 min. dirty.csv uses the same encoding rounded to 4 decimals (`359399.0167`).
- **Category: transformed** (one column re-encoded wrongly, others re-printed).

### Real errors from the source that sit inside clean.csv
| issue | count |
|---|---|
| `cnt = casual + registered` | holds in **17,379 / 17,379** clean rows (0 violations); dirty.csv breaks it in 1,716 rows |
| hum = 0 (physically impossible, all on 2011-03-10, weathersit 3 = rain in 20 of the 22 h) | 22 |
| atemp constant 0.2424 for a whole day while temp 0.62–0.86 (2012-08-17) | 24 |
| windspeed = 0 | 2,180 (12.5 %). The next value is 6 km/h (0.0896×67) and 1–5 km/h never occur, so 0 most likely means "calm or not recorded" **[inference: disguised MV]** |
| missing hourly records (731 × 24 = 17,544 expected) | 165 rows absent; 76 days incomplete (2012-10-29: 1 row, Hurricane Sandy; 2011-01-27: 8 rows) |
| weekday vs real calendar day; workingday = not(weekend or holiday); yr and mnth vs date | 0 violations each |
| duplicates (ignoring instant) | 0 |

The data does not match the Readme. The Readme says `season (1:springer, 2:summer, 3:fall, 4:winter)`, but the data uses astronomical seasons with 1 = winter (Dec 21–Mar 20), 2 = spring, 3 = summer and 4 = autumn. As a result, mnth→season is **not** an FD in the clean data: 1,911 rows (March, June, September, December) differ from the month's majority season. These rows are correct, but any rule-based detector that assumes mnth→season will flag them as false positives.

Side finding: `datasets_dictionary.py` sets `labels_reg = ["cnt"]` with `excluded_attribs = []`, so casual and registered (which sum exactly to the target) are model features. This is target leakage for Block D.

---

## 6. beers [21]

### Alignment (verified)
- **REPO clean = Raha clean.** All cells are equal (2,410 × 11). Two differences only: the REPO header uses `beer_name`/`brewery_name` where Raha uses `beer-name`/`brewery-name`, and the REPO file has CRLF line endings.
- **REPO dirty = Raha dirty**, byte-identical (sha256 equal).
- **Raha clean = Hould's Kaggle data.** It is `beers.csv` ⋈ `breweries.csv` on brewery_id, in the same row order (Kaggle row index = clean `index` − 1) and with the same id set. Every column agrees after the following, and no other change exists:
  - stripped whitespace: trailing space in 10 beer names and 11 brewery names, and the leading space in all 2,410 `state` values (`' OR'`);
  - numbers re-printed: ounces `12.0`→`12`; abv `0.08199999999999999`→`0.082`, numerically equal at a tolerance of 1e-9.

  The ibu and abv NaN sets are identical (1,005 and 62). Kaggle `beers.csv` is byte-identical to `nickhould/craft-beers-dataset/data/processed/beers.csv` on GitHub.
- **Category: identical up to formatting + join.**

### Is it manually verified?
- The Kaggle description says the data "was collected in January 2017 from CraftCans.com" and that "values have been cleaned up". That cleanup was the curator's scraping and cleaning script, described in his blog post. No evidence of cell-by-cell manual verification was found **[inference from the source description]**.
- **The dirty file was generated in code from this clean data (verified):**
  - every one of the 2,410 dirty `ounces` strings starts with the Kaggle float string (`12.0 oz.`, `12.0 ounce`, `16.0 OZ.`, …), which the website would not print;
  - all 693 dirty `abv` values with `%` are the Kaggle fraction string plus `%`, float noise included (`0.052000000000000005%`), so not a percentage;
  - ibu `''`→`N/A` (1,005);
  - city+state merged (127).

  So beers' "real-world errors" are realistic-looking format variants put back by script onto the curated data. The ground truth is exactly the curated data.

### Real errors that sit inside clean.csv
| issue | count |
|---|---|
| empty ibu / abv / style | 1,005 (41.7 %) / 62 / 5 |
| empty ibu turned into `N/A` in dirty | 1,005 GT errors whose "correct" value is itself missing (23 % of the 4,362 GT error cells) |
| duplicate beer listings (identical on all columns except index/id) | 33 (e.g. "Dale's Pale Ale", Oskar Blues, ids 1444/1252) |
| same (beer_name, brewery_id) | 83 (some are legitimate size variants) |
| one brewery under 2 brewery_ids | 7 names: Blackrocks (same city twice), Summit (`St Paul` vs `St. Paul`), Lucette (`Menominee` vs `Menominie`; the town is Menomonie, WI **[inference]**), Oskar Blues, Otter Creek, Sly Fox, Blue Mountain (two sites, possibly legitimate) |
| brewery_id → name/city/state FD | 0 violations |
| abv range | 0.001–0.128 (0.001 = "Scotty K NA", non-alcoholic, plausible) |

---

## 7. Verdict per dataset

- **adult: (b), after list-wise deletion.** clean.csv is the UCI raw data treated as clean. Rows with real missing values were deleted rather than kept. What remains as "correct":
  - 47 duplicate copies;
  - 5 conflicting-label pairs;
  - 229 `99999` sentinels;
  - 2 relationship/gender contradictions.

  The label is recoded with 1 = `<=50K`.
- **breast_cancer: (b), with N = 16 real missing values (`?`) kept as ground-truth values** (13 counted as "no error"), 8 exact duplicate rows and 4 conflicting-class IDs. The file also carries an artificial index column that REIN injects errors into.
- **nasa: (b) with no detectable real errors.** It is the closest of the five to a trustworthy ground truth, but only because the source is a clean physical measurement table, not because anyone verified it.
- **bike: (b) plus (c).** It is the raw source treated as clean, with 46 clearly wrong sensor cells (22 hum = 0, 24 atemp stuck), about 2,180 probable disguised missing values and 165 missing records. `dteday` is additionally a REIN-side mis-encoding (month stored as minutes), so the clean date column is not a faithful copy of the original.
- **beers: (c).** It is not manually verified ground truth. It is the curator's scripted cleanup of a web scrape, and the dirty version was generated in code from it. It is the only one of the five whose dirty version is published by a source other than REIN (Raha GitHub, byte-identical). It still contains about 1,072 empty cells (ibu, abv, style), 33 duplicate listings and 7 split brewery entities as "clean".

Published dirty versions:
- beers: yes (Raha GitHub = REPO dirty, byte-identical).
- adult, breast_cancer, nasa, bike: no. UCI and Kaggle hold only the single raw table; the dirty files exist only in REIN's `rein-datasets`.
