# server_env: running the benchmark on the 1 TB server

Setup files for `reports/server_plan_2026-10-13.md` (P0 step 5). The order of use is step 0 → the Mac rehearsal → P1 → P2. Block D (P3) runs on the Mac since 14 Oct (Block D plan §16), so P3 below is optional and V4 is informational. Each command comes with one plain sentence that says what it does. Memory is in decimal GB (10^9 bytes); every memory limit is given in bytes. Where the server plan disagrees with this file, this file wins: see "Plan errata" at the end.

| File | What it is |
|---|---|
| `docker-compose.server.yml` | The server's compose file: the loaded image (never built or pulled), a cpuset and a memory limit from `REIN_CPUSET`/`REIN_MEM`, no published database port, and one database per project. |
| `sitecustomize.py` | Makes `os.cpu_count()` return `REIN_WORKERS` (10), so Raha's `multiprocessing.Pool()` starts 10 workers, as on the Mac's 10-CPU Docker VM. |
| `calib.sh` | The P2 checks: `v4`, `v1`, `v3`, `v2`, `c4`, `probe`, `v5`. Each check ends with one `PASS` / `PASS WITH NOTE` / `FAIL` / `STOP` line. |
| `calib_lib.py` | Python helpers that `calib.sh` runs inside the container: the Mac listdir order for V3, the linkage probe, and the V4c line classifier. |
| `gitconfig` | Mounted as `/etc/gitconfig`, so that git inside the container (root) accepts your repo; `blockd_driver.py` records git HEAD. |
| `rein-move-excludes.txt` | The rsync exclude list for `rein-datasets/`, written by `scripts/make_env_manifest.sh`. |

**Rules that always hold**
- The commands are written for bash. On the Mac, type `bash` first: zsh (the macOS default) does not split `$DC` into words and answers "no such file or directory".
- Run every command from the folder of a repo copy (`~/rein-benchmark`, `~/rein-v4` or `~/rein-calib`), inside `tmux`, and end it with `< /dev/null`. Otherwise a background `docker compose run` can stop and wait for keyboard input.
- Always pass a project name with `-p`. Without it, compose names the project after the file's folder, `server_env`, in every copy, so two copies would share one database and one FAHES volume. Compose resolves the paths in the file against `server_env/`, so never add `--project-directory`.
- Every `$DC` command, `down` included, stops with "required variable REIN_CPUSET is missing a value" unless `REIN_CPUSET` and `REIN_MEM` are exported in this shell. In a new shell, export them again first (for `down`, any values work).
- A container started through the image's entrypoint first prints `Waiting for PostgreSQL at db:5432...` and `PostgreSQL is ready.`. The result is on the line(s) after them. Commands with `--no-deps --entrypoint python3` skip both lines and need no database.
- `calib.sh` refuses to run in the main repo. `v4` runs only in `~/rein-v4` (server) or `~/rein-calib-mac` (Mac rehearsal); every other check runs in `~/rein-calib` or `~/rein-calib-mac`.
- Lane T is `REIN_CPUSET=0-9`: 10 physical cores on NUMA node 0. Their hyperthreads 96-105 stay unused. A lane Q job takes another 10 cores, for example `48-57` on node 1.

Set this once in every new bash shell, from the repo copy you are working in:

```bash
DC='docker compose -f server_env/docker-compose.server.yml'
```
This saves typing: `$DC` now stands for "docker compose with the server file".

## Step 0 (Mac): commit the setup files, after the last Block D run

`env/`, `server_env/` and `scripts/make_env_manifest.sh` are untracked. A bundle holds only commits, and `calib.sh v4` refuses a copy whose `git status` is not empty. So commit them before the bundle (plan P0 steps 5-6) and before the rehearsal. Do it only after the last Block D run on the Mac: the Block D runs share one git HEAD (Block D plan §16), and `blockd_analysis.py` refuses runs from different HEADs.

```bash
cd ~/Desktop/BA/rein-benchmark && bash scripts/make_env_manifest.sh mac_20261014 < /dev/null | tail -n 3
```
This rebuilds `env/` from the current tree (its one editable `pip freeze` line names the current commit) and checks every checksum; it should end with `DONE`.

```bash
git add env server_env scripts/make_env_manifest.sh && git add -f env/order_manifest.json && git status --short env server_env scripts/make_env_manifest.sh
```
This stages the setup files. The second `add` needs `-f`, because `.gitignore` l. 60 ignores every `*.json`. Expect 20 lines that start with `A`.

```bash
git commit -m "Server setup: env/ record and checksums, server_env/"
```
This records them in one commit. Then merge into `master` as in plan P0 step 5, and make the bundle from `master` (P0 step 6).

## P0 step 7 (Mac): rehearsal in `~/rein-calib-mac`

```bash
git clone --branch master ~/rein-transfer/rein-master.bundle ~/rein-calib-mac && cd ~/rein-calib-mac && git log --oneline -1
```
This makes a fresh copy from the bundle, as the server will, and shows its newest commit (step 0's commit or later).

```bash
mkdir -p logs && rsync -a --exclude-from=server_env/rein-move-excludes.txt ~/Desktop/BA/rein-benchmark/rein-datasets/ rein-datasets/ && shasum -a 256 -c --quiet env/MANIFEST.sha256 && echo COPY_OK
```
This copies the datasets without the excluded folders and checks every file against the Mac's checksums.

```bash
export REIN_CPUSET=0-9 REIN_MEM=30000000000
```
This gives each container the Mac VM's 10 CPUs and a limit of 30 GB, below the VM's 33.6 GB.

```bash
$DC -p reint run --rm -T --no-deps --entrypoint python3 rein -c "import os,multiprocessing as m,sitecustomize as s;print(s.__file__,os.cpu_count(),m.Pool()._processes,len(os.sched_getaffinity(0)))" < /dev/null
```
This is U3 on the Mac: it should print `/rein/server_env/sitecustomize.py 10 10 10`.

```bash
bash server_env/calib.sh v4 < /dev/null; tail -n 7 logs/v4.log
```
This runs V4 with the Block D settings and makes the V4 baseline. Run it **before** `v1`: V1 rewrites `adult/holoclean/detections.csv` and `detection_results.csv`, both in `env/MANIFEST.sha256`, and V4 then refuses the copy ("precondition").

If V4c reports changed lines here, they come from the thread count (the committed d2-d6 outputs ran with 10 OpenBLAS threads). Since V4 is informational, a baseline is optional. If you want one:
```bash
W=$(ls -d logs/v4-*/v4c | tail -n 1); B=~/Desktop/BA/rein-benchmark/reports/block_d_final_plan_2026-10-09/checks/decisions/v4_baseline_mac
mkdir -p "$B" && cut -f1 "$W/list.tsv" | while read -r f; do cp "$W/$f" "$B/"; done; ls "$B" | wc -l
```
This copies exactly the 11 rerun outputs that `list.tsv` names (not the `.err`, `.tsv`, `classify.*` or `d2_part*` files), keeps their names (the classifier reads them), and prints `11`. Commit them in the Mac tree (also only after the last Block D run), make a new bundle, and rerun V4 in a fresh rehearsal copy.

```bash
bash server_env/calib.sh v1 < /dev/null; tail -n 2 logs/v1.log
```
This replays GE (three tiers) and HoloClean on 8 datasets and expects `V1 PASS 32/32`.

```bash
$DC -p reint down -v
```
This removes the rehearsal's test containers, network and volumes (in the shell with the two exports). It does not touch any file of the repo.

## P1: server bring-up

S1-S9 and T1-T8 are in the plan, §3. Apply the "Plan errata" at the end of this file first.

```bash
find rein-datasets -type d -empty | wc -l
```
After T5, this counts the empty folders that arrived: expect `22`, as the Mac's rsync creates. They matter: an existing `embeddings/` folder makes the Profiler load embeddings instead of training them (`rein/datasets.py:539`). rsync and tar keep empty folders, git does not, so never move `rein-datasets/` through git.

```bash
export REIN_CPUSET=0-9 REIN_MEM=40000000000
```
This tells compose which cores to use (lane T) and the memory limit in bytes. Every `$DC` command refuses to start without these two.

```bash
docker pull postgres:14-alpine && $DC -p reint config --quiet && echo CONFIG_OK
```
U1 fetches the database image and checks that the compose file is valid. Without Docker Hub, load `postgres-14-alpine-amd64.tar.gz` first (plan, P0 step 6).

```bash
$DC -p reint up -d --wait db
```
U2 starts lane T's own database in the background and waits until it reports `Healthy`.

```bash
$DC -p reint run --rm -T rein python3 -c "import os,multiprocessing as m,sitecustomize as s;print(s.__file__,os.cpu_count(),m.Pool()._processes,len(os.sched_getaffinity(0)))" < /dev/null
```
U3 checks that Python loads our `sitecustomize.py` and sees 10 CPUs. After the two PostgreSQL lines, the last line should be `/rein/server_env/sitecustomize.py 10 10 10`.

```bash
$DC -p reint run --rm -T rein cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.peak < /dev/null
```
U4 shows, in the last two lines, the container's memory limit (`40000000000`) and that its peak counter can be read.

```bash
$DC -p reint run --rm -T --no-deps --entrypoint python3 rein -m pip freeze < /dev/null | grep -v '^-e ' | diff - <(grep -v '^-e ' env/mac_20261014/pip_freeze.txt) && echo SAME
```
U5 compares the installed Python packages with the Mac's list and prints `SAME`. The editable line (`-e git+...@<commit>`) is left out on both sides: it names the repo's commit, and it appears only where the untracked `tools/error-generator/errorgenerator.egg-info/` exists (the Mac, not a clone).

```bash
$DC -p reint down
```
This stops lane T's database again (in the same shell as the exports). Every `calib.sh` check starts its own database.

## P2: calibration (one check at a time, in this order)

```bash
cp -a ~/rein-benchmark ~/rein-v4 && cd ~/rein-v4 && mkdir -p logs && sha256sum -c --quiet env/MANIFEST.sha256 && echo COPY_OK
```
P2.0a makes a byte copy for V4 that keeps the file times (`cp -a`; `d8` prints a file time) and checks every file against the Mac's checksums.

```bash
export REIN_CPUSET=0-9 REIN_MEM=40000000000
bash server_env/calib.sh v4 < /dev/null; tail -n 7 logs/v4.log
```
V4 (J6a) checks the flag hashes (V4a), reruns the flags-only scripts (V4b) and the d2-d6 decision runs (V4c) with 1 thread. It is informational since 14 Oct: Block D runs on the Mac, and nothing waits for this verdict. It tells whether server runs of the Block D scripts (an optional replication, P6) can be compared with the Mac's:
- `V4 PASS`: no line changed.
- `V4 PASS WITH NOTE`: V4a and V4b are clean, and only linear lines changed (on bc and adult also xgb). Paste the word diff from the log.
- `V4 STOP`: a V4a or V4b diff, or a changed RF, XGBRegressor, rows-kept or fill-value line. No debugging; re-check T5 and note the result.

Two choices of `calib.sh` go beyond the plan's wording. A V4c file whose bytes differ only in spacing or line ends counts as STOP (stricter than the plan, which does not name whitespace). A `=> ... pair verdicts change` line without a model word is allowed as "summary", because each verdict line it counts is classified on its own line.

```bash
cp -a ~/rein-benchmark ~/rein-calib && cd ~/rein-calib && mkdir -p logs results/server && sha256sum -c --quiet env/MANIFEST.sha256 && echo COPY_OK
```
P2.0 makes the second byte copy, in which V1, V3, V2 and C4 are allowed to rewrite files.

```bash
bash server_env/calib.sh v1 < /dev/null; tail -n 2 logs/v1.log
```
V1 (J3) replays GE and HoloClean, one fresh container per run, and compares TP/FP with Table 3. It expects `V1 PASS 32/32`.

```bash
bash server_env/calib.sh v3 breast_cancer nasa beers < /dev/null; tail -n 4 logs/v3.log
```
V3 (J6) runs cached Raha while `os.listdir` returns the Mac's file order (`env/order_manifest.json`). It expects bc 317/78, nasa 710/1864 and beers 3972/0 (F1 0.9532), and it is informational only.

```bash
bash server_env/calib.sh v2 breast_cancer nasa < /dev/null; tail -n 3 logs/v2.log
```
V2a (J4) moves each Mac cache aside, runs Raha cold and counts the new cache files: bc 318/89 with 305 files, nasa 731/1864 with 125 files. The new cache is kept as `strategy-profiling.server`, and the Mac cache is put back.

```bash
bash server_env/calib.sh v2 beers soilmoisture bike smartfactory < /dev/null; tail -n 5 logs/v2.log
```
V2b does the same for four datasets: beers 3922/0 (511 files), soilmoisture 8881/15343 (18 103), bike 30861/15142 (508), smartfactory 7091/379869 (568).

```bash
bash server_env/calib.sh v2 adult < /dev/null; tail -n 2 logs/v2.log
```
V2c (J5) runs adult cold, the largest run (865/5081, 513 files; the Mac's cold run took 1217 s with a peak of 23.2 GB). On any V2 mismatch the line reads `V2 STOP`: no debugging, and server Raha becomes a server-only series.

```bash
bash server_env/calib.sh c4 < /dev/null; tail -n 4 logs/c4.log
```
C4 (J7) runs `scalability_driver.py` on har r10, har r50 and mercedes c10 and compares TP/FP with `reports/scalability/results.csv` l. 107, 111 and 117. The rows are appended to `results/server/c4_<time>.csv`.

```bash
export REIN_CPUSET=48-57 REIN_MEM=80000000000
bash server_env/calib.sh probe 70000 < /dev/null; tail -n 2 logs/probe.log
```
J8 runs Raha's clustering call on 70 000 random rows (2.45e9 distances, more than 2^31) on lane Q cores, with a limit of 80 GB, and expects `linkage ok` (peak ≈ 39 GB est.). Run it only while lane T is idle if the server turns out to have one NUMA node.

```bash
bash server_env/calib.sh v5 < /dev/null
```
V5 lists, for every run above, the speed factor (Mac runtime / server runtime, for runs of at least 1 s) and the peak ratio where the Mac measured a peak. It gates nothing; the switch rule (plan §2, P2) decides.

What a check leaves behind: `logs/<check>.log` (appended), `logs/<check>-<time>/` (each container's output and memory samples), `logs/runs.tsv` (one row per run, read by V5) and `logs/.gitignore` (so git ignores `logs/`). A `v2` that stopped keeps `strategy-profiling.server`. Rename that folder yourself before you run `v2` again on the same dataset. The memory peak in a check's log is the last 1-s sample; C4 and the probe read `memory.peak` exactly at the end.

## P3: Block D runs on the Mac (optional replication only)

Since 14 Oct, Block D steps 4-9 run on the Mac (Block D plan §16), so the plan's P3 and table P3 (P3.0-P3.10) no longer apply. The Mac's results commit is the only one: **on the server, never commit, tag or bundle Block D results.** If you want to see whether the server reproduces the Mac's final core run, use a throwaway copy:

```bash
cp -a ~/rein-benchmark ~/rein-bd && cd ~/rein-bd && mkdir -p logs && DC='docker compose -f server_env/docker-compose.server.yml'
export REIN_CPUSET=48-57 REIN_MEM=16000000000
BD="$DC -p reinb run --rm -T --no-deps --entrypoint python3 -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -e MKL_NUM_THREADS=1 -e PYTHONHASHSEED=0 -e REIN_IMAGE_ID=$(docker image inspect -f '{{.Id}}' rein-benchmark-rein:latest) rein"
```
This makes a separate copy and defines `$BD`: one container with no database, 1 thread per library and a fixed hash seed, as in the Mac runs. `env/mac_20261014/` has no `openblas_coretype.txt` (numpy and scipy OpenBLAS report Nehalem and Atom), so there is no `OPENBLAS_CORETYPE` pin.

```bash
$BD scripts/blockd_driver.py --flags_dir reports/block_d/flags --datasets breast_cancer nasa --out reports/block_d/runs/<date>_server_core > logs/bd_core.log 2>&1 < /dev/null; echo exit $?
```
This runs the core run on the server and prints `exit 0` when it finishes.

```bash
$BD scripts/blockd_analysis.py --compare reports/block_d/runs/<mac date>_mac_core reports/block_d/runs/<date>_server_core < /dev/null | tail -n 1
```
This compares the two runs without `fit_s` and `timestamp` (V4d) and prints `V4d PASS`, `V4d PASS WITH NOTE` (only linear, or xgb on bc/adult, differs) or `V4d STOP`. Record the line; delete `~/rein-bd` afterwards (see Housekeeping).

## Plan errata (as of 14 Oct)

1. Plan §3 "How to run" (l. 391) and P0 step 5 (l. 135) put the compose file at the repo root. It is `server_env/docker-compose.server.yml`; use the `DC` above.
2. Plan P0 step 7 (l. 149), T3 (l. 413) and cleanup manifest §5.2 (l. 326, 342) use `~/Desktop/BA/rein-move-excludes.txt`, which does not exist. Use `server_env/rein-move-excludes.txt` (the same six lines).
3. Plan P0 step 7 (l. 152-153) runs `v1` before `v4`. Run `v4` first, as above.
4. Plan U5 (l. 423) cannot print `SAME` (entrypoint lines, the editable line, `env/mac_20261013`). Use U5 above.
5. `env/mac_20261013/` (plan l. 128, 394, 423) is `env/mac_20261014/`, and it has no `openblas_coretype.txt`.
6. Plan "Block D on the server", §2 (order items 2-4, disagreement 1), P3 and table P3: superseded by the 14 Oct decision (Block D plan §16). V4 is informational.
7. Cleanup manifest §5.1 step 3 and §5.3 V2 expect 20 661 checksum lines. `env/MANIFEST.sha256` replaces that list: 20 753 lines = 36 inputs + 15 constraint files + 8 FD files + 18 results + 30 embeddings + 12 live `detections.csv` + 20 633 cache files + the suite file.
8. Not in the plan: the record's `uname.txt` is `uname -srvm`, without the Mac's host name, so `env/` can go into a public fork.
9. T8 (plan l. 418) expects Id `sha256:8ccf6a40…`. That holds only if `docker info -f '{{.Driver}}'` prints `overlayfs` (containerd image store, as on the Mac). With `overlay2` the same image loads as `sha256:19912b85…` (its config digest, `ConfigDigest` in `env/mac_20261014/image.txt`). `calib.sh` accepts both; any other Id is a stop.

## Housekeeping

The container runs as root, so files it creates in a copy (Raha caches, `results/server/`, `detection_logs/`) belong to root. To delete a copy later, first give its files back to you (in a shell with the two exports):
```bash
$DC -p reinclean run --rm -T --no-deps --entrypoint chown rein -R "$(id -u):$(id -g)" /rein < /dev/null; $DC -p reinclean down -v
```
This uses the container's root rights to make you the owner of everything under this copy, and then removes the helper project.
