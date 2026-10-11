#!/bin/bash
# Block D plan, step 0: snapshot everything that steps 2-8 can overwrite, before any regeneration.
#   - the three detection files per dataset (GE, HoloClean, Raha): regeneration overwrites them,
#     and GE dirty/clean-profiled runs write into the same file as the hand-written tier
#   - detection_results.csv and iou.csv: every benchmark run appends a row
#   - _all_constraints.txt: every HoloClean run rewrites it
#   - the Raha caches: a lost cache means a cold run, which changes Raha's results (strategy order)
#   - results/runs_log.csv
# Also records checksums of dirty.csv, clean.csv and actual_errors.csv, which must never change.
# Usage (repo root):  bash reports/block_d/step0_backup.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
B=reports/block_d/backup_20261011
[ -e "$B" ] && { echo "$B exists already; not overwriting a backup"; exit 1; }
for ds in breast_cancer nasa bike adult; do
  for f in greatExpectations/detections.csv holoclean/detections.csv raha/detections.csv \
           results/detection_results.csv results/iou.csv constraints/_all_constraints.txt; do
    mkdir -p "$B/rein-datasets/$ds/$(dirname "$f")"
    cp -p "rein-datasets/$ds/$f" "$B/rein-datasets/$ds/$f"
  done
  cp -Rp "rein-datasets/$ds/raha-baran-results-$ds" "$B/rein-datasets/$ds/"
done
mkdir -p "$B/results" && cp -p results/runs_log.csv "$B/results/"
# One manifest, paths relative to the repo root: check the backup with
#   (cd reports/block_d/backup_20261011 && shasum -a 256 -c MANIFEST.sha256)
# and the live files with
#   shasum -a 256 -c reports/block_d/backup_20261011/MANIFEST.sha256
(cd "$B" && find . -type f ! -name '*.sha256' -print0 | sort -z | xargs -0 shasum -a 256 | sed 's#  \./#  #') > "$B/MANIFEST.sha256"
shasum -a 256 rein-datasets/{breast_cancer,nasa,bike,adult}/{dirty.csv,clean.csv,actual_errors.csv} > "$B/INPUTS.sha256"
echo "backup: $B, $(wc -l < "$B/MANIFEST.sha256" | tr -d ' ') files, $(du -sh "$B" | cut -f1)"
