#!/usr/bin/env bash
# calib.sh: the server calibration checks of reports/server_plan_2026-10-13.md
# (§3 table P2, and the section "Block D on the server" for v4).
#
#   bash server_env/calib.sh v4                     V4a-V4c (informational)          -> V4 PASS | V4 PASS WITH NOTE | V4 STOP
#   bash server_env/calib.sh v1                     GE x3 tiers + HoloClean replay   -> V1 PASS 32/32 | V1 FAIL n/32
#   bash server_env/calib.sh v3 [datasets]          cached Raha, Mac file order      -> V3 PASS n/n | V3 FAIL n/m (informational)
#   bash server_env/calib.sh v2 <datasets>          cold Raha, Mac cache moved aside -> V2 PASS n/n | V2 STOP n/m
#   bash server_env/calib.sh c4                     three scalability_driver points  -> C4 PASS 3/3 | C4 FAIL n/3
#   bash server_env/calib.sh probe <rows> [feats]   scipy linkage(average, cosine)   -> PROBE PASS | PROBE FAIL
#   bash server_env/calib.sh v5                     speed factor and peak ratios     -> V5 PASS n runs | V5 FAIL
#
# Before any mode except v5:  export REIN_CPUSET=<cores, e.g. 0-9> REIN_MEM=<limit in bytes, e.g. 40000000000>
# Optional: REIN_PROJECT (compose project; default rein<mode>), REIN_SAMPLE_S (memory sampling interval, default 1),
#           REIN_MAC_RECORD (folder under env/ with openblas_coretype.txt; default the newest env/mac_*).
#
# Rules this script enforces:
#   - It runs only in a copy whose folder is rein-calib, rein-v4 or rein-calib-mac; v4 only in rein-v4 or
#     rein-calib-mac, and nothing else in rein-v4. V1-V3 rewrite detections.csv and append to
#     detection_results.csv, and V4b rewrites the frozen expected_pair_verdicts.csv in place
#     (implied_predictions.py:125), so none of it may touch the main repo.
#   - Every mode has its own compose project (own database, own volumes) and removes it at the end.
#   - Pure-python work (v4, probe, helpers) uses run --no-deps --entrypoint python3 (no Postgres;
#     entrypoint.sh:14-19 would wait for it). Detector runs (v1, v2, v3, c4) keep the db and the entrypoint.
#   - Every container's memory.peak, sampled anon maximum, memory.max and oom_kill are recorded.
#   - Output: everything to the terminal and to logs/<mode>.log (appended; if you redirect stdout to
#     logs/<mode>.log yourself, the script notices and writes it once). Per-run files in logs/<mode>-<time>/.
#     logs/.gitignore ignores the whole folder, so V4's "git status --porcelain" stays empty.
#   - The last line is always one summary line: PASS, PASS WITH NOTE, FAIL or STOP.
# Written for bash 3.2 (the Mac rehearsal) and bash 5 (the server). Never uses sudo, never pushes, never commits.
# V4 is informational since 14 Oct: Block D steps 4-9 run on the Mac (Block D plan §16), so no step waits for it.

set -u -o pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
ROOT=$(cd "$HERE/.." && pwd -P)
MODE=${1:-}
[ $# -gt 0 ] && shift
MODE_UC=$(printf '%s' "$MODE" | tr '[:lower:]' '[:upper:]')

IMAGE=rein-benchmark-rein:latest
# server plan P0 step 6 and T8; env/mac_20261014/image.txt. The same image has two Ids: the OCI index digest
# (containerd image store, Docker driver "overlayfs", as on the Mac) and the config digest (classic "overlay2").
EXPECTED_IMAGE_ID=sha256:8ccf6a40cb8a4a351a85952bdb5ec9563ae25551b63059c5a081770a01d4a760
EXPECTED_IMAGE_CONFIG=sha256:19912b857c9b98fe21c59281ecec3304045d8b8597c670b5c56700d05b39eb92
CHK=reports/block_d_final_plan_2026-10-09/checks
DEC=$CHK/decisions
FROZEN_COMMIT=c61ee72                       # the frozen prediction: plan v2.1 §9 + expected_pair_verdicts.csv
PLAN_MD=reports/block_d_final_plan_2026-10-09.md
SAMPLE_S=${REIN_SAMPLE_S:-1}
DC=(docker compose -f server_env/docker-compose.server.yml)
PROJECT=${REIN_PROJECT:-rein$MODE}
LOGDIR=$ROOT/logs
LOG=$LOGDIR/$MODE.log
WORK=$LOGDIR/$MODE-$(date +%Y%m%d-%H%M%S)-$$
RUNS=$LOGDIR/runs.tsv
CURRENT_PID=
V2_SP=
RESULT_RC=1

# ======================================================================================= expected values
# Each table: one row per run, then the source of the expected numbers.

# V1: GE x3 tiers + HoloClean on the stored constraints; TP FP = Table 3 (Mac, 15 Sep 2026 17:02).
# Order per dataset: dirty, clean, hand_written last (GE writes every tier into one detections.csv), HoloClean.
v1_table() { cat <<'EOF'
# dataset       config              TP      FP  mac_runtime_s  source
breast_cancer   ge_dirty_profiled   247     13  0.02   results/runs_log.csv l.13
breast_cancer   ge_clean_profiled   278     13  0.02   results/runs_log.csv l.14
breast_cancer   ge_hand_written     438     22  0.01   results/runs_log.csv l.15
breast_cancer   holoclean           416   5275  0.30   results/runs_log.csv l.16
nasa            ge_dirty_profiled    30      0  0.01   results/runs_log.csv l.8
nasa            ge_clean_profiled   384      0  0.02   results/runs_log.csv l.9
nasa            ge_hand_written     680      0  0.01   results/runs_log.csv l.10
nasa            holoclean           556   5709  0.32   results/runs_log.csv l.11
beers           ge_dirty_profiled  1132     67  0.02   results/runs_log.csv l.3
beers           ge_clean_profiled  4235     67  0.03   results/runs_log.csv l.4
beers           ge_hand_written    4362     67  0.02   results/runs_log.csv l.5
beers           holoclean          2557   3264  0.70   results/runs_log.csv l.6
bike            ge_dirty_profiled     0      0  0.23   results/runs_log.csv l.18
bike            ge_clean_profiled     0      0  0.25   results/runs_log.csv l.19
bike            ge_hand_written   24247      0  0.14   results/runs_log.csv l.20
bike            holoclean         25134 173845  8.30   results/runs_log.csv l.21
smartfactory    ge_dirty_profiled  7093      0  0.34   results/runs_log.csv l.23
smartfactory    ge_clean_profiled  7093      0  0.33   results/runs_log.csv l.24
smartfactory    ge_hand_written    7093      0  0.16   results/runs_log.csv l.25
smartfactory    holoclean          6995 246806  9.70   results/runs_log.csv l.26
soilmoisture    ge_dirty_profiled   213      0  0.26   results/runs_log.csv l.28
soilmoisture    ge_clean_profiled   213      0  0.26   results/runs_log.csv l.29
soilmoisture    ge_hand_written    5659      0  0.12   results/runs_log.csv l.30
soilmoisture    holoclean             0      0  0.40   results/runs_log.csv l.31
adult           ge_dirty_profiled     0      0  0.33   results/runs_log.csv l.33
adult           ge_clean_profiled     0      0  0.33   results/runs_log.csv l.34
adult           ge_hand_written       0      0  0.23   results/runs_log.csv l.35
adult           holoclean          1677 663530 26.23   results/runs_log.csv l.36
har             ge_dirty_profiled 10502      0  0.23   rein-datasets/har/results/detection_results.csv l.2 (14 Sep) = reports/scalability/results.csv l.11
har             ge_clean_profiled 11142      0  0.23   rein-datasets/har/results/detection_results.csv l.3 = reports/scalability/results.csv l.26
har             ge_hand_written   22400      0  0.15   rein-datasets/har/results/detection_results.csv l.4 = reports/scalability/results.csv l.41
har             holoclean             0      0  0.93   rein-datasets/har/results/detection_results.csv l.5 = reports/scalability/results.csv l.73
EOF
}

# V3: cached Raha run 1 in the Mac file order = Table 3 (Mac). files = complete cache (plan T6).
v3_table() { cat <<'EOF'
# dataset       TP      FP  files  mac_runtime_s  source
breast_cancer   317     78    305    2.01  results/runs_log.csv l.17 (plan V3: bc 317/78)
nasa            710   1864    125    1.79  results/runs_log.csv l.12 (plan V3: nasa 710/1864)
beers          3972      0    511    5.15  results/runs_log.csv l.7 (plan V3: beers F1 0.9532)
bike          30861  15138    508  160.11  results/runs_log.csv l.22
soilmoisture   8833  15222  18103   26.03  results/runs_log.csv l.32
smartfactory   7091 379839    568  364.67  results/runs_log.csv l.27
adult           865   5081    513  607.52  results/runs_log.csv l.37
EOF
}

# V2: cold Raha (the cache moved aside) = the Mac's cold runs; files = new cache size (plan §3 V2a-V2c, T6).
# mac_peak only where the Mac measured one. adult: its only clean cold run is reports/scalability/results.csv l.106
# (26 Sep, adult r100 Raha on a scratch copy, 1217.35 s, peak 23164956672 B); detection_results.csv l.15 (607.52 s)
# is run 1 of the cached batch (results/runs_log.csv l.37); the file keeps no cold run (the one ending 28 Sep 09:07
# logged 47 566 s across a laptop sleep and was removed on 29 Sep).
# TP/FP are identical cold and cached on adult (865/5081), so only V5's speed factor depends on this choice.
v2_table() { cat <<'EOF'
# dataset       TP      FP  files  mac_runtime_s  mac_peak_bytes  source
breast_cancer   318     89    305    8.52  -            rein-datasets/breast_cancer/results/detection_results.csv l.33 (23 Sep 17:38:52); plan V2a 318/89
nasa            731   1864    125    5.78  -            rein-datasets/nasa/results/detection_results.csv l.32 (23 Sep 17:38:37); plan V2a 731/1864
beers          3922      0    511   24.60  -            rein-datasets/beers/results/detection_results.csv l.18 (13 Sep 20:50:18); plan V2b F1 0.9469
soilmoisture   8881  15343  18103  177.17  -            rein-datasets/soilmoisture/results/detection_results.csv l.6 (14 Sep 18:01:51); plan V2b 8881/15343
bike          30861  15142    508  493.47  -            rein-datasets/bike/results/detection_results.csv l.6 (14 Sep 17:58:11); plan V2b FP 15142
smartfactory   7091 379869    568  878.69  -            rein-datasets/smartfactory/results/detection_results.csv l.33 (23 Sep 17:53:41); plan V2b 386960 detections
adult           865   5081    513 1217.35  23164956672  reports/scalability/results.csv l.106 (26 Sep 23:01:41, cold, runtime and peak); plan V2c 865/5081
EOF
}

# C4: scalability_driver.py points = reports/scalability/results.csv (Mac, 26-27 Sep; plan §3 C4: l. 107/111/117).
c4_table() { cat <<'EOF'
# dataset   axis  fraction  TP     FP    mac_runtime_s  mac_peak_bytes  source
har         rows  0.1        4592   147   21.82         2328981504     reports/scalability/results.csv l.107
har         rows  0.5       24391  1328  176.62        11634896896     reports/scalability/results.csv l.111
mercedes    cols  0.1       27624    33  432.62         5699686400     reports/scalability/results.csv l.117
EOF
}

# ======================================================================================= helpers
say()     { printf '%s\n' "$*"; }
section() { printf '\n==== %s\n' "$*"; }
rel()     { case "$1" in "$ROOT"/*) printf '%s' "${1#"$ROOT"/}";; *) printf '%s' "$1";; esac; }
gb()      { awk -v b="${1:-}" 'BEGIN { if (b == "" || b == "-" || b == "max") print (b == "max" ? "unlimited" : "n/a"); else printf "%.2f", b / 1e9 }'; }
num_eq()  { awk -v a="${1:-}" -v b="${2:-}" 'BEGIN { exit !(a != "" && b != "" && a + 0 == b + 0) }'; }
show_cmd() { printf '  $'; printf ' %q' "$@"; printf '\n'; }
count_files() { if [ -d "$1" ]; then find "$1" -type f | wc -l | tr -d ' '; else echo 0; fi; }
nlines()  { if [ -f "$1" ]; then awk 'END { print NR }' "$1"; else echo 0; fi; }
det_csv() { printf '%s/rein-datasets/%s/results/detection_results.csv' "$ROOT" "$1"; }

if command -v sha256sum >/dev/null 2>&1; then SHA=(sha256sum); else SHA=(shasum -a 256); fi
sha_of() { "${SHA[@]}" "$1" | awk '{ print $1 }'; }

# The last line of a detection_results.csv: "TP FP DETECTIONS RUNTIME F1", or "MISMATCH <detector>"
# when the last line belongs to another detector.
last_detection() {
  awk -F, -v want="$2" '
    NR == 1 { for (i = 1; i <= NF; i++) h[$i] = i; next }
    { last = $0 }
    END {
      split(last, f, ",")
      if (f[h["detector"]] != want) { print "MISMATCH " f[h["detector"]]; exit }
      print f[h["cell_TP"]], f[h["cell_FP"]], f[h["#detections"]], f[h["detection_runtime"]], f[h["f1"]]
    }' "$1"
}

# One result line per run: printed now, and again in the recap just above the summary line,
# so that "tail -n <runs + 1> logs/<mode>.log" shows every result and the verdict.
RECAP=
result() { say "$1"; RECAP="$RECAP$1"$'\n'; }

# Prints the recap and the final summary line, and sets the exit code (0 for PASS / PASS WITH NOTE, 1 otherwise).
summary() {
  case "$1" in *" PASS"*) RESULT_RC=0;; *) RESULT_RC=1;; esac
  if [ -n "$RECAP" ]; then printf '\n==== results\n%s' "$RECAP"; fi
  printf '%s\n' "$1"
}

refuse() {   # before anything ran
  printf '%s STOP refused: %s\n' "${MODE_UC:-CALIB}" "$*"
  exit 2
}

# Every second, ask the running container for its cgroup memory counters (memory.peak only grows,
# so the last sample is the peak up to about one second before the end).
SNAP_CMD='cd /sys/fs/cgroup && echo peak $(cat memory.peak 2>/dev/null) && echo limit $(cat memory.max 2>/dev/null) && cat memory.stat memory.events 2>/dev/null'
sample_memory() {   # NAME PID OUTFILE
  local name=$1 pid=$2 out=$3 snap
  printf 'epoch\tpeak_bytes\tanon_bytes\tmax_bytes\toom_kill\n' > "$out"
  while kill -0 "$pid" 2>/dev/null; do
    snap=$(docker exec "$name" sh -c "$SNAP_CMD" < /dev/null 2>/dev/null | awk '
      $1 == "peak" { p = $2 } $1 == "limit" { l = $2 } $1 == "anon" && a == "" { a = $2 } $1 == "oom_kill" { o = $2 }
      END { if (p != "") printf "%s\t%s\t%s\t%s\n", p, a, l, o }')
    [ -n "$snap" ] && printf '%s\t%s\n' "$(date +%s)" "$snap" >> "$out"
    sleep "$SAMPLE_S"
  done
}

# run_job TAG STDIN STDOUT STDERR <docker compose run arguments: options, service, command...>
# Starts one fresh container (--rm -T, named so the sampler can find it) and records memory.
JOB_RC=0; JOB_WALL=0; JOB_PEAK=; JOB_ANON=; JOB_LIMIT=; JOB_OOM=; JOB_SAMPLES=0
run_job() {
  local tag=$1 in=$2 out=$3 err=$4 name mem t0 pid
  shift 4
  name="$PROJECT-$tag-$$"
  mem="$WORK/$tag.mem.tsv"
  show_cmd "${DC[@]}" -p "$PROJECT" run --rm -T --name "$name" "$@"
  say "      stdin $(rel "$in") | stdout $(rel "$out") | stderr $(rel "$err")"
  t0=$(date +%s)
  if [ "$err" = "$out" ]; then
    "${DC[@]}" -p "$PROJECT" run --rm -T --name "$name" "$@" < "$in" > "$out" 2>&1 &
  else
    "${DC[@]}" -p "$PROJECT" run --rm -T --name "$name" "$@" < "$in" > "$out" 2> "$err" &
  fi
  pid=$!
  CURRENT_PID=$pid
  sample_memory "$name" "$pid" "$mem"
  wait "$pid"
  JOB_RC=$?
  CURRENT_PID=
  JOB_WALL=$(( $(date +%s) - t0 ))
  JOB_SAMPLES=$(( $(nlines "$mem") - 1 ))
  JOB_PEAK=$(awk -F'\t' 'NR > 1 { p = $2 } END { print p }' "$mem")
  JOB_ANON=$(awk -F'\t' 'NR > 1 && $3 != "" && $3 + 0 > m { m = $3 + 0 } END { if (m != "") printf "%.0f", m }' "$mem")
  JOB_LIMIT=$(awk -F'\t' 'NR > 1 { l = $4 } END { print l }' "$mem")
  JOB_OOM=$(awk -F'\t' 'NR > 1 { o = $5 } END { print o }' "$mem")
  say "      exit $JOB_RC | wall $JOB_WALL s | memory.peak $(gb "$JOB_PEAK") GB (last of $JOB_SAMPLES samples) | anon max $(gb "$JOB_ANON") GB | limit $(gb "$JOB_LIMIT") GB | oom_kill ${JOB_OOM:-n/a}"
  [ "$JOB_RC" -eq 0 ] || { say "      last lines of $(rel "$err"):"; tail -n 5 "$err" | sed 's/^/      | /'; }
}

# record_run ITEM STATUS RUNTIME_S MAC_RUNTIME_S MAC_PEAK_BYTES  -> one row in logs/runs.tsv (read by v5)
record_run() {
  [ -f "$RUNS" ] || printf 'time\tmode\titem\tstatus\texit\truntime_s\tmac_runtime_s\twall_s\tpeak_bytes\tanon_max_bytes\tlimit_bytes\toom_kill\tmac_peak_bytes\n' > "$RUNS"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$MODE" "$1" "$2" "$JOB_RC" \
    "${3:--}" "${4:--}" "$JOB_WALL" "${JOB_PEAK:--}" "${JOB_ANON:--}" "${JOB_LIMIT:--}" "${JOB_OOM:--}" "${5:--}" >> "$RUNS"
}

project_busy() { [ -n "$(docker ps -q --filter "label=com.docker.compose.project=$PROJECT" 2>/dev/null)" ]; }
project_down() { "${DC[@]}" -p "$PROJECT" down -v --remove-orphans >> "$WORK/compose.log" 2>&1; }
start_db() {
  section "Start this mode's own database (project $PROJECT)"
  show_cmd "${DC[@]}" -p "$PROJECT" up -d --wait db
  "${DC[@]}" -p "$PROJECT" up -d --wait db >> "$WORK/compose.log" 2>&1 || return 1
  say "  db healthy"
}

on_interrupt() {
  local c
  [ -n "$CURRENT_PID" ] && kill "$CURRENT_PID" 2>/dev/null
  for c in $(docker ps -aq --filter "label=com.docker.compose.project=$PROJECT" 2>/dev/null); do
    docker rm -f "$c" >> "$WORK/compose.log" 2>&1     # this mode's own containers only
  done
  project_down
  if [ -n "$V2_SP" ] && [ -d "$V2_SP.mac" ]; then        # v2 was interrupted: put the Mac cache back
    [ -d "$V2_SP" ] && mv "$V2_SP" "$V2_SP.server-interrupted"
    mv "$V2_SP.mac" "$V2_SP" && say "  put the Mac cache back: $(rel "$V2_SP")"
  fi
  summary "$MODE_UC STOP interrupted"
  exit 1
}

# Block D thread settings ("Block D on the server"): every v4 command.
BD_ENV=()
block_d_env() {
  local rec="" d
  BD_ENV=(-e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -e MKL_NUM_THREADS=1 -e PYTHONHASHSEED=0 -e "REIN_IMAGE_ID=$REIN_IMAGE_ID")
  if [ -n "${REIN_MAC_RECORD:-}" ]; then rec=$ROOT/env/$REIN_MAC_RECORD; else
    for d in "$ROOT"/env/mac_*/; do [ -d "$d" ] && rec=${d%/}; done
  fi
  if [ -n "$rec" ] && [ -f "$rec/openblas_coretype.txt" ]; then
    BD_ENV+=(-e "OPENBLAS_CORETYPE=$(tr -d '[:space:]' < "$rec/openblas_coretype.txt")")
    say "  OPENBLAS_CORETYPE pinned from $(rel "$rec")/openblas_coretype.txt"
  else
    say "  no openblas_coretype.txt in $([ -n "$rec" ] && rel "$rec" || echo 'env/mac_*') (numpy and scipy OpenBLAS disagree): no OPENBLAS_CORETYPE pin"
  fi
}
PY=(--no-deps --entrypoint python3)

# ======================================================================================= v1
mode_v1() {
  local ds cfg etp efp mrt src label tier csv before after row tp fp det rt f1 res n=0 ok=0 tag
  start_db || { summary "V1 FAIL database did not start (see $(rel "$WORK")/compose.log)"; return; }
  v1_table | grep -v '^#' > "$WORK/expected.tsv"
  section "V1: GE x3 + HoloClean on the stored constraints, one fresh container per run (compare TP/FP with Table 3)"
  while read -r ds cfg etp efp mrt src <&3; do
    [ -n "$ds" ] || continue
    n=$((n + 1)); tag="${ds}_$cfg"
    say ""; say "V1 $n/32 $ds $cfg"
    csv=$(det_csv "$ds"); before=$(nlines "$csv")
    if [ "$cfg" = holoclean ]; then
      label=holoclean
      run_job "$tag" /dev/null "$WORK/$tag.out" "$WORK/$tag.out" \
        rein python3 scripts/detect_errors.py --dataset_name "$ds" --detect_method holoclean --n_iterations 1
    else
      tier=${cfg#ge_}; label="greatExpectations:$tier"
      run_job "$tag" /dev/null "$WORK/$tag.out" "$WORK/$tag.out" \
        -e "EXPECTATION_TIER=$tier" rein python3 scripts/detect_errors.py --dataset_name "$ds" --detect_method greatExpectations --n_iterations 1
    fi
    after=$(nlines "$csv"); tp=-; fp=-; rt=-
    if [ "$JOB_RC" -ne 0 ]; then res="FAIL (exit $JOB_RC)"
    elif [ $((after - before)) -ne 1 ]; then res="FAIL ($((after - before)) new rows in $(rel "$csv"), expected 1)"
    else
      row=$(last_detection "$csv" "$label")
      read -r tp fp det rt f1 <<< "$row"
      if [ "$tp" = MISMATCH ]; then res="FAIL (last row is detector $fp)"; tp=-; fp=-
      elif num_eq "$tp" "$etp" && num_eq "$fp" "$efp"; then res=OK; ok=$((ok + 1))
      else res=FAIL; fi
    fi
    result "  V1 $ds $cfg: TP/FP $tp/$fp, expected $etp/$efp ($src) -> $res | runtime $rt s (Mac $mrt s)"
    record_run "$ds:$cfg" "$res" "$rt" "$mrt" -
  done 3< "$WORK/expected.tsv"
  project_down
  if [ "$ok" -eq "$n" ] && [ "$n" -eq 32 ]; then summary "V1 PASS $ok/$n"; else summary "V1 FAIL $ok/$n (server used for cost only; no debugging)"; fi
}

# ======================================================================================= v3
mode_v3() {
  local list ds etp efp efiles mrt src sp have csv before after row tp fp det rt f1 res n=0 ok=0 tag
  [ $# -gt 0 ] && list="$*" || list="breast_cancer nasa beers"
  [ -f "$ROOT/env/order_manifest.json" ] || { summary "V3 FAIL env/order_manifest.json is missing (P0 step 4)"; return; }
  start_db || { summary "V3 FAIL database did not start"; return; }
  v3_table | grep -v '^#' > "$WORK/expected.tsv"
  section "V3: cached Raha run 1 with os.listdir returning the Mac order (env/order_manifest.json); informational"
  for ds in $list; do
    n=$((n + 1)); tag="${ds}_raha_cached"
    read -r _ etp efp efiles mrt src <<< "$(awk -v d="$ds" '$1 == d' "$WORK/expected.tsv")"
    if [ -z "${etp:-}" ]; then result "  V3 $ds: no expected values (datasets: $(awk '{printf "%s ", $1}' "$WORK/expected.tsv"))"; continue; fi
    sp=$ROOT/rein-datasets/$ds/raha-baran-results-$ds/strategy-profiling; have=$(count_files "$sp")
    say ""; say "V3 $ds (cache $have files, expected $efiles)"
    if [ "$have" != "$efiles" ]; then result "  V3 $ds: cache has $have files, expected $efiles -> FAIL (a cold run would not test the Mac order)"; etp=; continue; fi
    csv=$(det_csv "$ds"); before=$(nlines "$csv")
    run_job "$tag" /dev/null "$WORK/$tag.out" "$WORK/$tag.out" \
      rein python3 /rein/server_env/calib_lib.py mac-order scripts/detect_errors.py --dataset_name "$ds" --detect_method raha --n_iterations 1
    after=$(nlines "$csv"); tp=-; fp=-; rt=-; f1=-
    if [ "$JOB_RC" -ne 0 ]; then res="FAIL (exit $JOB_RC)"
    elif ! grep -q 'returned in the Mac order' "$WORK/$tag.out"; then res="FAIL (the Mac order was not applied: cache not loaded?)"
    elif [ $((after - before)) -ne 1 ]; then res="FAIL ($((after - before)) new rows)"
    else
      row=$(last_detection "$csv" raha); read -r tp fp det rt f1 <<< "$row"
      if num_eq "$tp" "$etp" && num_eq "$fp" "$efp"; then res=OK; ok=$((ok + 1)); else res=DIFFERS; fi
    fi
    result "  V3 $ds: TP/FP $tp/$fp F1 $f1, expected $etp/$efp ($src) -> $res | runtime $rt s (Mac $mrt s)"
    record_run "$ds:raha_cached" "$res" "$rt" "$mrt" -
    etp=
  done
  project_down
  if [ "$ok" -eq "$n" ] && [ "$n" -gt 0 ]; then summary "V3 PASS $ok/$n (informational)"; else summary "V3 FAIL $ok/$n (informational, no stop)"; fi
}

# ======================================================================================= v2
mode_v2() {
  local ds etp efp efiles mrt mpeak src sp have newf csv before after row tp fp det rt f1 res n=0 ok=0 tag
  [ $# -gt 0 ] || { summary "V2 FAIL name the datasets, e.g. v2 breast_cancer nasa"; return; }
  start_db || { summary "V2 FAIL database did not start"; return; }
  v2_table | grep -v '^#' > "$WORK/expected.tsv"
  section "V2: cold Raha per dataset: move the Mac cache aside, run, count the new cache, put the Mac cache back"
  for ds in "$@"; do
    n=$((n + 1)); tag="${ds}_raha_cold"; etp=
    read -r _ etp efp efiles mrt mpeak src <<< "$(awk -v d="$ds" '$1 == d' "$WORK/expected.tsv")"
    if [ -z "${etp:-}" ]; then result "  V2 $ds: no expected values -> STOP"; continue; fi
    sp=$ROOT/rein-datasets/$ds/raha-baran-results-$ds/strategy-profiling; have=$(count_files "$sp")
    say ""; say "V2 $ds"
    if [ -e "$sp.mac" ] || [ -e "$sp.server" ]; then result "  V2 $ds: $(rel "$sp").mac or .server exists already (an earlier v2 run?) -> STOP"; continue; fi
    if [ "$have" != "$efiles" ]; then result "  V2 $ds: Mac cache has $have files, expected $efiles -> STOP"; continue; fi
    show_cmd mv "$(rel "$sp")" "$(rel "$sp").mac"
    mv "$sp" "$sp.mac" || { result "  V2 $ds: could not move the cache aside -> STOP"; continue; }
    V2_SP=$sp
    csv=$(det_csv "$ds"); before=$(nlines "$csv")
    run_job "$tag" /dev/null "$WORK/$tag.out" "$WORK/$tag.out" \
      rein python3 scripts/detect_errors.py --dataset_name "$ds" --detect_method raha --n_iterations 1
    after=$(nlines "$csv"); newf=$(count_files "$sp"); tp=-; fp=-; rt=-; f1=-
    # keep the new server cache beside the Mac cache, and put the Mac cache back where Raha looks for it
    if [ -d "$sp" ]; then show_cmd mv "$(rel "$sp")" "$(rel "$sp").server"; mv "$sp" "$sp.server"; fi
    show_cmd mv "$(rel "$sp").mac" "$(rel "$sp")"; mv "$sp.mac" "$sp"; V2_SP=
    if [ "$JOB_RC" -ne 0 ]; then res="STOP (exit $JOB_RC)"
    elif [ $((after - before)) -ne 1 ]; then res="STOP ($((after - before)) new rows)"
    else
      row=$(last_detection "$csv" raha); read -r tp fp det rt f1 <<< "$row"
      if num_eq "$tp" "$etp" && num_eq "$fp" "$efp" && [ "$newf" = "$efiles" ]; then res=OK; ok=$((ok + 1)); else res=STOP; fi
    fi
    result "  V2 $ds: TP/FP $tp/$fp F1 $f1, new cache $newf files; expected $etp/$efp, $efiles files ($src) -> $res | runtime $rt s (Mac $mrt s) | peak $(gb "$JOB_PEAK") GB, limit $(gb "$JOB_LIMIT") GB"
    record_run "$ds:raha_cold" "$res" "$rt" "$mrt" "$mpeak"
  done
  project_down
  if [ "$ok" -eq "$n" ]; then summary "V2 PASS $ok/$n"; else summary "V2 STOP $ok/$n (no debugging: server Raha becomes a server-only series, §5.2.4)"; fi
}

# ======================================================================================= c4
mode_c4() {
  local ds axis frac etp efp mrt mpeak src out tag row status tp fp rt peak res n=0 ok=0 before after
  mkdir -p "$ROOT/results/server"
  out=results/server/c4_$(date +%Y%m%d-%H%M%S).csv
  start_db || { summary "C4 FAIL database did not start"; return; }
  c4_table | grep -v '^#' > "$WORK/expected.tsv"
  section "C4: scalability_driver.py on three Mac points (scratch copies; rows appended to $out)"
  while read -r ds axis frac etp efp mrt mpeak src <&3; do
    [ -n "$ds" ] || continue
    n=$((n + 1)); tag="${ds}_${axis}_${frac}_raha"
    say ""; say "C4 $ds $axis $frac raha"
    before=$(nlines "$ROOT/$out")
    run_job "$tag" /dev/null "$WORK/$tag.out" "$WORK/$tag.out" \
      -e EXPECTATION_TIER=hand_written rein python3 scripts/scalability_driver.py \
      --dataset "$ds" --axis "$axis" --fraction "$frac" --detector raha --out "$out"
    after=$(nlines "$ROOT/$out"); status=-; tp=-; fp=-; rt=-; peak=-
    if [ "$after" -gt "$before" ]; then
      row=$(awk -F, 'NR == 1 { for (i = 1; i <= NF; i++) h[$i] = i; next } { last = $0 } END { split(last, f, ","); print f[h["status"]], f[h["cell_TP"]], f[h["cell_FP"]], f[h["runtime_s"]], f[h["peak_mem_bytes"]] }' "$ROOT/$out")
      read -r status tp fp rt peak <<< "$row"
    fi
    if [ "$status" = ok ] && num_eq "$tp" "$etp" && num_eq "$fp" "$efp"; then res=OK; ok=$((ok + 1)); else res=FAIL; fi
    result "  C4 $ds $axis $frac: status $status TP/FP $tp/$fp, expected $etp/$efp ($src) -> $res | runtime $rt s (Mac $mrt s) | driver peak $(gb "$peak") GB (Mac $(gb "$mpeak") GB)"
    JOB_PEAK=${peak:-$JOB_PEAK}      # the driver reads memory.peak itself at the very end: exact
    record_run "$ds:$axis:$frac:raha" "$res" "$rt" "$mrt" "$mpeak"
  done 3< "$WORK/expected.tsv"
  project_down
  if [ "$ok" -eq "$n" ] && [ "$n" -eq 3 ]; then summary "C4 PASS $ok/$n"; else summary "C4 FAIL $ok/$n"; fi
}

# ======================================================================================= probe
mode_probe() {
  local rows=${1:-} feats=${2:-20} line
  case "$rows" in ''|*[!0-9]*) summary "PROBE FAIL give the number of rows, e.g. probe 70000"; return;; esac
  section "Probe: scipy linkage(average, cosine) on $rows random rows x $feats features (Raha's build_clusters call)"
  run_job "probe_$rows" /dev/null "$WORK/probe_$rows.out" "$WORK/probe_$rows.out" \
    "${PY[@]}" rein /rein/server_env/calib_lib.py probe "$rows" "$feats"
  sed 's/^/  | /' "$WORK/probe_$rows.out"
  line=$(grep '^linkage ' "$WORK/probe_$rows.out" | tail -n 1)
  record_run "linkage:$rows" "${line:-no result}" - - -
  project_down
  if [ "$JOB_RC" -eq 0 ] && [ "${line#linkage ok}" != "$line" ]; then
    summary "PROBE PASS linkage ok, rows $rows, peak $(gb "$JOB_PEAK") GB, limit $(gb "$JOB_LIMIT") GB"
  elif [ "${JOB_OOM:-0}" != "" ] && [ "${JOB_OOM:-0}" != 0 ] || [ "$JOB_RC" -eq 137 ]; then
    summary "PROBE FAIL oom_killed (exit $JOB_RC, oom_kill ${JOB_OOM:-n/a}), rows $rows, limit $(gb "$JOB_LIMIT") GB"
  else
    summary "PROBE FAIL ${line:-no linkage line, exit $JOB_RC}, rows $rows"
  fi
}

# ======================================================================================= v5
mode_v5() {
  [ -s "$RUNS" ] || { summary "V5 FAIL no runs recorded in logs/runs.tsv (run v1, v3, v2, c4 first)"; return; }
  section "V5: speed factor = Mac runtime / server runtime (runs of >= 1 s on the Mac); peak ratio = server / Mac peak"
  awk -F'\t' -v speeds="$WORK/speeds.txt" '
    NR == 1 { for (i = 1; i <= NF; i++) h[$i] = i; next }
    { k = $h["mode"] " " $h["item"]; row[k] = $0; if (!(k in seen)) { seen[k] = 1; order[++n] = k } }
    END {
      printf "%-40s %12s %12s %8s %10s %10s %8s\n", "run", "server_s", "mac_s", "speed", "peak_GB", "mac_GB", "ratio"
      for (i = 1; i <= n; i++) {
        split(row[order[i]], f, "\t")
        s = f[h["runtime_s"]]; m = f[h["mac_runtime_s"]]; p = f[h["peak_bytes"]]; mp = f[h["mac_peak_bytes"]]
        sp = "-"; if (s + 0 > 0 && m + 0 >= 1) { sp = sprintf("%.2f", m / s); print sp > speeds }
        pr = "-"; if (p + 0 > 0 && mp + 0 > 0) pr = sprintf("%.2f", p / mp)
        printf "%-40s %12s %12s %8s %10s %10s %8s\n", order[i], s, m, sp, (p + 0 > 0 ? sprintf("%.2f", p / 1e9) : "-"), (mp + 0 > 0 ? sprintf("%.2f", mp / 1e9) : "-"), pr
      }
    }' "$RUNS"
  local k med
  touch "$WORK/speeds.txt"
  k=$(nlines "$WORK/speeds.txt")
  if [ "$k" -eq 0 ]; then summary "V5 FAIL no run with a Mac runtime of at least 1 s"; return; fi
  med=$(sort -n "$WORK/speeds.txt" | awk '{ v[NR] = $1 } END { print (NR % 2 ? v[(NR + 1) / 2] : (v[NR / 2] + v[NR / 2 + 1]) / 2) }')
  say ""; say "  the switch rule (plan §2 P2) decides whether a qualitative claim changes; V5 itself gates nothing"
  summary "V5 PASS $k runs, median speed factor $med (Mac/server)"
}

# ======================================================================================= v4
mode_v4() {
  local st man n=0 ok=0 ds cfg file det tp fp sha rest got v4a_ok=0 v4b_changed=0 v4b_fail=0 v4c_fail=0
  local f ref new ds0 spec name out c v4c_changed=0 v4c_bytes=0 lin=0 xgbc=0 summ=0 stopc=0 git_clean=0 c61_ok=0 verdict pre=""
  local V4B_FILES
  section "V4: cross-machine check (copy $(rel "$ROOT"), project $PROJECT, Block D thread settings)"
  block_d_env

  # ---- preconditions: a pristine copy
  st=$(git -C "$ROOT" status --porcelain 2>&1)
  if [ -n "$st" ]; then pre="git status is not empty before V4 (make a fresh copy):"$'\n'"$st"; fi
  if [ -z "$pre" ]; then
    if [ ! -f "$ROOT/env/MANIFEST.sha256" ]; then pre="env/MANIFEST.sha256 is missing (P0 step 4)"
    else
      show_cmd "${SHA[@]}" -c --quiet env/MANIFEST.sha256
      if ! (cd "$ROOT" && "${SHA[@]}" -c --quiet env/MANIFEST.sha256 > "$WORK/manifest_check.txt" 2>&1); then
        pre="env/MANIFEST.sha256 does not match this copy (V1-V3 ran here, or the transfer is broken):"$'\n'"$(head -n 5 "$WORK/manifest_check.txt")"
      else say "  env/MANIFEST.sha256: all files OK"; fi
    fi
  fi
  if [ -n "$pre" ]; then
    say "  $pre"
    printf 'V4a not run\nV4b not run\nV4c not run\ngit status %s\nc61ee72 diff not checked\n' "$([ -n "$st" ] && echo 'NOT clean' || echo clean)"
    summary "V4 STOP (precondition)"
    return
  fi

  # ---- V4a: flag files vs MANIFEST.csv
  section "V4a: sha256 of the frozen flag files vs reports/block_d/flags/MANIFEST.csv"
  man=$ROOT/reports/block_d/flags/MANIFEST.csv
  while IFS=, read -r ds cfg file det tp fp sha rest <&3; do
    [ "$ds" = dataset ] && continue
    [ -n "$ds" ] || continue
    n=$((n + 1)); got=$(sha_of "$ROOT/$file" 2>/dev/null)
    if [ "$got" = "$sha" ]; then ok=$((ok + 1)); else say "  differs: $file (MANIFEST ${sha:0:16}..., file ${got:0:16}...)"; fi
  done 3< "$man"
  # 20 = 4 datasets x 5 configurations (Block D plan v2.1 §3; MANIFEST.csv has 20 rows since 13 Oct, commit 1394804)
  [ "$ok" -eq 20 ] && [ "$n" -eq 20 ] && v4a_ok=1
  say "  $ok/$n flag files match"

  # ---- V4b: flags-only scripts must reproduce their committed outputs byte for byte
  section "V4b: flags-only scripts rewrite their committed outputs in this copy; git diff must be empty"
  run_job v4b_measure_fixes /dev/null "$ROOT/$CHK/measure_fixes_output.txt" "$WORK/v4b_measure_fixes.err" \
    "${PY[@]}" "${BD_ENV[@]}" rein "$CHK/measure_fixes.py"; [ "$JOB_RC" -eq 0 ] || v4b_fail=1
  run_job v4b_implied_predictions /dev/null "$ROOT/$CHK/implied_predictions_output.txt" "$WORK/v4b_implied_predictions.err" \
    "${PY[@]}" "${BD_ENV[@]}" rein "$CHK/implied_predictions.py"; [ "$JOB_RC" -eq 0 ] || v4b_fail=1
  run_job v4b_reference_rankings /dev/null "$ROOT/$CHK/reference_rankings_output.txt" "$WORK/v4b_reference_rankings.err" \
    "${PY[@]}" "${BD_ENV[@]}" rein "$CHK/reference_rankings.py"; [ "$JOB_RC" -eq 0 ] || v4b_fail=1
  run_job v4b_run_addendum /dev/null "$WORK/v4b_run_addendum.out" "$WORK/v4b_run_addendum.err" \
    "${PY[@]}" "${BD_ENV[@]}" rein "$CHK/addendum_raha_run1/run_addendum.py"; [ "$JOB_RC" -eq 0 ] || v4b_fail=1
  run_job v4b_d8 /dev/null "$ROOT/$DEC/d8_adult_holoclean_output.txt" "$WORK/v4b_d8.err" \
    "${PY[@]}" -w "/rein/$DEC" "${BD_ENV[@]}" rein d8_adult_holoclean.py; [ "$JOB_RC" -eq 0 ] || v4b_fail=1
  V4B_FILES="$CHK/measure_fixes_output.txt $CHK/measure_fixes.json $CHK/implied_predictions_output.txt
    $CHK/expected_pair_verdicts.csv $CHK/reference_rankings_output.txt
    $CHK/addendum_raha_run1/measure_fixes_output.txt $CHK/addendum_raha_run1/measure_fixes.json
    $CHK/addendum_raha_run1/implied_predictions_output.txt $CHK/addendum_raha_run1/expected_pair_verdicts_raha_run1.csv
    $DEC/d8_adult_holoclean_output.txt"
  # shellcheck disable=SC2086  # V4B_FILES is a list of paths without spaces
  git -C "$ROOT" diff --no-color --word-diff=plain -U0 -- $V4B_FILES > "$WORK/v4b.diff"
  v4b_changed=$(grep -c -E '\[-|\{\+' "$WORK/v4b.diff")
  # the decision is git diff --exit-code itself (the word count above can miss whitespace-only changes)
  # shellcheck disable=SC2086
  if ! git -C "$ROOT" diff --quiet --exit-code -- $V4B_FILES; then
    [ "$v4b_changed" -gt 0 ] || { v4b_changed=1; say "  git diff --exit-code: files differ in whitespace or line ends only"; }
  fi
  # shellcheck disable=SC2086
  git -C "$ROOT" diff --numstat -- $V4B_FILES | sed 's/^/  numstat /'
  if [ "$v4b_changed" -gt 0 ]; then say "  word diff (first 40 lines, all in $(rel "$WORK")/v4b.diff):"; head -n 40 "$WORK/v4b.diff" | sed 's/^/  | /'; fi
  [ "$v4b_fail" -eq 0 ] || say "  a V4b script exited non-zero"

  # ---- V4c: decision reruns vs the Mac baseline
  section "V4c: d2-d6 decision reruns vs checks/decisions/v4_baseline_mac/<file> if it exists, else the committed file"
  mkdir -p "$WORK/v4c"
  : > "$WORK/v4c/pairs.tsv"
  # d2 runs from stdin, plain then 'adult', into one file (d2_impute_stats.py:3; plan §8 item 13)
  run_job v4c_d2_plain "$ROOT/$DEC/d2_impute_stats.py" "$WORK/v4c/d2_part1.txt" "$WORK/v4c/d2_part1.err" \
    "${PY[@]}" "${BD_ENV[@]}" rein -; [ "$JOB_RC" -eq 0 ] || v4c_fail=1
  run_job v4c_d2_adult "$ROOT/$DEC/d2_impute_stats.py" "$WORK/v4c/d2_part2.txt" "$WORK/v4c/d2_part2.err" \
    "${PY[@]}" "${BD_ENV[@]}" rein - adult; [ "$JOB_RC" -eq 0 ] || v4c_fail=1
  cat "$WORK/v4c/d2_part1.txt" "$WORK/v4c/d2_part2.txt" > "$WORK/v4c/d2_impute_stats_output.txt"
  printf 'd2_impute_stats_output.txt\tnasa\n' > "$WORK/v4c/list.tsv"
  # name | output file | default dataset for the classifier | arguments (run with -w checks/decisions; d7 skipped: timings only)
  for spec in \
    "d3|d3_model_seed_output.txt|breast_cancer|d3_model_seed.py" \
    "d4|d4_numeric_rule_output.txt|breast_cancer|d4_numeric_rule.py" \
    "d5_bc|d5_fill_statistic_breast_cancer.txt|breast_cancer|d5_fill_statistic.py breast_cancer" \
    "d5_nasa|d5_fill_statistic_nasa.txt|nasa|d5_fill_statistic.py nasa" \
    "d5_bike|d5_fill_statistic_bike.txt|bike|d5_fill_statistic.py bike floor,impute" \
    "d5_why|d5_why_mean_wins_output.txt|nasa|d5_why_mean_wins.py" \
    "d5_bike_columns|d5_bike_columns_output.txt|bike|d5_bike_columns.py" \
    "d5_bike_holiday|d5_bike_holiday_output.txt|bike|d5_bike_holiday.py" \
    "d6_nasa|d6_format_only_nasa.txt|nasa|d6_format_only.py nasa" \
    "d6_bike|d6_format_only_bike.txt|bike|d6_format_only.py bike"; do
    name=${spec%%|*}; rest=${spec#*|}; out=${rest%%|*}; rest=${rest#*|}; ds0=${rest%%|*}; rest=${rest#*|}
    # shellcheck disable=SC2086  # the script and its arguments contain no spaces
    run_job "v4c_$name" /dev/null "$WORK/v4c/$out" "$WORK/v4c/$name.err" \
      "${PY[@]}" -w "/rein/$DEC" "${BD_ENV[@]}" rein $rest; [ "$JOB_RC" -eq 0 ] || v4c_fail=1
    printf '%s\t%s\n' "$out" "$ds0" >> "$WORK/v4c/list.tsv"
  done
  while IFS="$(printf '\t')" read -r f ds0 <&3; do
    if [ -f "$ROOT/$DEC/v4_baseline_mac/$f" ]; then ref=$DEC/v4_baseline_mac/$f; else ref=$DEC/$f; fi
    new=$(rel "$WORK")/v4c/$f
    cmp -s "$ROOT/$ref" "$ROOT/$new" || v4c_bytes=$((v4c_bytes + 1))
    printf '%s\t%s\t%s\n' "$ref" "$new" "$ds0" >> "$WORK/v4c/pairs.tsv"
    c=$(git diff --no-index --no-color --word-diff=plain -U0 -- "$ROOT/$ref" "$ROOT/$new" | grep -c -E '\[-|\{\+')
    say "  $f vs $ref: $c changed lines"
    [ "$c" -gt 0 ] && git diff --no-index --no-color --word-diff=plain -U0 -- "$ROOT/$ref" "$ROOT/$new" | grep -E '\[-|\{\+' | head -n 30 | sed 's/^/  | /'
  done 3< "$WORK/v4c/list.tsv"
  run_job v4c_classify /dev/null "$WORK/v4c/classify.out" "$WORK/v4c/classify.err" \
    "${PY[@]}" rein /rein/server_env/calib_lib.py v4classify "$(rel "$WORK")/v4c/pairs.tsv"
  sed 's/^/  /' "$WORK/v4c/classify.out"
  c=$(grep '^V4C_CLASSES ' "$WORK/v4c/classify.out" | tail -n 1)
  if [ -z "$c" ]; then v4c_fail=1; say "  the classifier printed no result"
  else
    v4c_changed=$(printf '%s' "$c" | sed -n 's/.* changed=\([0-9]*\).*/\1/p')
    lin=$(printf '%s' "$c" | sed -n 's/.* linear=\([0-9]*\).*/\1/p')
    xgbc=$(printf '%s' "$c" | sed -n 's/.* xgb_clf=\([0-9]*\).*/\1/p')
    summ=$(printf '%s' "$c" | sed -n 's/.* summary=\([0-9]*\).*/\1/p')
    stopc=$(printf '%s' "$c" | sed -n 's/.* stop=\([0-9]*\).*/\1/p')
  fi
  [ "$v4c_fail" -eq 0 ] || say "  a V4c script or the classifier exited non-zero"
  say "  files that differ byte for byte: $v4c_bytes of 11"
  if [ "$v4c_bytes" -gt 0 ] && [ "${v4c_changed:-0}" -eq 0 ]; then
    v4c_changed=$v4c_bytes; stopc=$v4c_bytes            # whitespace or line ends only: not a linear change, so STOP (stricter than the plan)
    say "  the bytes differ, but no line does (whitespace or line ends): counted as stop"
  fi
  say "  rerun outputs: $(rel "$WORK")/v4c/ (copy them to checks/decisions/v4_baseline_mac/ only in the Mac rehearsal, plan P0 step 7)"

  # ---- end: the copy is unchanged and the frozen prediction is untouched
  section "End checks: git status --porcelain and the $FROZEN_COMMIT diff (expected_pair_verdicts.csv and plan §9)"
  st=$(git -C "$ROOT" status --porcelain 2>&1)
  if [ -z "$st" ]; then git_clean=1; else say "  git status --porcelain:"; printf '%s\n' "$st" | sed 's/^/  | /'; fi
  if git -C "$ROOT" diff --quiet "$FROZEN_COMMIT" -- "$CHK/expected_pair_verdicts.csv" \
     && [ -n "$(git -C "$ROOT" show "$FROZEN_COMMIT:$PLAN_MD" | awk '/^## 9\./ { f = 1 } /^## 10\./ { f = 0 } f')" ] \
     && [ "$(git -C "$ROOT" show "$FROZEN_COMMIT:$PLAN_MD" | awk '/^## 9\./ { f = 1 } /^## 10\./ { f = 0 } f')" = \
          "$(awk '/^## 9\./ { f = 1 } /^## 10\./ { f = 0 } f' "$ROOT/$PLAN_MD")" ]; then c61_ok=1
  else say "  expected_pair_verdicts.csv or §9 differs from $FROZEN_COMMIT"; fi
  project_down

  # ---- the pass rule ("Block D on the server"), applied mechanically. Two choices go beyond the plan's wording:
  #      a V4c file that differs only in spacing or line ends is a stop (the plan's stop list names no whitespace),
  #      and a "=> ... pair verdicts change" line without a model word is allowed (calib_lib.py: "summary"),
  #      because each verdict line it counts is classified on its own line.
  if [ "$v4a_ok" -ne 1 ] || [ "$v4b_fail" -ne 0 ] || [ "$v4b_changed" -ne 0 ] || [ "$v4c_fail" -ne 0 ] \
     || [ "$git_clean" -ne 1 ] || [ "$c61_ok" -ne 1 ] || [ "${stopc:-1}" -ne 0 ]; then verdict="V4 STOP"
  elif [ "${v4c_changed:-1}" -eq 0 ]; then verdict="V4 PASS"
  else verdict="V4 PASS WITH NOTE"; fi
  printf 'V4a %s/%s\n' "$ok" "$n"
  printf 'V4b %s changed lines%s\n' "$v4b_changed" "$([ "$v4b_fail" -ne 0 ] && echo ' (a script failed)')"
  if [ "${v4c_changed:-0}" -eq 0 ]; then printf 'V4c %s changed lines%s\n' "${v4c_changed:-?}" "$([ "$v4c_fail" -ne 0 ] && echo ' (a script failed)')"
  else printf 'V4c %s changed lines: linear %s, xgb on bc/adult %s, summary %s, stop %s%s\n' "$v4c_changed" "$lin" "$xgbc" "$summ" "$stopc" "$([ "$v4c_fail" -ne 0 ] && echo ' (a script failed)')"; fi
  printf 'git status %s\n' "$([ "$git_clean" -eq 1 ] && echo clean || echo 'NOT clean')"
  printf '%s diff %s\n' "$FROZEN_COMMIT" "$([ "$c61_ok" -eq 1 ] && echo empty || echo 'NOT empty')"
  printf 'V4 is informational: Block D runs on the Mac (Block D plan §16, 14 Oct)\n'
  case "$verdict" in
    "V4 STOP") summary "V4 STOP";;
    "V4 PASS") summary "V4 PASS";;
    *) summary "V4 PASS WITH NOTE";;
  esac
}

# ======================================================================================= main
main() {
  say "==== calib.sh $MODE $* | $(date '+%Y-%m-%d %H:%M:%S') | copy $ROOT | project $PROJECT"
  mkdir -p "$WORK"
  if [ "$MODE" != v5 ]; then
    say "  REIN_CPUSET=$REIN_CPUSET REIN_MEM=$REIN_MEM ($(gb "$REIN_MEM") GB) REIN_IMAGE_ID=$REIN_IMAGE_ID"
    if project_busy; then summary "$MODE_UC STOP compose project $PROJECT has running containers (another run?)"; return; fi
    project_down          # start from nothing: no old db volume, no old network
  fi
  trap on_interrupt INT TERM
  case "$MODE" in
    v1) mode_v1 "$@";;
    v2) mode_v2 "$@";;
    v3) mode_v3 "$@";;
    v4) mode_v4 "$@";;
    c4) mode_c4 "$@";;
    probe) mode_probe "$@";;
    v5) mode_v5 "$@";;
  esac
  return "$RESULT_RC"
}

case "$MODE" in
  v1|v2|v3|v4|c4|probe|v5) ;;
  *) sed -n '2,12p' "${BASH_SOURCE[0]}"; refuse "unknown mode '${MODE}'";;
esac

# ---- where this may run
case "$(basename "$ROOT")" in
  rein-calib|rein-v4|rein-calib-mac) ;;
  *) refuse "this is $ROOT; calib.sh runs only in a copy named rein-calib, rein-v4 or rein-calib-mac (never in the main repo)";;
esac
case "$MODE:$(basename "$ROOT")" in
  v4:rein-v4|v4:rein-calib-mac) ;;
  v4:*) refuse "v4 runs only in ~/rein-v4 (server) or ~/rein-calib-mac (Mac rehearsal)";;
  *:rein-v4) refuse "~/rein-v4 is reserved for v4 (V1-V3 rewrite the detections.csv files that V4b reads)";;
esac
cd "$ROOT" || refuse "cannot cd to $ROOT"

if [ "$MODE" != v5 ]; then
  [ -n "${REIN_CPUSET:-}" ] || refuse "export REIN_CPUSET first (cores, e.g. 0-9)"
  case "$REIN_CPUSET" in *[!0-9,-]*) refuse "REIN_CPUSET=$REIN_CPUSET is not a cpu list like 0-9";; esac
  case "${REIN_MEM:-}" in ''|*[!0-9]*) refuse "export REIN_MEM first, in bytes (e.g. 40000000000)";; esac
  [ "$REIN_MEM" -ge 1000000000 ] || refuse "REIN_MEM=$REIN_MEM bytes is below 1 GB"
  docker info > /dev/null 2>&1 || refuse "docker does not answer (are you in the docker group?)"
  REIN_IMAGE_ID=$(docker image inspect -f '{{.Id}}' "$IMAGE" 2>/dev/null)
  case "$REIN_IMAGE_ID" in
    "$EXPECTED_IMAGE_ID"|"$EXPECTED_IMAGE_CONFIG") ;;
    *) refuse "image $IMAGE has Id '${REIN_IMAGE_ID}', expected $EXPECTED_IMAGE_ID or $EXPECTED_IMAGE_CONFIG (T7/T8)";;
  esac
  export REIN_CPUSET REIN_MEM REIN_IMAGE_ID
fi

mkdir -p "$LOGDIR"
[ -f "$LOGDIR/.gitignore" ] || printf '*\n' > "$LOGDIR/.gitignore"

# Write to the terminal and append to logs/<mode>.log, unless stdout already is that file.
if perl -e 'my @a = stat(STDOUT); my @b = stat($ARGV[0]); exit((@a && @b && $a[0] == $b[0] && $a[1] == $b[1]) ? 0 : 1)' "$LOG" 2>/dev/null; then
  main "$@"
  exit $?
fi
main "$@" 2>&1 | (trap '' INT; tee -a "$LOG")      # tee ignores Ctrl-C, so the STOP line still reaches the log
exit "${PIPESTATUS[0]}"
