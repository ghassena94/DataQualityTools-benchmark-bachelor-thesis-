# Search for prepared REIN clean/dirty pairs: citation, print3d, water, power, soccer

Date: 2026-10-07. No logins, nothing changed under REPO. The only downloads went into DL/citation/rein_prepared/ and DL/soccer/rein_prepared/.

## Bottom line

- **The official REIN release (ResearchGate) contains only the 9 datasets you already have.** Verified: the file on ResearchGate has the same SHA-256 as `~/Downloads/rein-datasets.zip`.
- **citation: a prepared pair is published**, in the first author's repo `mohamedyd/DVBench`. dirty.csv is 5005×2 and matches Table 4. clean.csv is 3997×2 because it is the de-duplicated version. **It is NOT cell-aligned with dirty.csv.**
- **soccer: a prepared clean.csv is published.** It is 180228×43, so the row count matches Table 4 exactly. It sits in the Lopster/LOP repo (VLDB 2024; dos Reis, **Abdelaal**, Binnig), which says it ships "the REIN benchmark data ... as is". The aligned dirty versions there are LOP's own error injections from 2023–2024, with error rates of 0.13, 0.17 and 0.22, not REIN's 0.27. **REIN's own soccer dirty.csv was not found.**
- **water:** no data files were found. LOP's code has a `water` config entry, but no water files were shipped.
- **print3d, power:** no trace anywhere.

## 1. ResearchGate release (lead 1)

| Check | Result |
|---|---|
| `curl` with a browser user agent on the publication page | **HTTP 403** ("Temporarily Unavailable", bot block) |
| DataCite record for DOI 10.13140/RG.2.2.18388.82567 | "Datasets of REIN Benchmark", Abdelaal, 2024, type Dataset. Registered 2024-07-24. No file list or size in the metadata. |
| Built-in browser, public page (read only, not logged in) | One file: **`rein-datasets.zip`, "6.2 MB"**, CC BY 4.0. Abstract: "several tabular datasets ... each dataset includes a clean and a dirty version". Data URL: `https://www.researchgate.net/profile/Mohamed-Abdelaal-29/publication/382496079_Datasets_of_REIN_Benchmark/data/66a0c66d5919b66c9f684294/rein-datasets.zip` |
| HEAD request on that URL from the browser | `content-length: 6506397`, `application/zip` |
| SHA-256 of the RG bytes, hashed in browser memory and not saved | `a5208ce6927ff5808bfd23930be99ba551a1da7bdf63e57f7f4e275f45e00084` |
| SHA-256 of `~/Downloads/rein-datasets.zip` (and of the `(1)` copy) | **identical**: `a5208ce6…0084` |
| Zip listing | 28 entries: 9 folders (adult, beers, bike, breast_cancer, har, mercedes, nasa, smartfactory, soilmoisture), each with clean.csv and dirty.csv. The archive was made 2024-07-17 on Windows (FAT attributes). The CSV dates run from 2020-11 to 2022-11. |

**Verified:** the RG release is exactly the 9-dataset zip you already have. It contains nothing for the 5 missing datasets.

## 2. GitHub: mohamedyd repositories (lead 2)

All 48 repos of `mohamedyd` were listed. Recursive HEAD trees were fetched for 21 of them: every non-fork repo plus the relevant forks. The full git history (all paths ever committed) was scanned with blobless bare clones for these 11: AutoCure, SAGED, ReClean, RTClean, DiffClean, DiffSelect, D3Bench, XAI2Clean, DataLens, Data-quality-Dashboard, DVBench. The upstream rein-benchmark history was cloned in full (section 4).

| Repo | Hits for citation / print3d / water / power / soccer | Data it does hold |
|---|---|---|
| rein-benchmark | none (HEAD and all 6 commits) | only tool fixtures |
| AutoCure | none | none in the repo; Zenodo copy in section 3 |
| SAGED | none (the paper uses a 200000×10 "Soccer"; no files in the repo) | none |
| ReClean | none | ccpp, nasa, retailSales, smartfactory, wdbc, wine (clean only) |
| RTClean | none | hospital, iot |
| DiffClean | none (history scanned too) | airbnb, bike, mercedes, nasa, soilmoisture (+ custom injections) |
| DiffSelect | none | UJIndoorLoc, airbnb, beers, bike, mercedes, nasa, news, prostate, slice, soilmoisture |
| D3Bench | none | energy_data, occupacy_data, nasa |
| XAI2Clean | none | adult, breast_cancer, nasa |
| DataLens | none | beers, breast_cancer, movies_1, nasa |
| Data-quality-Dashboard | none | none |
| **DVBench** (branches local_tk and master) | **`microbenchmark/data/datasets/citation/{clean,dirty}.csv`** (local_tk) and the same blobs in `experiments/data/citation/` (master). First committed 2022-08-03 ("moved to benchmark folder"). The repo mirrors `git.sagresearch.de/kompaki/data-valuation/val4clean`. | adult, beers, breast_cancer, **citation**, nasa |
| **data_cleaning_with_latent_operators** (fork of DataManagementLab) | **`rein_data.zip` → `DATASETS_REIN/soccer_PLAYER/`** | adult, bikes, smart_factory, **soccer_PLAYER** |
| GLLM, IML4E-*, Energy_efficient-WSNs, awesome_ml_resources, Haipipe | none | n/a |
| SEED (fork) | only unrelated Wikipedia tables (e.g. "List_of_power_stations…") | n/a |
| mohamedyd.github.io (homepage) | no data links. The only links are the GitHub repos above and ResearchGate pages. | n/a |

Repo READMEs (14 repos) were checked for Drive, Zenodo, Figshare, Dropbox, Kaggle or HF links. **The only link found is the RG link in rein-benchmark.**

Broad GitHub searches:
- `gh search repos "rein benchmark"`: only upstream and your own repo.
- `gh search code` for these terms: "rein-datasets", "tension_strenght" (REIN's print3d label spelling), "Datasets_of_REIN_Benchmark", `groundTruth_path print3d`, `CS,title` in dirty.csv or clean.csv, and `--filename dirty.csv` with path citation, water, soccer or print3d.
- Results: only REIN's own code, plus unrelated datasets. Two examples: the 200000×10 cleaning-literature "soccer" in Huenao/BudgetedGroupRepair and qzkinhit/MDCBaseline, and Matelda DGov tables.
- **Caveat:** GitHub code search does not index large CSVs, so this is supporting evidence, not proof.

## 3. Zenodo / Figshare / Drive / papers (lead 3)

| Source | Result |
|---|---|
| REIN paper (SCRATCH/rein.txt, arXiv v1, EDBT PDF) | Footnote 1: "source code, data, and other artifacts" are at github.com/mohamedyd/rein-benchmark. There is no Zenodo, Figshare or Drive link. The other URLs only point to the raw sources (UCI, Kaggle, Magellan). |
| DataCite, all DOIs with creator Abdelaal | The only REIN dataset DOI is the RG one. There are Zenodo records 7253265/7253266 (AutoCure software). |
| Zenodo 7253266 `AutoCure.zip` (270,642,761 B): central directory listed with HTTP range requests; 555 KB fetched, nothing downloaded | 3480 entries. Data only for adult, breast_cancer, housing, nasa, smartfactory, soilmoisture. **None of the 5.** |
| AutoCure, SAGED, DataLens, LLMClean, RTClean papers | No data-hosting links. AutoCure: "will be publicly released". DataLens: "Source code will be publicly available". SAGED: GitHub only. |
| **Lopster/LOP (VLDB 2024, Reis, Abdelaal, Binnig)**, `DataManagementLab/data_cleaning_with_latent_operators` README | Ships `rein_data.zip`. Also links **"Large Soccer Dataset"**: `https://drive.google.com/file/d/1svyTShYV6DAO87_BbmWmeUDozf7AAvcv` → `LOP-Soccer-Full.zip`, 24,351,046 B, public, no login needed. The `dataset_configuration.json` and `datasets.py` have a **`water`** entry (id col `index`, target `x38`), but no water files exist anywhere in the repo or its history. The forks floroh and OlgaOvcharenko hold the same blob. |
| Hugging Face dataset search (rein, rein-benchmark, citation_dirty, print3d, soccer_dirty) | nothing relevant |
| Kaggle public search API (rein datasets, rein data cleaning, abdelaal) | nothing relevant |
| `git.sagresearch.de` (KompAKI GitLab named in DVBench merges) | 404 / not public |
| TUdatalib (TU Darmstadt), search "Abdelaal" | 0 results |

## 4. Upstream rein-benchmark git history (lead 4)

- `gh api commits?path=datasets` (and `rein/datasets`, `data`): no commits.
- Full bare clone: 6 commits in total (2022-05-27 ×3, 2024-07-24 ×3), 870 distinct paths. **No dataset folder was ever committed.** The only CSVs are tool fixtures (FAHES DMV_dirty.csv, Picket titanic/wine).
- Branches: master only. No tags, no releases.
- Forks (aksharkaul, kavumatimothy, harel-coffee/-auto, Kellsky, zitronian): same trees, no datasets.

## 5. What was downloaded and measured

### citation → `DL/citation/rein_prepared/`
| File | URL | Size | SHA-256 |
|---|---|---|---|
| clean.csv | `https://raw.githubusercontent.com/mohamedyd/DVBench/21dc972be8443259b20dd7472b38d358baaca544/microbenchmark/data/datasets/citation/clean.csv` | 232,730 | `b17a498da012ae2248861809d26b92d4659488418e8bfb9413cf13df3016f912` |
| dirty.csv | same path, `dirty.csv` | 291,584 | `3d2c7359a45b9dfd7f4e80a9387d11a21c62d1c5f646f4f978abd40d07b6a781` |

The git blob hashes match the tree (db2f72cf…, 06ddd1ff…). The files are byte-identical to the copy another agent saved in `DL/citation/dvbench_mohamedyd/`.

Measured:
- dirty **5005×2**, columns `CS,title`. This matches Table 4 (5005 rows, 2 cols) and REIN's `datasets_dictionary` (keys `['CS','title']`, label `CS`).
- clean **3997×2**. **Not cell-aligned: the clean file has 1008 fewer rows.**
- clean = the first occurrence of each case-insensitive title in dirty, in the same order (verified), with corrected labels.
- Duplicate rows: 1008 (947 exact, 61 case-only), so **1008/5005 = 0.201**. This matches Table 4's 0.2.
- Mislabels: 209 dirty rows have a label that differs from clean. 190 duplicate groups carry conflicting labels. The union of duplicates and mislabels is 1112 rows (0.222).
- dirty.csv is identical in content to CleanML's `Citation/raw/raw.csv` (from the other agent's download).
- **Consequence:** the benchmark's cell-wise diff cannot be applied as is. Duplicates are row deletions, not cell changes.

### soccer → `DL/soccer/rein_prepared/`
| File | URL | Size | SHA-256 |
|---|---|---|---|
| rein_data.zip | `https://raw.githubusercontent.com/DataManagementLab/data_cleaning_with_latent_operators/73be3561a15958d45f5342f7786ed57d1665e0b1/rein_data.zip` | 83,840,547 | `491b765f073f5d21870ba142dd6030085af011f9ef7a0afef2aa5a1fc903f49a` (git blob 133e3b92…) |
| LOP-Soccer-Full.zip | `https://drive.usercontent.google.com/download?id=1svyTShYV6DAO87_BbmWmeUDozf7AAvcv&export=download` | 24,351,046 | `f6c07bd84ec0e5412ef710f7a472498d7d2d20f55e756e6af8ad76847afaddad` |

Extracted into `extract_lop_soccer_full/LOP-Soccer-Full/` and `extract_rein_data/DATASETS_REIN/soccer_PLAYER/`. Three clean.csv files were also extracted for the provenance check.

| File (date in zip) | Size | SHA-256 |
|---|---|---|
| clean.csv (2022-01-26; same bytes in both zips) | 29,986,365 | `f613a3fd…8dbc` |
| LOP-Soccer-Full dirty.csv (2024-07-11) | 44,857,543 | `8a2840c6…7b93` |
| LOP-Soccer-Full actual_errors.csv (2024-07-12, REIN `row,col,DUMMY VALUE` format) | 37,694,999 | `59328cec…e3d3` |
| soccer_PLAYER dirty01.csv (2024-01-19) | 4,603,016 | `b83cb1b6…a771` |
| soccer_PLAYER dirty02.csv (2023-10-11) | 56,019,667 | `8f5a6f6e…b69f` |

Provenance (measured): adult, bikes and smart_factory clean.csv inside the same `rein_data.zip` are **byte-identical to the RG REIN release**. That supports the README's claim that the data is REIN's, "as is". LOP-Soccer-Full also uses REIN's folder layout: `actual_errors.csv` in DUMMY-VALUE format, `constraints/`, and a REIN-style `parameters.yml`.

Measured:
- clean **180228×43**. Rows match Table 4 exactly.
- Columns: 43 vs Table 4's 44. There are 38 numeric columns, including the `id_x` player id, and 5 text columns: player_name, birthday, date, preferred_foot, attacking_work_rate. Table 4 says 40 numeric and 4 categorical.
- 3,287 `attacking_work_rate` cells hold the literal `None`, which pandas reads as NaN by default.
- LOP-Soccer-Full dirty.csv:
  - 180228×43, same column order, **cell-aligned**.
  - **Cell error rate 0.2196**: 1,701,745 of 7,749,804 cells.
  - Error types: 1,656,688 numeric noise values (dirty/clean ratio p1 = −12.8, p99 = 15.1) and 45,057 blanks. There are no string or rule changes, although `parameters.yml` lists rule_violation.
  - 180225 of 180228 rows contain at least one error.
  - `actual_errors.csv` lists 1,692,323 cells, 9,422 fewer than the measured diff.
- dirty02.csv (2023-10):
  - 180228×43, but in a different column order.
  - Aligned after reordering columns, though floats are re-formatted ("1" vs "1.0").
  - Real error rate **0.132**.
- dirty01.csv: the first 20000 rows only, error rate **0.172**.
- **No soccer dirty file matches Table 4's 0.27 or its error mix** (rule violations, outliers, MVs, implicit MVs).
- Inference, not verified: clean.csv is REIN's soccer ground truth (2022 date, exact row count, shipped next to REIN files). The dirty files are LOP's own injections, not REIN's.

## Final table

| dataset | prepared clean/dirty published? | where | verified shape |
|---|---|---|---|
| citation | **Yes, both files** (dirty = CleanML raw; clean = de-duplicated) | github.com/mohamedyd/DVBench `microbenchmark/data/datasets/citation/` (also `experiments/data/citation/` on master) | dirty 5005×2, clean 3997×2. **Not cell-aligned.** Duplicate-row rate 0.201 matches Table 4's 0.2. Plus 209 mislabels. |
| print3d | **No** | nowhere: RG zip, 21 author repos plus history, Zenodo, LOP, HF, Kaggle, code search | n/a |
| water | **No** (LOP code has a config entry, but no file) | nowhere | n/a |
| power | **No** | nowhere | n/a |
| soccer | **clean: yes (REIN-era, very likely REIN's). dirty: only LOP's own versions, REIN's 0.27 dirty not found** | DataManagementLab/data_cleaning_with_latent_operators `rein_data.zip` (soccer_PLAYER) and Google Drive `LOP-Soccer-Full.zip` | clean 180228×43. LOP-Full dirty 180228×43, aligned, error rate 0.220. dirty02 180228×43, 0.132. dirty01 20000×43, 0.172. Table 4: 180228×44, 0.27. |

## Side notes (not acted on)
- AutoCure's Zenodo `experiments/data/adult/dirty.csv` is 5,243,355 B (2022-07-19). The RG adult dirty.csv is 4,774,871 B (2022-11-14), so there are at least two different REIN-family adult dirty versions.
- DVBench's adult, beers, breast_cancer and nasa pairs differ in size from the RG release (e.g. nasa dirty is 84,544 vs 58,431/59,935 B). The authors kept several dirty variants per dataset across their repos.
