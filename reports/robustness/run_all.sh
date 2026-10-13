#!/bin/bash
# Error-rate campaign for the robustness experiment: 6 levels x 5 configurations on nasa,
# one fresh container per run, no time cap. Levels are the NOMINAL rates asked of REIN's
# generator; the real rates are about half (1, 2, 5, 10, 19, 29 %).
# Usage (from the repo root): bash reports/robustness/run_all.sh [--write_like_clean] [--outlier_degree 4] < /dev/null
# Extra arguments are passed to every driver call (--write_like_clean = main protocol; without it = REIN's generator as is).
cd "$(dirname "$0")/../.."
LEVELS="0.02 0.04 0.10 0.20 0.40 0.60"
for rate in $LEVELS; do
  for tier in dirty_profiled clean_profiled hand_written; do
    echo "== $(date +%T) rate $rate greatExpectations $tier"
    docker compose run --rm -T rein python3 scripts/robustness_driver.py --out reports/robustness/results.csv --dataset nasa \
      --error_rate "$rate" --detector greatExpectations --tier "$tier" "$@" < /dev/null 2>&1 | tail -1
  done
  for det in holoclean raha; do
    echo "== $(date +%T) rate $rate $det"
    docker compose run --rm -T rein python3 scripts/robustness_driver.py --out reports/robustness/results.csv --dataset nasa \
      --error_rate "$rate" --detector "$det" "$@" < /dev/null 2>&1 | tail -1
  done
done
echo "== $(date +%T) campaign finished"
