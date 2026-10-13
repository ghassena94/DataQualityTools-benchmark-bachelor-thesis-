#!/bin/bash
# Outlier-degree campaign (knob 2, REIN section 6.2.1 / Fig. 3c): outliers only at a fixed
# asked rate of 30 % (measured ~25 % on nasa, the label column is muted), outlier degree
# 1..10 as in run_robustness_exp, 5 configurations, one fresh container per run, no time cap.
# The injection seed does not depend on the degree, so every degree hits the same cells.
# Usage (from the repo root): bash reports/robustness/run_knob2.sh [--write_like_clean] < /dev/null
cd "$(dirname "$0")/../.."
for deg in 1 2 3 4 5 6 7 8 9 10; do
  for tier in dirty_profiled clean_profiled hand_written; do
    echo "== $(date +%T) degree $deg greatExpectations $tier"
    docker compose run --rm -T rein python3 scripts/robustness_driver.py --out reports/robustness/results.csv --dataset nasa --outlier_degree_mode \
      --error_rate 0.3 --outlier_degree "$deg" --detector greatExpectations --tier "$tier" "$@" < /dev/null 2>&1 | tail -1
  done
  for det in holoclean raha; do
    echo "== $(date +%T) degree $deg $det"
    docker compose run --rm -T rein python3 scripts/robustness_driver.py --out reports/robustness/results.csv --dataset nasa --outlier_degree_mode \
      --error_rate 0.3 --outlier_degree "$deg" --detector "$det" "$@" < /dev/null 2>&1 | tail -1
  done
done
echo "== $(date +%T) knob-2 campaign finished"
