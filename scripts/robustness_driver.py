####################################################
# Robustness driver (REIN section 6.2.1): one (dataset, level, detector) per process.
# Error-rate mode (knob 1): outliers + explicit missing values at --error_rate.
# Outlier-degree mode (knob 2, --outlier_degree_mode): outliers only at a fixed rate
# (REIN: 30 %), the degree varies; added 2026-10-02.
#
# Generates a dirty version of a dataset at a given error rate with REIN's own
# injector (Datasets.inject_errors: outliers + explicit missing values, labels
# muted), exactly as Benchmark.run_robustness_exp does, but WITHOUT touching the
# dataset's own files: clean.csv is copied to a scratch directory
# datasets/<scratch>/, registered in the dataset and expectation
# dictionaries at runtime, the dirty version is injected there, the detector is
# run, and the scratch directory and its Postgres tables are deleted afterwards.
# Injection is seeded per (seed, rate) only (not per degree, since 2 Oct), so every
# configuration of one level, and every degree at one rate, sees the same injected cells;
# the sha256 of each dirty file is recorded. Scratch names: <ds>_e<pct>[c][_d<k>]_<conf>
# (knob 1) and <ds>_o<k>[c]_<conf> (knob 2); c = write_like_clean (main protocol), no letter =
# REIN's generator as is. Earlier rewriting variants (30 Sep rounding, 2 Oct format_like_clean)
# were removed on 3 Oct together with their runs.
#
# Output: one row appended to the CSV given by --out (required).
# Added 2026-09-26 for the thesis robustness subsection.
####################################################

import argparse
import copy
import csv
import hashlib
import json
import os
import random
import shutil
import sys
import time

import numpy as np
import pandas as pd

from rein.auxiliaries.configurations import DetectMethod, ErrorType, outliers
from rein.auxiliaries.datasets_dictionary import datasets_dictionary, datasets_path
from rein.auxiliaries import expectations_dictionary as ed
from rein.datasets import Database, Datasets

OUT_FIELDS = ['dataset', 'mode', 'level', 'outlier_degree', 'rows', 'cols', 'detector', 'tier',
              'status', 'measured_error_rate', 'precision', 'recall', 'f1', 'cell_TP', 'cell_FP',
              'cell_FN', 'cell_FG1', 'detections', 'runtime_s', 'wall_s', 'seed', 'dirty_sha256',
              'scratch', 'timestamp']


def append_row(out_path, row):
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    new = not os.path.exists(out_path)
    with open(out_path, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, '') for k in OUT_FIELDS})


def register(base, scratch, dst_dir):
    entry = copy.deepcopy(datasets_dictionary[base])
    entry['name'] = scratch
    entry['dataset_path'] = os.path.abspath(dst_dir)
    entry['dirty_path'] = os.path.abspath(os.path.join(dst_dir, 'dirty.csv'))
    entry['groundTruth_path'] = os.path.abspath(os.path.join(dst_dir, 'clean.csv'))
    datasets_dictionary[scratch] = entry
    # hand-written suite: the same rules as the base dataset
    if base in ed.DATASET_EXPECTATIONS:
        ed.DATASET_EXPECTATIONS[scratch] = copy.deepcopy(ed.DATASET_EXPECTATIONS[base])
    return entry


def muted_columns(entry):
    # same rule as Benchmark.run_robustness_exp: the ML labels stay clean
    muted = []
    if 'regression' in entry['ml_tasks']:
        muted.extend(entry['labels_reg'])
    if 'classification' in entry['ml_tasks']:
        muted.extend(entry['labels_clf'])
    return muted


def decimals(value):
    return len(value.split('.', 1)[1]) if '.' in value else 0


def sig_digits(value):
    """Significant digits of a plain decimal string ("0.00266337" -> 6, "1250.0" -> 3; only used
    for significant-figure columns such as nasa's thickness)."""
    return len(value.lstrip('-').replace('.', '').lstrip('0').rstrip('0') or '0')


def clean_style(values):
    """How a clean column writes its numbers: fixed printed decimals (every value has the same
    number of decimals) or significant figures (decimals vary with the magnitude, as nasa's
    thickness), plus whether any value ends in 0."""
    vals = [v for v in values if v != '']
    decs = {decimals(v) for v in vals}
    style = dict(ends_in_zero=any(v.endswith('0') for v in vals))
    if len(decs) == 1:
        style.update(kind='fixed', printed=decs.pop(),
                     sig_dec=max(len(v.split('.', 1)[1].rstrip('0')) if '.' in v else 0 for v in vals))
    else:
        style.update(kind='sigfig', sig=max(sig_digits(v) for v in vals))
    return style


def write_value(value, st):
    if st['kind'] == 'fixed':
        # round to the decimals the column really uses, print with its fixed width
        unit = 10.0 ** -st['sig_dec']
        s = ('{:.%df}' % st['printed']).format(round(value, st['sig_dec']))
    else:
        # round to the column's significant figures, plain decimal, no trailing zeros
        if value == 0:
            return '0'
        exp = int(np.floor(np.log10(abs(value))))
        nd = max(st['sig'] - 1 - exp, 0)
        unit = 10.0 ** -nd
        s = ('{:.%df}' % nd).format(round(value, nd))
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
    if not st['ends_in_zero'] and s.endswith('0'):
        # the clean column never ends in 0: move the last written digit by one unit
        # (one step of the column's own precision), away from zero
        v = float(s) + (unit if float(s) >= 0 else -unit)
        return write_value(v, st)
    if float(s) == 0:
        s = s.lstrip('-')     # never write "-0.0"
    return s


def write_like_clean(dirty, clean):
    """Main protocol from 2 Oct (v2, replaces format_like_clean): write every injected
    non-blank value exactly in its clean column's number style (clean_style / write_value):
    fixed-decimal columns keep their width and real precision (frequency "3072.0"),
    significant-figure columns keep their significant digits (nasa thickness: 6, no trailing
    zeros), and a column that never ends in 0 gets no value ending in 0. format_like_clean
    (removed 3 Oct) rounded thickness to 9 decimals, which left 7-9 significant digits against at
    most 6 in the clean data."""
    for col in dirty.columns:
        st = clean_style(clean[col])
        changed = (dirty[col] != clean[col]) & (dirty[col] != '')
        dirty.loc[changed, col] = [write_value(float(v), st) for v in dirty.loc[changed, col]]
    return dirty


def inject(entry, rate, degree, seed, outliers_only=False, cleanstyle=False):
    """Error-rate mode of run_robustness_exp: outliers + explicit MV at `rate`,
    outlier degree `degree`. Seeded, so the dirty version depends only on
    (seed, rate, degree); `cleanstyle` applies write_like_clean afterwards.
    The seed does not depend on the degree (2 Oct): every degree hits the same cells with
    the same standard-normal draws, only scaled by degree * sigma, so degrees compare
    pairwise. The constant 3 keeps the seeds, and so the dirty files, of the 30 Sep
    degree-3 runs."""
    level_seed = seed * 100000 + int(round(rate * 1000)) * 100 + 3
    np.random.seed(level_seed)
    random.seed(level_seed)
    data_object = Datasets(entry)
    # outlier-degree mode injects outliers only, as run_robustness_exp does
    types = [outliers] if outliers_only else [outliers, [ErrorType.explicit_mv.func]]
    data_object.inject_errors(types, [rate, degree], muted_columns(entry), False)
    # inject_errors appends the muted columns at the end; restore the clean
    # column order so position-based comparisons (Raha) line up
    clean = pd.read_csv(entry['groundTruth_path'], dtype=str, keep_default_na=False)
    clean_cols = list(clean.columns)
    dirty = pd.read_csv(entry['dirty_path'], dtype=str, keep_default_na=False)
    if list(dirty.columns) != clean_cols or cleanstyle:
        dirty = dirty[clean_cols]
        if cleanstyle:
            dirty = write_like_clean(dirty, clean)
        dirty.to_csv(entry['dirty_path'], index=False)
    with open(entry['dirty_path'], 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def drop_tables(db, scratch):
    for tbl in ('dirty_' + scratch, 'ground_truth_' + scratch):
        try:
            if db.db_table_exists_postgresql(tbl):
                db.remove_table_postgres(tbl)
        except Exception:  # noqa: BLE001
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--error_rate', type=float, default=0.3,
                    help='nominal rate, e.g. 0.05 (REIN fixes 0.3 in the outlier-degree mode)')
    ap.add_argument('--outlier_degree', type=float, default=3, help='code default of run_robustness_exp')
    ap.add_argument('--detector', choices=['greatExpectations', 'holoclean', 'raha'], required=True)
    ap.add_argument('--tier', default=os.environ.get('EXPECTATION_TIER', 'hand_written'))
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--inject_only', action='store_true', help='generate the dirty version, report, clean up')
    ap.add_argument('--write_like_clean', action='store_true',
                    help='main protocol (v2, 2 Oct): injected values in the clean number style (mode *_cleanstyle)')
    ap.add_argument('--outlier_degree_mode', action='store_true',
                    help='knob 2: outliers only at --error_rate, level = --outlier_degree')
    ap.add_argument('--out', required=True,
                    help='CSV the result row is appended to (created with a header if missing)')
    args = ap.parse_args()
    variant = 'c' if args.write_like_clean else ''
    base_mode = 'outlier_degree' if args.outlier_degree_mode else 'error_rate'
    mode = base_mode + ('_cleanstyle' if variant else '')

    if args.detector == 'greatExpectations':
        os.environ['EXPECTATION_TIER'] = args.tier
    tier = args.tier if args.detector == 'greatExpectations' else ''

    pct = int(round(args.error_rate * 100))
    # detector and tier are part of the scratch name so that two runners never
    # share a scratch directory (same rule as scalability_driver.py)
    # a degree other than the code default 3 gets a _d<degree> suffix, so its kept run
    # folder never overwrites a degree-3 one
    conf = args.detector + ('_' + tier if tier else '')
    if args.outlier_degree_mode:
        # knob 2: nasa_o<degree>[r|f]_<configuration> (the rate is fixed)
        scratch = '{}_o{:g}{}_{}'.format(args.dataset, args.outlier_degree, variant, conf)
    else:
        deg = '' if args.outlier_degree == 3 else '_d{:g}'.format(args.outlier_degree)
        scratch = '{}_e{}{}{}_{}'.format(args.dataset, pct, variant, deg, conf)
    src_dir = datasets_dictionary[args.dataset]['dataset_path']
    dst_dir = os.path.join(datasets_path, scratch)
    row = dict(dataset=args.dataset, mode=mode,
               level=args.outlier_degree if args.outlier_degree_mode else args.error_rate,
               outlier_degree=args.outlier_degree, detector=args.detector, tier=tier,
               seed=args.seed, scratch=scratch, timestamp=time.strftime('%Y-%m-%dT%H:%M:%S'))
    db = Database()
    t0 = time.time()
    try:
        if os.path.exists(dst_dir):
            shutil.rmtree(dst_dir)
        drop_tables(db, scratch)
        os.makedirs(dst_dir)
        shutil.copy2(os.path.join(src_dir, 'clean.csv'), os.path.join(dst_dir, 'clean.csv'))
        # HoloClean reads datasets/<name>/constraints/_all_constraints.txt (the base
        # dataset's FDX-derived DCs are reused unchanged)
        cdir = os.path.join(src_dir, 'constraints')
        if os.path.isdir(cdir):
            shutil.copytree(cdir, os.path.join(dst_dir, 'constraints'))
        entry = register(args.dataset, scratch, dst_dir)
        row['dirty_sha256'] = inject(entry, args.error_rate, args.outlier_degree, args.seed,
                                     outliers_only=args.outlier_degree_mode,
                                     cleanstyle=args.write_like_clean)
        shape = pd.read_csv(entry['dirty_path'], dtype=str).shape
        row['rows'], row['cols'] = shape

        if args.inject_only:
            dirty = pd.read_csv(entry['dirty_path'], dtype=str, keep_default_na=False)
            clean = pd.read_csv(entry['groundTruth_path'], dtype=str, keep_default_na=False)
            ds = Datasets(entry)
            _, rate = ds.get_actual_errors(dirty, clean)
            row.update(status='inject_only', measured_error_rate=rate)
        else:
            from rein.benchmark import Benchmark  # imports datawig etc.; keep after the cheap steps
            app = Benchmark(False, log_label='robustness-{}-{}-{}'.format(scratch, args.detector, tier or 'x'))
            app.run_detectors(pct, [scratch], [DetectMethod(args.detector)], iterations=1)

            with open(os.path.join(dst_dir, 'error_rate.json')) as f:
                er = json.load(f)
            row['measured_error_rate'] = er if not isinstance(er, dict) else er.get('error_rate', er)
            res = pd.read_csv(os.path.join(dst_dir, 'results', 'detection_results.csv')).iloc[-1]
            row.update(status='ok', precision=res['precision'], recall=res['recall'], f1=res['f1'],
                       cell_TP=res['cell_TP'], cell_FP=res['cell_FP'], cell_FN=res['cell_FN'],
                       cell_FG1=res.get('cell_FG1', ''), detections=res['#detections'],
                       runtime_s=res['detection_runtime'])
    except Exception as e:  # noqa: BLE001
        row.update(status='error: {}'.format(type(e).__name__))
        print('robustness_driver failed: {!r}'.format(e), file=sys.stderr)
    finally:
        row['wall_s'] = round(time.time() - t0, 1)
        append_row(args.out, row)
        # keep the generated dirty version, its actual errors and the detections,
        # so the mechanism (missing values vs outliers caught) can be analysed later
        if not args.inject_only and os.path.isdir(dst_dir):
            keep_dir = os.path.join(os.path.dirname(args.out), 'runs', scratch)
            os.makedirs(keep_dir, exist_ok=True)
            for name in ('dirty.csv', 'actual_errors.csv', 'error_rate.json'):
                if os.path.exists(os.path.join(dst_dir, name)):
                    shutil.copy2(os.path.join(dst_dir, name), keep_dir)
            for root, _, files in os.walk(dst_dir):
                if 'detections.csv' in files:
                    shutil.copy2(os.path.join(root, 'detections.csv'), keep_dir)
        shutil.rmtree(dst_dir, ignore_errors=True)
        drop_tables(db, scratch)
    print('done', scratch, row.get('status'), 'rate=', row.get('measured_error_rate'),
          'f1=', row.get('f1'), 'sha=', str(row.get('dirty_sha256'))[:12])
    sys.exit(0 if row.get('status') in ('ok', 'inject_only') else 1)


if __name__ == '__main__':
    main()
