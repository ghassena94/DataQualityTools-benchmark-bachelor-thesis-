#!/bin/bash
# Block D plan, step 9: put back the step-0 snapshot so the benchmark's stored state is what the thesis reports.
# Default is a dry run: it lists which live files differ from the snapshot and changes nothing.
#   bash reports/block_d/step9_restore.sh            # dry run
#   bash reports/block_d/step9_restore.sh --apply    # restore detection files, results and constraints
#   bash reports/block_d/step9_restore.sh --apply --cache   # also replace the Raha caches (only if damaged)
# The frozen Block D flags live in reports/block_d/flags/ and are not touched.
set -eu
cd "$(dirname "$0")/../.."
B=reports/block_d/backup_20261011
APPLY=0; CACHE=0
for a in "$@"; do case "$a" in --apply) APPLY=1;; --cache) CACHE=1;; *) echo "unknown option $a"; exit 1;; esac; done
echo "== backup intact?"; (cd "$B" && shasum -a 256 -c --quiet MANIFEST.sha256) && echo "yes"
echo "== inputs unchanged?"; shasum -a 256 -c --quiet "$B/INPUTS.sha256" && echo "yes"
diffs=$(shasum -a 256 -c "$B/MANIFEST.sha256" 2>/dev/null | grep -v ': OK$' || true)
ncache=$(printf '%s\n' "$diffs" | awk '/\/raha-baran-results-/ {n++} END {print n+0}')
other=$(printf '%s\n' "$diffs" | awk 'NF && !/\/raha-baran-results-/')
echo "== Raha cache files that differ from the snapshot: $ncache"
echo "== other live files that differ from the snapshot:"
if [ -n "$other" ]; then printf '%s\n' "$other" | sed 's/^/   /'; else echo "   none"; fi
[ "$APPLY" = 1 ] || { echo "dry run: nothing changed"; exit 0; }
for ds in breast_cancer nasa bike adult; do
  for f in greatExpectations/detections.csv holoclean/detections.csv raha/detections.csv \
           results/detection_results.csv results/iou.csv constraints/_all_constraints.txt; do
    cp -p "$B/rein-datasets/$ds/$f" "rein-datasets/$ds/$f"
  done
  if [ "$CACHE" = 1 ]; then
    rm -rf "rein-datasets/$ds/raha-baran-results-$ds"
    cp -Rp "$B/rein-datasets/$ds/raha-baran-results-$ds" "rein-datasets/$ds/"
  fi
done
cp -p "$B/results/runs_log.csv" results/runs_log.csv
echo "restored; check: shasum -a 256 -c $B/MANIFEST.sha256 | grep -v ': OK$'"
