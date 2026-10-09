"""Measure every fix of the 9 Oct Block D review on the real flag sets.

Run inside the rein container (pandas 1.3.3, sklearn 0.24.2, scipy 1.7.1), read-only on
/rein/datasets; writes only into this folder:
    docker exec rein-benchmark-rein-1 python3 reports/block_d_final_plan_2026-10-09/checks/measure_fixes.py

Flag sets used:
  GE dirty/clean-profiled  replayed (real profiler, legacy GE semantics; reproduces Table 3)
  GE hand-written          replayed from expectations_dictionary_local.py (checked against the file on disk)
  HoloClean                replayed from <ds>_dcs.txt (checked against the file on disk; adult's disk file is stale)
  Raha                     the detections.csv on disk (NOT run 1: bc 407/395, nasa 2595/2574, bike 46001/45999,
                           adult 5514/5946) -> Raha numbers are close approximations until step 2 regenerates run 1
  perfect                  actual_errors.csv;  always_positive: every cell
"""
import importlib.util
import itertools
import json
import math
import re
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from scipy.stats import wilcoxon

warnings.filterwarnings('ignore')
sys.dont_write_bytecode = True
R = '/rein'
D = R + '/datasets'
OUT = R + '/reports/block_d_final_plan_2026-10-09/checks'

CFG = {
    'breast_cancer': dict(label='class', excl=['Unnamed: 0', 'Sample code number'], task='clf', pos='4'),
    'nasa': dict(label='sound_pressure_level', excl=[], task='reg'),
    'bike': dict(label='cnt', excl=['instant', 'dteday', 'casual', 'registered'], task='reg'),
    'adult': dict(label='income', excl=[], task='clf', pos='0'),
}
TABLE3 = {  # TP/FP/detections, results/runs_log.csv (spec section 3)
    'breast_cancer': dict(ge_dirty_profiled=(247, 13, 260), ge_clean_profiled=(278, 13, 291), ge_hand_written=(438, 22, 460), holoclean=(416, 5275, 5691), raha=(317, 78, 395)),
    'nasa': dict(ge_dirty_profiled=(30, 0, 30), ge_clean_profiled=(384, 0, 384), ge_hand_written=(680, 0, 680), holoclean=(556, 5709, 6265), raha=(710, 1864, 2574)),
    'bike': dict(ge_dirty_profiled=(0, 0, 0), ge_clean_profiled=(0, 0, 0), ge_hand_written=(24247, 0, 24247), holoclean=(25134, 173845, 198979), raha=(30861, 15138, 45999)),
    'adult': dict(ge_dirty_profiled=(0, 0, 0), ge_clean_profiled=(0, 0, 0), ge_hand_written=(0, 0, 0), holoclean=(1677, 663530, 665207), raha=(865, 5081, 5946)),
}
CONFIGS = ['ge_dirty_profiled', 'ge_clean_profiled', 'ge_hand_written', 'holoclean', 'raha']


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


prof = load_module('prof', R + '/rein/auxiliaries/expectations_profiler.py')
hw = load_module('hw', R + '/rein/auxiliaries/expectations_dictionary_local.py').DATASET_EXPECTATIONS


def ge(df, exps):
    det = set()
    for e in exps:
        col = e['column']
        if col not in df.columns:
            continue
        j = df.columns.get_loc(col)
        s = df[col].astype(str)
        k, kw = e['expectation'], e['kwargs']
        if k == 'expect_column_values_to_match_regex':
            bad = ~s.str.contains(kw['regex'], regex=True)
        elif k == 'expect_column_values_to_not_match_regex':
            bad = s.str.contains(kw['regex'], regex=True)
        elif k == 'expect_column_values_to_be_in_set':
            bad = ~s.isin(kw['value_set'])
        elif k == 'expect_column_values_to_not_be_in_set':
            bad = s.isin(kw['value_set'])
        elif k == 'expect_column_values_to_be_unique':
            bad = s.duplicated(keep=False)
        else:
            raise ValueError(k)
        det |= {(i, j) for i in np.flatnonzero(bad.values)}
    return det


PRED = re.compile(r'(EQ|IQ)\(t1\.(.+?),t2\.(.+?)\)')


def holo(df, ds):
    det = set()
    for line in open('{}/{}/constraints/{}_dcs.txt'.format(D, ds, ds)):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        eq, iq = [], []
        for op, l, _ in PRED.findall(line):
            (eq if op == 'EQ' else iq).append(l)
        n = df.groupby(eq, sort=False)[iq[0]].transform('nunique')
        rows = np.flatnonzero((n > 1).values)
        cols = [df.columns.get_loc(c) for c in eq + iq]
        det |= {(r, c) for r in rows for c in cols}
    return det


def read_cells(path):
    try:
        f = pd.read_csv(path, header=None)
    except pd.errors.EmptyDataError:
        return set()
    return set(zip(f[0].astype(int), f[1].astype(int)))


def tp_fp(det, A):
    tp = len(det & A)
    return (tp, len(det) - tp, len(det))


def isnum(v):
    if v == '':
        return False
    try:
        x = float(v)
        return math.isfinite(x)
    except ValueError:
        return False


report = {}
for ds, cfg in CFG.items():
    clean = pd.read_csv('{}/{}/clean.csv'.format(D, ds), dtype=str, keep_default_na=False)
    dirty = pd.read_csv('{}/{}/dirty.csv'.format(D, ds), dtype=str, keep_default_na=False)
    assert list(clean.columns) == list(dirty.columns), ds
    A = read_cells('{}/{}/actual_errors.csv'.format(D, ds))
    n, d = dirty.shape
    cols = list(dirty.columns)
    lab = cols.index(cfg['label'])
    excl = {cols.index(c) for c in cfg['excl']}
    schema = set(range(d)) - excl                       # features + label
    feats = schema - {lab}

    # ---------- flag sets
    F = {}
    F['ge_dirty_profiled'] = ge(dirty, prof.profile_expectations(dirty))
    F['ge_clean_profiled'] = ge(dirty, prof.profile_expectations(clean))
    F['ge_hand_written'] = ge(dirty, hw.get(ds, {}).get('hand_written', []))
    F['holoclean'] = holo(dirty, ds)
    F['raha'] = read_cells('{}/{}/raha/detections.csv'.format(D, ds))
    F['perfect'] = set(A)
    F['always_positive'] = {(r, c) for r in range(n) for c in range(d)}
    disk = {'ge_hand_written': '{}/{}/greatExpectations/detections.csv', 'holoclean': '{}/{}/holoclean/detections.csv'}
    rep = dict(n=n, d=d, errors=len(A), configs={})
    print('\n' + '=' * 100 + '\n' + ds, n, 'x', d, 'errors', len(A))

    # ---------- check: replay vs Table 3 and vs disk
    for c in CONFIGS:
        got = tp_fp(F[c], A)
        print('  %-18s replay/disk TP/FP/det %-24s Table 3 %-24s %s' % (c, got, TABLE3[ds][c], 'OK' if got == TABLE3[ds][c] else 'DIFFERS'))
    for c, p in disk.items():
        if ds == 'adult' and c == 'ge_hand_written':
            continue
        on_disk = read_cells(p.format(D, ds))
        print('  %-18s replay == file on disk: %s (disk %d cells)' % (c, on_disk == F[c], len(on_disk)))

    # ---------- per configuration: excluded-column flags, format-only FPs, label flags, parsable TPs
    y = clean[cfg['label']]
    for c, fl in F.items():
        excl_flags = sum(1 for _, j in fl if j in excl)
        fp = fl - A
        fmt_only = sum(1 for (i, j) in fp if dirty.iat[i, j] != clean.iat[i, j])
        fmt_only_schema = sum(1 for (i, j) in fp if j in schema and dirty.iat[i, j] != clean.iat[i, j])
        label_flags = sum(1 for _, j in fl if j == lab)
        label_tp = sum(1 for (i, j) in fl & A if j == lab)
        feat_tp = [(i, j) for (i, j) in fl & A if j in feats]
        feat_tp_parsable = sum(1 for (i, j) in feat_tp if isnum(dirty.iat[i, j]))
        rows_all = {i for i, _ in fl}
        rows_schema = {i for i, j in fl if j in schema}
        rows_schema_nofmt = {i for i, j in fl if j in schema and not ((i, j) not in A and dirty.iat[i, j] != clean.iat[i, j])}
        rep['configs'][c] = dict(flags=len(fl), excl_col_flags=excl_flags, format_only_fp=fmt_only,
                                 format_only_fp_schema=fmt_only_schema, label_flags=label_flags, label_tp=label_tp,
                                 feature_tp=len(feat_tp), feature_tp_parsable=feat_tp_parsable,
                                 rows_touched_all=len(rows_all), rows_touched_schema=len(rows_schema),
                                 rows_touched_schema_without_format_only=len(rows_schema_nofmt))
    # feature errors: parsable vs not (featurization mean-fills unparsable cells in EVERY version, floor included)
    fe = [(i, j) for (i, j) in A if j in feats]
    rep['feature_errors'] = len(fe)
    rep['feature_errors_unparsable'] = sum(1 for (i, j) in fe if not isnum(dirty.iat[i, j]))
    rep['label_errors'] = sum(1 for (i, j) in A if j == lab)
    rep['excluded_col_errors'] = sum(1 for (i, j) in A if j in excl)

    # identical flag sets (fix 3)
    keyed = {}
    for c in CONFIGS:
        keyed.setdefault(frozenset((i, j) for i, j in F[c] if j in schema), []).append(c)
    rep['identical_flag_sets'] = [v for v in keyed.values() if len(v) > 1]

    # ---------- per seed: rows kept (fix 1, 6, 7)
    if cfg['task'] == 'clf':
        yb = (y == cfg['pos']).astype(int).values
    per = {}
    for seed in range(10):
        idx = np.arange(n)
        tr, _ = train_test_split(idx, test_size=0.2, random_state=seed, stratify=yb if cfg['task'] == 'clf' else None)
        trs = set(tr)
        for c, fl in F.items():
            rows_all = {i for i, _ in fl} & trs
            rows_sch = {i for i, j in fl if j in schema} & trs
            rows_lab = {i for i, j in fl if j == lab} & trs
            kept = {'delete_allcols': len(trs - rows_all), 'delete_schema': len(trs - rows_sch), 'impute': len(trs - rows_lab)}
            onecls = {}
            if cfg['task'] == 'clf':
                for k, rowset in (('delete_allcols', rows_all), ('delete_schema', rows_sch), ('impute', rows_lab)):
                    keep = np.array(sorted(trs - rowset), dtype=int)
                    onecls[k] = len(keep) == 0 or len(set(yb[keep])) < 2
            for k, v in kept.items():
                per.setdefault(c, {}).setdefault(k, []).append(v)
                deg = v < 50 or (cfg['task'] == 'clf' and onecls[k])
                per[c].setdefault(k + '_degenerate', []).append(bool(deg))
            per[c].setdefault('label_errors_left_impute', []).append(
                sum(1 for (i, j) in A if j == lab and i in trs and i not in rows_lab))
    rep['n_train'] = len(tr)
    rep['per_seed'] = per

    print('  n_train', len(tr), '| feature errors', rep['feature_errors'], 'unparsable', rep['feature_errors_unparsable'],
          '| label errors', rep['label_errors'], '| errors in excluded cols', rep['excluded_col_errors'])
    print('  identical flag sets (schema columns):', rep['identical_flag_sets'])
    print('  %-17s %8s %6s %7s %6s %6s %9s | %-13s %-13s %-13s | %s' % (
        'config', 'flags', 'excl', 'fmtFP', 'lblF', 'lblTP', 'featTP(p)', 'del all-cols', 'del schema', 'impute', 'degenerate'))
    for c in F:
        m, p = rep['configs'][c], per[c]
        rng = lambda k: '%d-%d' % (min(p[k]), max(p[k]))
        degs = [k for k in ('delete_allcols', 'delete_schema', 'impute') if any(p[k + '_degenerate'])]
        print('  %-17s %8d %6d %7d %6d %6d %4d(%4d) | %-13s %-13s %-13s | %s' % (
            c, m['flags'], m['excl_col_flags'], m['format_only_fp'], m['label_flags'], m['label_tp'], m['feature_tp'],
            m['feature_tp_parsable'], rng('delete_allcols'), rng('delete_schema'), rng('impute'), ','.join(degs) or '-'))
    report[ds] = rep

# ---------- fix 8: the training mean of nasa thickness, dirty vs clean
cl = pd.read_csv(D + '/nasa/clean.csv', dtype=str, keep_default_na=False)
di = pd.read_csv(D + '/nasa/dirty.csv', dtype=str, keep_default_na=False)
num = lambda s: pd.to_numeric(s, errors='coerce')
report['nasa_thickness'] = dict(dirty_mean=float(num(di.thickness).mean()), clean_mean=float(num(cl.thickness).mean()),
                                dirty_median=float(num(di.thickness).median()), clean_median=float(num(cl.thickness).median()))
print('\nnasa thickness  mean dirty %.4g  clean %.4g | median dirty %.4g  clean %.4g' % tuple(report['nasa_thickness'].values()))


# ---------- fix 5: SciPy 1.7.1 exact Wilcoxon vs an exact sign-flip test on midranks
def signflip_p(dd):
    dd = np.asarray([x for x in dd if x != 0], float)
    if len(dd) == 0:
        return 1.0
    r = pd.Series(np.abs(dd)).rank().values          # midranks for ties
    obs = abs(np.sum(np.sign(dd) * r))
    tot = 0
    for s in itertools.product((1, -1), repeat=len(dd)):
        tot += abs(np.dot(s, r)) >= obs - 1e-9
    return tot / 2 ** len(dd)


rng = np.random.default_rng(0)
found = []
for _ in range(20000):
    dd = rng.integers(-3, 6, size=10).astype(float)
    if (dd == 0).any() or len(set(np.abs(dd))) == 10:
        continue
    p1 = wilcoxon(dd, mode='exact').pvalue
    p2 = wilcoxon(-dd, mode='exact').pvalue
    if abs(p1 - p2) > 1e-9 and min(p1, p2) < 0.05 <= max(p1, p2):
        found.append(dict(d=dd.tolist(), p_d=p1, p_minus_d=p2, signflip=signflip_p(dd)))
        if len(found) == 3:
            break
report['wilcoxon_order_examples'] = found
print('\nSciPy exact Wilcoxon: verdict depends on pair order when |d| ties:')
for f in found:
    print('  d=%s  p(d)=%.4f  p(-d)=%.4f  exact sign-flip=%.4f' % (f['d'], f['p_d'], f['p_minus_d'], f['signflip']))

json.dump(report, open(OUT + '/measure_fixes.json', 'w'), indent=1, default=int)
print('\nwritten', OUT + '/measure_fixes.json')
