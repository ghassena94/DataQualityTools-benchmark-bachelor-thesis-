####################################################
# Scalability driver: one (dataset, axis, fraction, detector) per process.
#
# Runs a detector on a row or column fraction of a dataset WITHOUT touching
# the dataset's own files: the fraction is written to a scratch dataset
# directory datasets/<name>_<axis><pct>/ that is registered in the dataset
# and expectation dictionaries at runtime and deleted afterwards. Each call
# is meant to run in its own container, so the container's cgroup peak
# (/sys/fs/cgroup/memory.peak) is the peak memory of exactly this run,
# worker processes included.
#
# Output: one row appended to the CSV given by --out (required).
# Added 2026-09-26 for thesis section 5.2.6.
####################################################

import argparse
import copy
import csv
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd

from rein.auxiliaries.configurations import DetectMethod
from rein.auxiliaries.datasets_dictionary import datasets_dictionary, datasets_path
from rein.auxiliaries import expectations_dictionary as ed
from rein.datasets import Database

OUT_FIELDS = ['dataset', 'axis', 'fraction', 'rows', 'cols', 'detector', 'tier',
              'status', 'precision', 'recall', 'f1', 'cell_TP', 'cell_FP', 'cell_FN',
              'cell_FG1', 'detections', 'runtime_s', 'wall_s', 'peak_mem_bytes',
              'baseline_mem_bytes', 'scratch', 'timestamp']


def read_peak():
    for p in ('/sys/fs/cgroup/memory.peak', '/sys/fs/cgroup/memory/memory.max_usage_in_bytes'):
        try:
            with open(p) as f:
                return int(f.read().strip())
        except (OSError, ValueError):
            continue
    return -1


def append_row(out_path, row):
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    new = not os.path.exists(out_path)
    with open(out_path, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, '') for k in OUT_FIELDS})


def make_fraction(src_dir, dst_dir, axis, fraction, seed):
    """Write dirty.csv and clean.csv of the fraction into dst_dir. Fractions are
    nested: the same permutation is used for every fraction and the first
    round(fraction * n) elements are kept, in their original order."""
    dirty = pd.read_csv(os.path.join(src_dir, 'dirty.csv'), dtype=str, keep_default_na=False)
    clean = pd.read_csv(os.path.join(src_dir, 'clean.csv'), dtype=str, keep_default_na=False)
    assert dirty.shape == clean.shape, 'dirty and clean differ in shape'
    assert set(dirty.columns) == set(clean.columns), 'dirty and clean differ in column set'
    # mercedes lists its columns in a different order in clean.csv; align by
    # name onto the dirty order, as the benchmark's ground-truth oracle does.
    clean = clean[list(dirty.columns)]
    rng = np.random.RandomState(seed)
    if axis == 'rows':
        n = dirty.shape[0]
        k = max(1, int(round(fraction * n)))
        keep = np.sort(rng.permutation(n)[:k]) if fraction < 1 else np.arange(n)
        dirty, clean = dirty.iloc[keep], clean.iloc[keep]
    else:
        d = dirty.shape[1]
        k = max(1, int(round(fraction * d)))
        keep = np.sort(rng.permutation(d)[:k]) if fraction < 1 else np.arange(d)
        dirty, clean = dirty.iloc[:, keep], clean.iloc[:, keep]
    os.makedirs(dst_dir, exist_ok=True)
    dirty.to_csv(os.path.join(dst_dir, 'dirty.csv'), index=False)
    clean.to_csv(os.path.join(dst_dir, 'clean.csv'), index=False)
    return dirty.shape


def register(base, scratch, dst_dir, columns):
    entry = copy.deepcopy(datasets_dictionary[base])
    entry['name'] = scratch
    entry['dataset_path'] = os.path.abspath(dst_dir)
    entry['dirty_path'] = os.path.abspath(os.path.join(dst_dir, 'dirty.csv'))
    entry['groundTruth_path'] = os.path.abspath(os.path.join(dst_dir, 'clean.csv'))
    for key in ('labels_reg', 'labels_clf', 'labels_cls', 'excluded_attribs', 'keys'):
        if key in entry:
            entry[key] = [c for c in entry[key] if c in columns]
    datasets_dictionary[scratch] = entry
    # hand-written suite: same rules, restricted to the columns that exist
    if base in ed.DATASET_EXPECTATIONS:
        suite = ed.DATASET_EXPECTATIONS[base]
        ed.DATASET_EXPECTATIONS[scratch] = {
            tier: [rule for rule in rules if rule.get('column') in columns]
            for tier, rules in suite.items()
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--axis', choices=['rows', 'cols'], required=True)
    ap.add_argument('--fraction', type=float, required=True)
    ap.add_argument('--detector', choices=['greatExpectations', 'holoclean', 'raha'], required=True)
    ap.add_argument('--tier', default=os.environ.get('EXPECTATION_TIER', 'hand_written'))
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--out', required=True,
                    help='CSV the result row is appended to (created with a header if missing)')
    args = ap.parse_args()

    if args.detector == 'greatExpectations':
        os.environ['EXPECTATION_TIER'] = args.tier
    tier = args.tier if args.detector == 'greatExpectations' else ''

    pct = int(round(args.fraction * 100))
    # detector and tier are part of the scratch name so that two runners never
    # share a scratch directory (a shared one cost a HoloClean run on 26 Sep)
    scratch = '{}_{}{}_{}'.format(args.dataset, 'r' if args.axis == 'rows' else 'c', pct,
                                  args.detector + ('_' + tier if tier else ''))
    src_dir = datasets_dictionary[args.dataset]['dataset_path']
    dst_dir = os.path.join(datasets_path, scratch)
    baseline = read_peak()
    row = dict(dataset=args.dataset, axis=args.axis, fraction=args.fraction, detector=args.detector,
               tier=tier, scratch=scratch, baseline_mem_bytes=baseline,
               timestamp=time.strftime('%Y-%m-%dT%H:%M:%S'))
    db = Database()
    t0 = time.time()
    try:
        if os.path.exists(dst_dir):
            shutil.rmtree(dst_dir)
        for tbl in ('dirty_' + scratch, 'ground_truth_' + scratch):
            if db.db_table_exists_postgresql(tbl):
                db.remove_table_postgres(tbl)
        shape = make_fraction(src_dir, dst_dir, args.axis, args.fraction, args.seed)
        row['rows'], row['cols'] = shape
        # HoloClean reads datasets/<name>/constraints/_all_constraints.txt
        cdir = os.path.join(src_dir, 'constraints')
        if os.path.isdir(cdir):
            shutil.copytree(cdir, os.path.join(dst_dir, 'constraints'))
        columns = list(pd.read_csv(os.path.join(dst_dir, 'dirty.csv'), nrows=0).columns)
        register(args.dataset, scratch, dst_dir, columns)

        from rein.benchmark import Benchmark  # imports datawig etc.; keep after the cheap steps
        app = Benchmark(False, log_label='scalability-{}-{}-{}'.format(scratch, args.detector, tier or 'x'))
        app.run_detectors(pct, [scratch], [DetectMethod(args.detector)], iterations=1)

        res_path = os.path.join(dst_dir, 'results', 'detection_results.csv')
        res = pd.read_csv(res_path).iloc[-1]
        row.update(status='ok', precision=res['precision'], recall=res['recall'], f1=res['f1'],
                   cell_TP=res['cell_TP'], cell_FP=res['cell_FP'], cell_FN=res['cell_FN'],
                   cell_FG1=res.get('cell_FG1', ''), detections=res['#detections'],
                   runtime_s=res['detection_runtime'])
    except Exception as e:  # noqa: BLE001
        row.update(status='error: {}'.format(type(e).__name__))
        print('scalability_driver failed: {!r}'.format(e), file=sys.stderr)
    finally:
        row['wall_s'] = round(time.time() - t0, 1)
        row['peak_mem_bytes'] = read_peak()
        append_row(args.out, row)
        shutil.rmtree(dst_dir, ignore_errors=True)
        for tbl in ('dirty_' + scratch, 'ground_truth_' + scratch):
            try:
                if db.db_table_exists_postgresql(tbl):
                    db.remove_table_postgres(tbl)
            except Exception:  # noqa: BLE001
                pass
    print('done', scratch, row.get('status'), 'f1=', row.get('f1'), 'peak=', row['peak_mem_bytes'])
    sys.exit(0 if row.get('status') == 'ok' else 1)


if __name__ == '__main__':
    main()
