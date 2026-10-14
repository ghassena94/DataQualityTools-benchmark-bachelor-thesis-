#!/usr/bin/env bash
# Write the environment record and the checksum manifest for the move to the server.
# Server plan 2026-10-13, P0 step 4; migration recipe in reports/cleanup_manifest_2026-10-13.md section 5.
#
#   bash scripts/make_env_manifest.sh [record_name]      (on the Mac; record_name defaults to mac_<today>)
#
# Outputs (nothing else is written):
#   env/MANIFEST.sha256               sha256 of every file the server needs byte-identical (shasum -a 256 format,
#                                     paths relative to the repo root, sorted by path)
#   env/order_manifest.json           os.listdir order of the seven Raha strategy-profiling folders, inside the
#                                     container (*.json is git-ignored: commit it with git add -f)
#   env/<record_name>/                uname (without the host name), Docker, image, pip freeze, BLAS thread pools,
#                                     numpy CPU features, CPU counts and the Block D host fingerprint, all from
#                                     inside the container where the server needs them
#   server_env/rein-move-excludes.txt the rsync exclude list for rein-datasets/ (cleanup manifest 5.2)
#
# Every output is rebuilt in a temporary folder and then moved into place, and no output holds a timestamp or a
# container ID. A rerun rewrites byte-identical files only at the same git HEAD, on the same Mac and Docker:
# pip_freeze.txt's one editable line names the HEAD commit, and it exists only while the untracked
# tools/error-generator/errorgenerator.egg-info/ is on the mount.
# Read-only on rein-datasets/ and on reports/block_d/backup_*. Docker runs only three read-only python3 calls in
# the rein container with --no-deps (no Postgres) and the Block D thread settings.
set -euo pipefail

REPO=$(cd "$(dirname "$0")/.." && pwd)
cd "$REPO"
REC=${1:-mac_$(date +%Y%m%d)}
# Letters, digits, _ . - only, and no leading dot: ".." would make the install step below delete env/../*.txt.
case "$REC" in .*|*[!A-Za-z0-9_.-]*|'') echo "bad record name: $REC"; exit 1;; esac
OUT=env/$REC
IMAGE=rein-benchmark-rein:latest
DATASETS="breast_cancer nasa beers bike adult smartfactory soilmoisture har mercedes"
CACHES="breast_cancer:305 nasa:125 beers:511 bike:508 adult:513 smartfactory:568 soilmoisture:18103"
LIVE="breast_cancer nasa bike adult"
SUITE=rein/auxiliaries/expectations_dictionary_local.py
BACKUP=reports/block_d/backup_20261011
MAC_CORE=reports/block_d/runs/2026-10-13_mac_core/manifest.json
TMP=$(mktemp -d "${TMPDIR:-/tmp}/make_env_manifest.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/rec"

say()  { printf '\n==> %s\n' "$*"; }
cmd()  { printf '    $ %s\n' "$*"; }
info() { printf '    %s\n' "$*"; }
die()  { printf 'STOP: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------------------------------- 1. excludes
say "1/9 Write the rsync exclude list for rein-datasets/ (cleanup manifest 5.2) to server_env/rein-move-excludes.txt"
printf '%s\n' '.DS_Store' '__pycache__/' '/*/raha-baran-results-*/error-detection/' \
    '/*/raha-baran-results-*.truncated-*/' '/har/raha-baran-results-har/' '/mercedes/raha-baran-results-mercedes/' \
    > "$TMP/excludes.txt"
sed 's/^/    | /' "$TMP/excludes.txt"

# ---------------------------------------------------------------------------------------------------- 2. file list
say "2/9 List the files the server needs byte-identical"
: > "$TMP/paths.txt"
need() { [ -f "$1" ] || die "missing $1"; echo "$1" >> "$TMP/paths.txt"; }
n_inputs=0; n_constraints=0; n_fd=0; n_results=0; n_emb=0; n_live=0; n_cache=0
for d in $DATASETS; do
  p=rein-datasets/$d
  for f in dirty.csv clean.csv actual_errors.csv error_rate.json; do need "$p/$f"; n_inputs=$((n_inputs + 1)); done
  for f in results/detection_results.csv results/iou.csv; do need "$p/$f"; n_results=$((n_results + 1)); done
  [ -d "$p/constraints" ] || die "missing $p/constraints/"
  c=$(find "$p/constraints" -type f ! -name .DS_Store | tee -a "$TMP/paths.txt" | wc -l | tr -d ' ')
  n_constraints=$((n_constraints + c))
  c=$(find "$p" -maxdepth 1 -type f -name '*_FDs_by_col.txt' | tee -a "$TMP/paths.txt" | wc -l | tr -d ' ')
  n_fd=$((n_fd + c))
  if [ -d "$p/embeddings" ]; then
    c=$(find "$p/embeddings" -type f ! -name .DS_Store | tee -a "$TMP/paths.txt" | wc -l | tr -d ' ')
    n_emb=$((n_emb + c))
  fi
done
for d in $LIVE; do
  for t in greatExpectations holoclean raha; do need "rein-datasets/$d/$t/detections.csv"; n_live=$((n_live + 1)); done
done
for dc in $CACHES; do
  d=${dc%%:*}; want=${dc#*:}
  sp=rein-datasets/$d/raha-baran-results-$d/strategy-profiling
  [ -d "$sp" ] || die "missing $sp"
  [ -z "$(find "$sp" -mindepth 1 ! -type f -print -quit)" ] || die "$sp holds something other than plain files"
  c=$(find "$sp" -type f | tee -a "$TMP/paths.txt" | wc -l | tr -d ' ')
  [ "$c" = "$want" ] || die "$sp has $c files, expected $want (incomplete cache)"
  info "cache $d: $c files"
  n_cache=$((n_cache + c))
done
need "$SUITE"
LC_ALL=C sort "$TMP/paths.txt" > "$TMP/paths.sorted"
[ -z "$(uniq -d "$TMP/paths.sorted")" ] || die "a path is listed twice"
if grep -E '\.DS_Store|__pycache__|/error-detection/|\.truncated-|\.partial-|raha-baran-results-(har|mercedes)' \
     "$TMP/paths.sorted"; then die "the list holds a path that must not travel (cleanup manifest 5.2)"; fi
total=$(wc -l < "$TMP/paths.sorted" | tr -d ' ')
info "inputs (dirty, clean, actual_errors, error_rate.json) $n_inputs; constraints/ $n_constraints; FD files $n_fd"
info "results/{detection_results,iou}.csv $n_results; embeddings/ $n_emb; live detections.csv $n_live"
info "Raha strategy-profiling caches $n_cache; suite file 1; total $total"

# ---------------------------------------------------------------------------------------------------- 3. hashes
say "3/9 Hash them in path order into env/MANIFEST.sha256"
cmd "tr '\\n' '\\0' < <sorted list> | xargs -0 shasum -a 256 > env/MANIFEST.sha256"
tr '\n' '\0' < "$TMP/paths.sorted" | xargs -0 shasum -a 256 > "$TMP/MANIFEST.sha256"
[ "$(wc -l < "$TMP/MANIFEST.sha256" | tr -d ' ')" = "$total" ] || die "shasum wrote a different number of lines"

# ---------------------------------------------------------------------------------------------------- 4. rsync check
say "4/9 Check the exclude list against the manifest with a local rsync dry run (copies nothing)"
cmd "rsync -a -n -v --exclude-from=server_env/rein-move-excludes.txt rein-datasets/ <empty temp folder>/"
rsync -a -n -v --exclude-from="$TMP/excludes.txt" rein-datasets/ "$TMP/rsync_dst/" > "$TMP/rsync.txt"
grep -v -e '/$' -e '^Transfer starting' -e '^sent ' -e '^total size' -e '^$' "$TMP/rsync.txt" \
  | LC_ALL=C sort > "$TMP/rsync.files"
grep '^rein-datasets/' "$TMP/paths.sorted" | sed 's|^rein-datasets/||' > "$TMP/hashed.files"
missing=$(LC_ALL=C comm -23 "$TMP/hashed.files" "$TMP/rsync.files" | wc -l | tr -d ' ')
leaked=$(grep -cE '\.DS_Store|__pycache__|/error-detection/|\.truncated-|\.partial-|raha-baran-results-(har|mercedes)' \
         "$TMP/rsync.files" || true)
sent=$(wc -l < "$TMP/rsync.files" | tr -d ' ')
info "rsync would send $sent files ($(grep '^total size' "$TMP/rsync.txt" | sed 's/  speedup.*//')); hashed: $(wc -l < "$TMP/hashed.files" | tr -d ' '); not hashed: $((sent - $(wc -l < "$TMP/hashed.files")))"
info "hashed files the rsync would skip: $missing; excluded paths the rsync would send: $leaked"
# Empty folders travel too (rsync -a keeps them, git does not). An existing embeddings/ folder switches the
# Profiler to load mode (rein/datasets.py:539), so the server must get the same ones.
n_empty=$(grep -v -e '^Transfer starting' -e '^sent ' -e '^total size' -e '^$' -e '^\./$' "$TMP/rsync.txt" | awk '
  { p = $0; isdir = sub(/\/$/, "", p); if (isdir) d[p] = 1; k = p; if (sub(/\/[^\/]*$/, "", k)) c[k] = 1 }
  END { for (x in d) if (!(x in c)) n++; print n + 0 }')
info "empty folders the rsync would create: $n_empty (on the server: find rein-datasets -type d -empty | wc -l)"
[ "$missing" = 0 ] && [ "$leaked" = 0 ] || die "the exclude list and the manifest disagree"

# ---------------------------------------------------------------------------------------------------- 5. backup check
say "5/9 Compare with the Block D step-0 snapshot hashes (read-only; after the step-9 restore they must agree)"
cat "$BACKUP/MANIFEST.sha256" "$BACKUP/INPUTS.sha256" | awk '
  NR == FNR { h[substr($0, 67)] = $1; next }
  { p = substr($0, 67); if (p in h) { n++; if (h[p] != $1) { d++; print "    differs: " p } } }
  END { printf "    paths in both: %d; different hashes: %d\n", n, d + 0; exit (d > 0) }' - "$TMP/MANIFEST.sha256" \
  || die "a live file differs from the step-0 snapshot (run reports/block_d/step9_restore.sh for details)"

# ---------------------------------------------------------------------------------------------------- 6. host
say "6/9 Record the Mac, Docker and the image"
cmd "uname -srvm   (uname -a without the host name)"; uname -srvm > "$TMP/rec/uname.txt"
cmd "sysctl -n machdep.cpu.brand_string hw.ncpu hw.memsize"
{ printf 'cpu %s\n' "$(sysctl -n machdep.cpu.brand_string)"; printf 'hw.ncpu %s\n' "$(sysctl -n hw.ncpu)"
  printf 'hw.memsize_bytes %s\n' "$(sysctl -n hw.memsize)"; printf 'macOS %s\n' "$(sw_vers -productVersion)"; } \
  > "$TMP/rec/host_hardware.txt"
cmd "docker version; docker compose version"
{ docker version; echo; docker compose version; } > "$TMP/rec/docker_version.txt"
cmd "docker info --format '<NCPU, MemTotal, ...>'"
docker info --format 'NCPU {{.NCPU}}
MemTotal_bytes {{.MemTotal}}
ServerVersion {{.ServerVersion}}
OperatingSystem {{.OperatingSystem}}
OSType {{.OSType}}
Architecture {{.Architecture}}
KernelVersion {{.KernelVersion}}
CgroupVersion {{.CgroupVersion}}
CgroupDriver {{.CgroupDriver}}
StorageDriver {{.Driver}}' > "$TMP/rec/docker_info.txt"
awk '/^MemTotal_bytes/ {printf "MemTotal_GB %.1f (decimal)\n", $2 / 1e9}' "$TMP/rec/docker_info.txt" >> "$TMP/rec/docker_info.txt"
cmd "docker image inspect $IMAGE"
docker image inspect -f 'Id {{.Id}}
Architecture {{.Architecture}}
Os {{.Os}}
Size_bytes {{.Size}}
RepoTags {{join .RepoTags " "}}' "$IMAGE" > "$TMP/rec/image.txt"
IMAGE_ID=$(awk '/^Id / {print $2}' "$TMP/rec/image.txt")
# The containerd image store reports the OCI index digest as Id; a classic overlay2 store reports the config
# digest after docker load. Record the config digest from the saved tar, so the server's Id can be checked too.
TAR=${REIN_IMAGE_TAR:-$HOME/rein-transfer/rein-image.tar.gz}
if [ -f "$TAR" ]; then
  cmd "gunzip -c $TAR | tar -xOf - index.json manifest.json"
  gunzip -c "$TAR" | tar -xOf - index.json manifest.json | python3 -c '
import json, sys
dec = json.JSONDecoder(); s = sys.stdin.read().strip()
index, end = dec.raw_decode(s); manifest = dec.raw_decode(s[end:].strip())[0]
print(index["manifests"][0]["digest"], "sha256:" + manifest[0]["Config"].rsplit("/", 1)[1])' > "$TMP/tar_digests"
  read -r TAR_INDEX TAR_CONFIG < "$TMP/tar_digests"
  [ "$TAR_INDEX" = "$IMAGE_ID" ] || die "$TAR holds image $TAR_INDEX, not the current $IMAGE_ID: save it again"
  echo "ConfigDigest $TAR_CONFIG" >> "$TMP/rec/image.txt"
else
  echo "ConfigDigest unknown (no saved image at $TAR)" >> "$TMP/rec/image.txt"
fi
sed 's/^/    | /' "$TMP/rec/docker_info.txt" "$TMP/rec/image.txt" | grep -E 'NCPU|MemTotal|Id |Architecture|ConfigDigest'

# The one container command: no Postgres (--no-deps), python3 instead of the waiting entrypoint, Block D threads.
RUN=(docker compose run --rm -T --no-deps --entrypoint python3
     -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -e MKL_NUM_THREADS=1 -e PYTHONHASHSEED=0
     -e REIN_IMAGE_ID="$IMAGE_ID" -e GIT_OPTIONAL_LOCKS=0 rein -B)
incontainer() {   # $1 = output file, rest = python3 arguments; stdout is the result, stderr goes to a log
  local out=$1; shift
  "${RUN[@]}" "$@" < /dev/null > "$out" 2> "$TMP/docker.err" || { cat "$TMP/docker.err" >&2; die "container call failed"; }
}

# ---------------------------------------------------------------------------------------------------- 7. pip freeze
say "7/9 List the installed Python packages inside the container"
cmd "docker compose run --rm -T --no-deps --entrypoint python3 <Block D -e settings> rein -B -m pip freeze"
incontainer "$TMP/rec/pip_freeze.txt" -m pip freeze
info "$(wc -l < "$TMP/rec/pip_freeze.txt" | tr -d ' ') packages"

# ---------------------------------------------------------------------------------------------------- 8. fingerprint
say "8/9 Ask blockd_driver.check_environment what it sees inside the container (threads, CPU features, fingerprint)"
cmd "docker compose run ... rein -B -c 'load scripts/blockd_driver.py; print(check_environment(\"dry_run\", ...))'"
incontainer "$TMP/env.json" -c '
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("blockd_driver", "/rein/scripts/blockd_driver.py")
drv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drv)
env = drv.check_environment("dry_run", lambda m: print(m, file=sys.stderr))
keep = ["host_fingerprint", "machine", "platform", "versions", "threadpool_info", "cpu_features",
        "sched_affinity", "cpu_count_unreliable", "variables"]
print(json.dumps({k: env[k] for k in keep}, sort_keys=True))'
python3 -I - "$TMP/env.json" "$TMP/rec" "$MAC_CORE" <<'PY'
import hashlib, json, os, sys
env = json.load(open(sys.argv[1])); rec = sys.argv[2]
feats = sorted(k for k, v in env['cpu_features'].items() if v)
fp = '{}:{}'.format(env['machine'], hashlib.sha256(','.join(feats).encode()).hexdigest()[:12])
assert fp == env['host_fingerprint'], (fp, env['host_fingerprint'])
def write(name, text):
    with open(os.path.join(rec, name), 'w') as f:
        f.write(text)
write('threadpool_info.txt', json.dumps(env['threadpool_info'], indent=1, sort_keys=True) + '\n')
write('cpu_features.txt', ','.join(feats) + '\n')
write('cpu_count.txt', 'os.cpu_count() {}\nlen(os.sched_getaffinity(0)) {}\n'.format(
    env['cpu_count_unreliable'], env['sched_affinity']))
lines = ['host_fingerprint ' + env['host_fingerprint'],
         "rule platform.machine() + ':' + sha256(','.join(sorted true numpy __cpu_features__ keys))[:12]",
         'machine ' + env['machine'], 'platform ' + env['platform']]
lines += ['version {} {}'.format(k, v) for k, v in sorted(env['versions'].items())]
lines += ['variable {}={}'.format(k, v) for k, v in sorted(env['variables'].items())]
write('host_fingerprint.txt', '\n'.join(lines) + '\n')
archs = sorted({p.get('architecture') for p in env['threadpool_info'] if p.get('internal_api') == 'openblas'})
path = os.path.join(rec, 'openblas_coretype.txt')
pools = ', '.join('{} {} threads={}'.format(p.get('internal_api'), p.get('architecture', '-'), p.get('num_threads'))
                  for p in env['threadpool_info'])
print('    thread pools: ' + pools)
print('    numpy CPU features ({}): {}'.format(len(feats), ','.join(feats)))
print('    os.cpu_count() {}, len(os.sched_getaffinity(0)) {}'.format(env['cpu_count_unreliable'], env['sched_affinity']))
if len(archs) == 1 and archs[0]:
    write('openblas_coretype.txt', archs[0] + '\n')
    print('    numpy and scipy OpenBLAS agree on {}: wrote openblas_coretype.txt'.format(archs[0]))
else:
    print('    OpenBLAS architectures differ ({}): no openblas_coretype.txt, so no OPENBLAS_CORETYPE pin'.format(
        ' vs '.join(map(str, archs))))
core = json.load(open(sys.argv[3]))['environment']['host_fingerprint'] if os.path.exists(sys.argv[3]) else None
print('    host_fingerprint {} ({} the 13 Oct Mac core run: {})'.format(
    env['host_fingerprint'], 'same as' if core == env['host_fingerprint'] else 'DIFFERENT from', core))
PY

# ---------------------------------------------------------------------------------------------------- 9. listdir order
say "9/9 Record the os.listdir order of the seven Raha caches inside the container into env/order_manifest.json"
cmd "docker compose run ... rein -B -c 'os.listdir(\"/rein/datasets/<ds>/raha-baran-results-<ds>/strategy-profiling\")'"
incontainer "$TMP/order.json" -c '
import json, os
out = {}
for ds in "'"$(for dc in $CACHES; do printf '%s ' "${dc%%:*}"; done)"'".split():
    out[ds] = os.listdir("/rein/datasets/{0}/raha-baran-results-{0}/strategy-profiling".format(ds))
print(json.dumps(out))'
python3 -I - "$TMP/order.json" "$TMP/order_manifest.json" "$IMAGE_ID" "$CACHES" <<'PY'
import hashlib, json, os, sys
seen = json.load(open(sys.argv[1]))
caches, total = {}, 0
for item in sys.argv[4].split():
    ds, want = item.split(':')
    names = seen[ds]
    assert len(names) == int(want), (ds, len(names), want)
    host = os.listdir('rein-datasets/{0}/raha-baran-results-{0}/strategy-profiling'.format(ds))
    caches[ds] = dict(files=len(names), sha256=hashlib.sha256('\n'.join(names).encode('utf-8')).hexdigest(),
                      equals_sorted=names == sorted(names), equals_host_listdir=names == host, order=names)
    total += len(names)
    print('    {:<13} {:>6} files  sha256 {}  sorted: {}  same as host listdir: {}'.format(
        ds, len(names), caches[ds]['sha256'][:16], caches[ds]['equals_sorted'], caches[ds]['equals_host_listdir']))
doc = dict(
    what='os.listdir order of each complete Raha strategy-profiling folder, seen inside the rein container on '
         'the Mac. Cached Raha reads its strategies in this order (raha/detection.py, os.listdir(sp_folder_path)).',
    taken_with='docker compose run --rm -T --no-deps --entrypoint python3 rein -B -c "os.listdir(...)"',
    container_path='/rein/datasets/<ds>/raha-baran-results-<ds>/strategy-profiling',
    image_id=sys.argv[3],
    sha256_rule='sha256 of the UTF-8 file names joined by one newline, in listdir order, no trailing newline',
    total_files=total, caches=caches)
with open(sys.argv[2], 'w') as f:
    json.dump(doc, f, indent=1)
    f.write('\n')
print('    total {} files'.format(total))
PY

# ---------------------------------------------------------------------------------------------------- install
say "Move the new files into place"
mkdir -p env server_env "$OUT"
mv "$TMP/excludes.txt" server_env/rein-move-excludes.txt
mv "$TMP/MANIFEST.sha256" env/MANIFEST.sha256
mv "$TMP/order_manifest.json" env/order_manifest.json
rm -f "$OUT"/*.txt
mv "$TMP"/rec/*.txt "$OUT"/
info "server_env/rein-move-excludes.txt  env/MANIFEST.sha256 ($total lines)  env/order_manifest.json"
info "$OUT/: $(cd "$OUT" && ls | tr '\n' ' ')"

say "Verify env/MANIFEST.sha256 against the files on disk"
cmd "shasum -a 256 -c env/MANIFEST.sha256 | grep -vc ': OK\$'"
bad=$(shasum -a 256 -c env/MANIFEST.sha256 2>&1 | grep -vc ': OK$' || true)
info "lines that are not OK: $bad"
[ "$bad" = 0 ] || die "checksum verification failed"
echo "DONE"
