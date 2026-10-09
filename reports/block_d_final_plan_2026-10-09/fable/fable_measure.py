"""Independent re-measurement for the Fable review of the Block D final plan v2 (9 Oct 2026).

Run:  docker exec -w /rein rein-benchmark-rein-1 python3 reports/block_d_final_plan_2026-10-09/fable/fable_measure.py
Read-only on /rein/datasets; writes only fable_measure.json next to this file.

Own implementations throughout (no code reused from checks/measure_fixes.py):
  GE tiers      : real great_expectations PandasDataset when importable (as rein/detectors.py does),
                  plus an own pandas evaluation; both compared with each other and with Table 3 / disk.
  HoloClean     : own pairwise DC-violation implementation (dict of EQ-key -> rows / IQ values).
  Raha          : detections.csv on disk (run 1 is not on disk; same caveat as the plan).
  perfect / always_positive as in the plan.
"""
import importlib.util
import json
import math
import re
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

warnings.filterwarnings('ignore')
sys.dont_write_bytecode = True
D = '/rein/datasets'
OUT = '/rein/reports/block_d_final_plan_2026-10-09/fable'

CFG = {
    'breast_cancer': dict(label='class', excl=['Unnamed: 0', 'Sample code number'], task='clf', pos='4'),
    'nasa': dict(label='sound_pressure_level', excl=[], task='reg'),
    'bike': dict(label='cnt', excl=['instant', 'dteday', 'casual', 'registered'], task='reg'),
    'adult': dict(label='income', excl=[], task='clf', pos='0'),
}
# results/runs_log.csv (Table 3): TP, FP, det, F1 as published
T3 = {
    'breast_cancer': dict(ge_dirty_profiled=(247, 13, 260, 0.5544), ge_clean_profiled=(278, 13, 291, 0.603), ge_hand_written=(438, 22, 460, 0.8029), holoclean=(416, 5275, 5691, 0.1316), raha=(317, 78, 395, 0.6179)),
    'nasa': dict(ge_dirty_profiled=(30, 0, 30, 0.0788), ge_clean_profiled=(384, 0, 384, 0.6888), ge_hand_written=(680, 0, 680, 0.9639), holoclean=(556, 5709, 6265, 0.1589), raha=(710, 1864, 2574, 0.4297)),
    'bike': dict(ge_dirty_profiled=(0, 0, 0, 0.0), ge_clean_profiled=(0, 0, 0, 0.0), ge_hand_written=(24247, 0, 24247, 0.8287), holoclean=(25134, 173845, 198979, 0.2155), raha=(30861, 15138, 45999, 0.7689)),
    'adult': dict(ge_dirty_profiled=(0, 0, 0, 0.0), ge_clean_profiled=(0, 0, 0, 0.0), ge_hand_written=(0, 0, 0, 0.0), holoclean=(1677, 663530, 665207, 0.005), raha=(865, 5081, 5946, 0.2262)),
}
CONFIGS = ['ge_dirty_profiled', 'ge_clean_profiled', 'ge_hand_written', 'holoclean', 'raha']


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


prof = load_module('prof_f', '/rein/rein/auxiliaries/expectations_profiler.py')
HW = load_module('hw_f', '/rein/rein/auxiliaries/expectations_dictionary_local.py').DATASET_EXPECTATIONS

try:
    from great_expectations.dataset import PandasDataset
    HAVE_GE = True
except Exception as e:  # noqa
    PandasDataset = None
    HAVE_GE = False
    print('great_expectations not importable:', e)


def load(ds):
    # exactly how rein/datasets.py:load_data reads the files (dtype=str, keep_default_na=False)
    rd = lambda f: pd.read_csv('{}/{}/{}.csv'.format(D, ds, f), dtype=str, header='infer', encoding='utf-8', keep_default_na=False, low_memory=False)
    return rd('clean'), rd('dirty')


def read_cells(path):
    cells = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            a, b = line.split(',')[:2]
            cells.add((int(a), int(b)))
    return cells


def ge_real(df, exps):
    """Replay with the real GE library the way rein/detectors.py:greatExpectations does."""
    pdset = PandasDataset(df)
    det = set()
    for e in exps:
        col = e['column']
        if col not in df.columns:
            continue
        j = df.columns.get_loc(col)
        res = getattr(pdset, e['expectation'])(col, **e['kwargs'], result_format='COMPLETE')
        det |= {(int(i), j) for i in res.result['unexpected_index_list']}
    return det


def ge_own(df, exps):
    """Own evaluation of the four expectation kinds on string cells ('' for blanks)."""
    det = set()
    for e in exps:
        col = e['column']
        if col not in df.columns:
            continue
        j = df.columns.get_loc(col)
        vals = df[col].tolist()
        k, kw = e['expectation'], e['kwargs']
        if k == 'expect_column_values_to_match_regex':
            rx = re.compile(kw['regex'])
            bad = [i for i, v in enumerate(vals) if rx.search(v) is None]
        elif k == 'expect_column_values_to_not_match_regex':
            rx = re.compile(kw['regex'])
            bad = [i for i, v in enumerate(vals) if rx.search(v) is not None]
        elif k == 'expect_column_values_to_be_in_set':
            s = set(kw['value_set'])
            bad = [i for i, v in enumerate(vals) if v not in s]
        elif k == 'expect_column_values_to_not_be_in_set':
            s = set(kw['value_set'])
            bad = [i for i, v in enumerate(vals) if v in s]
        elif k == 'expect_column_values_to_be_unique':
            from collections import Counter
            c = Counter(vals)
            bad = [i for i, v in enumerate(vals) if c[v] > 1]
        else:
            raise ValueError(k)
        det |= {(i, j) for i in bad}
    return det


PRED = re.compile(r'(EQ|IQ)\(t1\.([^,]+),t2\.([^)]+)\)')


def holo_own(df, ds):
    """Own DC violation replay: a row violates t1&t2&EQ(A..)&IQ(B) iff another row shares all EQ values
    and differs in B. Every row of such a group gets all DC attributes flagged (both tuples of a pair)."""
    det = set()
    cols = list(df.columns)
    per_dc = []
    for line in open('{}/{}/constraints/{}_dcs.txt'.format(D, ds, ds)):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        eq, iq = [], []
        for op, a, b in PRED.findall(line):
            assert a == b, line
            (eq if op == 'EQ' else iq).append(a)
        assert len(iq) == 1, line
        key_cols = [cols.index(c) for c in eq]
        iq_col = cols.index(iq[0])
        groups = {}
        arr = df.values
        for r in range(len(df)):
            key = tuple(arr[r, c] for c in key_cols)
            g = groups.setdefault(key, ([], set()))
            g[0].append(r)
            g[1].add(arr[r, iq_col])
        dc_cells = set()
        for rows, iqvals in groups.values():
            if len(iqvals) > 1:
                for r in rows:
                    for c in key_cols + [iq_col]:
                        dc_cells.add((r, c))
        per_dc.append((line, len(dc_cells)))
        det |= dc_cells
    return det, per_dc


def isnum(v):
    if v == '':
        return False
    try:
        return math.isfinite(float(v))
    except ValueError:
        return False


def fnum(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except ValueError:
        return None


def f1(det, truth):
    tp = len(det & truth)
    if tp == 0:
        return 0.0
    p, r = tp / len(det), tp / len(truth)
    return 2 * p * r / (p + r)


def prec_rec(det, truth):
    tp = len(det & truth)
    return (tp / len(det) if det else 0.0, tp / len(truth) if truth else 0.0)


def order(scores):
    return ' > '.join('%s(%.4f)' % (k, v) for k, v in sorted(scores.items(), key=lambda kv: -kv[1]))


def featurize_train(dirty_vals, tr, numeric_cols, flagged=None, label_flag_rows=None):
    """dirty_vals: 2-D object array (strings) of the model FEATURE columns in dataset column order.
    tr: sorted training row ids. numeric_cols: boolean per feature column.
    flagged: set of (row, feature_idx) to impute (None = floor).
    Returns (kept rows, float matrix) with the plan's rules: impute flagged numeric cells with the
    mean of unflagged parsable cells of the kept training rows, then coerce + fill NaN with the
    training mean of the resulting column. Categorical columns are not needed here (bc/nasa all numeric)."""
    rows = [r for r in tr if not (label_flag_rows and r in label_flag_rows)]
    X = np.full((len(rows), dirty_vals.shape[1]), np.nan)
    pos = {r: i for i, r in enumerate(rows)}
    for j in range(dirty_vals.shape[1]):
        assert numeric_cols[j]
        col = [fnum(dirty_vals[r, j]) for r in rows]
        col = np.array([np.nan if v is None else v for v in col])
        if flagged is not None:
            fl_idx = [pos[r] for (r, jj) in flagged if jj == j and r in pos]
            if fl_idx:
                mask = np.ones(len(rows), bool)
                mask[fl_idx] = False
                good = col[mask]
                good = good[~np.isnan(good)]
                fill = good.mean() if len(good) else 0.0
                col[fl_idx] = fill
        m = np.nanmean(col) if np.isfinite(np.nanmean(col)) else 0.0
        col[np.isnan(col)] = m
        X[:, j] = col
    return rows, X


report = {}
for ds, cfg in CFG.items():
    clean, dirty = load(ds)
    assert list(clean.columns) == list(dirty.columns) and clean.shape == dirty.shape
    cols = list(dirty.columns)
    n, d = dirty.shape
    A = read_cells('{}/{}/actual_errors.csv'.format(D, ds))
    lab = cols.index(cfg['label'])
    excl = {cols.index(c) for c in cfg['excl']}
    model_cols = set(range(d)) - excl
    feat_cols = model_cols - {lab}
    rep = dict(n=n, d=d, errors=len(A), configs={}, per_column_errors={cols[j]: sum(1 for (_, jj) in A if jj == j) for j in range(d)})
    print('\n' + '=' * 110 + '\n%s  %d x %d, %d errors; label=%s excl=%s' % (ds, n, d, len(A), cfg['label'], cfg['excl']))
    # sanity: every actual error really differs from clean as a string
    rep['errors_with_dirty_eq_clean'] = sum(1 for (i, j) in A if dirty.iat[i, j] == clean.iat[i, j])
    # cells that differ as strings but are not errors (formatting differences), parsed equal or not
    diff_not_err = [(i, j) for j in range(d) for i in range(n) if dirty.iat[i, j] != clean.iat[i, j] and (i, j) not in A]
    rep['diff_not_error_cells'] = len(diff_not_err)
    rep['diff_not_error_parsed_equal'] = sum(1 for (i, j) in diff_not_err if fnum(dirty.iat[i, j]) is not None and fnum(dirty.iat[i, j]) == fnum(clean.iat[i, j]))
    rep['diff_not_error_by_col'] = {cols[j]: sum(1 for (_, jj) in diff_not_err if jj == j) for j in range(d) if any(jj == j for (_, jj) in diff_not_err)}

    # ---- flag sets
    F = {}
    e_dirty, e_clean, e_hw = prof.profile_expectations(dirty), prof.profile_expectations(clean), HW.get(ds, {}).get('hand_written', [])
    own = {'ge_dirty_profiled': ge_own(dirty, e_dirty), 'ge_clean_profiled': ge_own(dirty, e_clean), 'ge_hand_written': ge_own(dirty, e_hw)}
    if HAVE_GE:
        real = {'ge_dirty_profiled': ge_real(dirty, e_dirty), 'ge_clean_profiled': ge_real(dirty, e_clean), 'ge_hand_written': ge_real(dirty, e_hw)}
        rep['ge_real_vs_own_identical'] = {k: real[k] == own[k] for k in own}
        F.update(real)
    else:
        F.update(own)
    F['holoclean'], per_dc = holo_own(dirty, ds)
    rep['holoclean_per_dc_cells'] = per_dc
    F['raha'] = read_cells('{}/{}/raha/detections.csv'.format(D, ds))
    F['perfect'] = set(A)
    F['always_positive'] = {(r, c) for r in range(n) for c in range(d)}
    # disk comparisons
    disk = {}
    try:
        disk['ge_hand_written'] = read_cells('{}/{}/greatExpectations/detections.csv'.format(D, ds))
    except Exception:
        disk['ge_hand_written'] = set()
    disk['holoclean'] = read_cells('{}/{}/holoclean/detections.csv'.format(D, ds))
    rep['disk'] = {k: dict(cells=len(v), identical_to_replay=(v == F[k])) for k, v in disk.items()}
    for c in CONFIGS:
        tp = len(F[c] & A)
        got = (tp, len(F[c]) - tp, len(F[c]))
        ok = got == T3[ds][c][:3]
        print('  %-18s replay TP/FP/det %-24s Table 3 %-24s %s' % (c, got, T3[ds][c][:3], 'OK' if ok else 'DIFFERS'))
        rep['configs'][c] = dict(tp_fp_det=got, table3=T3[ds][c][:3], matches_table3=ok)
    if HAVE_GE:
        print('  GE real library == own evaluation:', rep['ge_real_vs_own_identical'])
    print('  disk files:', rep['disk'])

    # ---- per configuration counts
    for c, fl in F.items():
        m = rep['configs'].setdefault(c, {})
        fp = fl - A
        fl_model = {x for x in fl if x[1] in model_cols}
        m['flags'] = len(fl)
        m['flags_model_cols'] = len(fl_model)
        m['excl_col_flags'] = len(fl) - len(fl_model)
        m['excl_col_fp_by_col'] = {cols[j]: sum(1 for (i, jj) in fp if jj == j) for j in excl}
        m['fp_by_col'] = {cols[j]: v for j in range(d) for v in [sum(1 for (i, jj) in fp if jj == j)] if v}
        fmt = [(i, j) for (i, j) in fp if dirty.iat[i, j] != clean.iat[i, j]]
        m['format_only_fp'] = len(fmt)
        m['format_only_fp_parsed_equal'] = sum(1 for (i, j) in fmt if fnum(dirty.iat[i, j]) is not None and fnum(dirty.iat[i, j]) == fnum(clean.iat[i, j]))
        m['format_only_fp_by_col'] = {cols[j]: v for j in range(d) for v in [sum(1 for (i, jj) in fmt if jj == j)] if v}
        m['label_flags'] = sum(1 for (i, j) in fl if j == lab)
        m['label_tp'] = sum(1 for (i, j) in fl & A if j == lab)
        ftp = [(i, j) for (i, j) in fl & A if j in feat_cols]
        m['feature_tp'] = len(ftp)
        m['feature_tp_parsable'] = sum(1 for (i, j) in ftp if isnum(dirty.iat[i, j]))
        ffp = [(i, j) for (i, j) in fp if j in feat_cols]
        m['feature_fp'] = len(ffp)
        m['feature_fp_parsable'] = sum(1 for (i, j) in ffp if isnum(dirty.iat[i, j]))
        m['feature_fp_unparsable_values'] = sorted({dirty.iat[i, j] for (i, j) in ffp if not isnum(dirty.iat[i, j])})[:10]
        m['rows_touched_all'] = len({i for i, _ in fl})
        m['rows_touched_model'] = len({i for i, _ in fl_model})
        fmt_set = set(fmt)
        m['rows_touched_model_without_format_only'] = len({i for (i, j) in fl_model if (i, j) not in fmt_set})
    fe = [(i, j) for (i, j) in A if j in feat_cols]
    rep['feature_errors'] = len(fe)
    rep['feature_errors_unparsable'] = sum(1 for (i, j) in fe if not isnum(dirty.iat[i, j]))
    rep['label_errors'] = sum(1 for (i, j) in A if j == lab)
    rep['excl_col_errors'] = {cols[j]: sum(1 for (i, jj) in A if jj == j) for j in excl}
    # identical restricted sets
    keyed = {}
    for c in CONFIGS:
        keyed.setdefault(frozenset(x for x in F[c] if x[1] in model_cols), []).append(c)
    rep['identical_model_col_sets'] = [v for v in keyed.values() if len(v) > 1]
    # numeric-column rule on clean (>= 90 % parse)
    numeric = {j: (sum(isnum(v) for v in clean.iloc[:, j]) / n >= 0.9) for j in range(d)}
    rep['categorical_model_cols'] = [cols[j] for j in sorted(model_cols) if not numeric[j]]
    rep['clean_unparsable_by_col'] = {cols[j]: v for j in range(d) for v in [sum(not isnum(x) for x in clean.iloc[:, j])] if v}

    # ---- references
    A_model = {x for x in A if x[1] in model_cols}
    A_mv = {(i, j) for (i, j) in A_model if fnum(dirty.iat[i, j]) is None or fnum(clean.iat[i, j]) is None or fnum(dirty.iat[i, j]) != fnum(clean.iat[i, j])}
    rowsA_all = {i for i, _ in A}
    rowsA_model = {i for i, _ in A_model}
    refs = {k: {} for k in ['a_cell_all', 'a_published', 'b_row_all', 'b_row_model', 'c_model_visible', 'cell_model', 'recall_model', 'recall_all', 'cell_precision_model', 'row_precision_all', 'row_precision_model', 'parsable_feature_recall', 'rows_kept_model']}
    for c in CONFIGS:
        fl = F[c]
        fm = {x for x in fl if x[1] in model_cols}
        refs['a_cell_all'][c] = f1(fl, A)
        refs['a_published'][c] = T3[ds][c][3]
        refs['b_row_all'][c] = f1({i for i, _ in fl}, rowsA_all)
        refs['b_row_model'][c] = f1({i for i, _ in fm}, rowsA_model)
        refs['c_model_visible'][c] = f1(fm, A_mv)
        refs['cell_model'][c] = f1(fm, A_model)
        refs['recall_model'][c] = prec_rec(fm, A_model)[1]
        refs['recall_all'][c] = prec_rec(fl, A)[1]
        refs['cell_precision_model'][c] = prec_rec(fm, A_model)[0]
        refs['row_precision_all'][c] = prec_rec({i for i, _ in fl}, rowsA_all)[0]
        refs['row_precision_model'][c] = prec_rec({i for i, _ in fm}, rowsA_model)[0]
        pf = {(i, j) for (i, j) in A_model if j != lab and isnum(dirty.iat[i, j])}
        refs['parsable_feature_recall'][c] = len(fm & pf) / len(pf) if pf else 0.0
        refs['rows_kept_model'][c] = n - len({i for i, _ in fm})
    rep['references'] = refs
    rep['A_model_visible'] = len(A_mv)
    print('  feature errors %d (unparsable %d) | label errors %d | excluded-col errors %s | model-visible truth %d of %d model-col errors' % (
        rep['feature_errors'], rep['feature_errors_unparsable'], rep['label_errors'], rep['excl_col_errors'], len(A_mv), len(A_model)))
    print('  diff-but-not-error cells %d (parsed equal %d) by col %s' % (rep['diff_not_error_cells'], rep['diff_not_error_parsed_equal'], rep['diff_not_error_by_col']))
    print('  identical model-column flag sets:', rep['identical_model_col_sets'], '| categorical model cols:', rep['categorical_model_cols'])
    for k, v in refs.items():
        print('  ref %-24s %s' % (k, order(v)))

    # ---- per seed
    y = clean[cfg['label']].values
    yb = (y == cfg['pos']).astype(int) if cfg['task'] == 'clf' else None
    per = {}
    for seed in range(10):
        tr, te = train_test_split(np.arange(n), test_size=0.2, random_state=seed, stratify=yb)
        trs = set(int(x) for x in tr)
        for c, fl in F.items():
            r_all = {i for i, _ in fl} & trs
            r_mod = {i for i, j in fl if j in model_cols} & trs
            r_lab = {i for i, j in fl if j == lab} & trs
            kept = dict(delete_all=trs - r_all, delete_model=trs - r_mod, impute=trs - r_lab)
            p = per.setdefault(c, {})
            for k, rows in kept.items():
                p.setdefault(k, []).append(len(rows))
                if cfg['task'] == 'clf':
                    cls = [int(yb[i]) for i in rows]
                    p.setdefault(k + '_minority', []).append(sum(cls))
                    deg = len(rows) < 50 or len(set(cls)) < 2
                else:
                    deg = len(rows) < 50
                p.setdefault(k + '_degenerate', []).append(bool(deg))
            p.setdefault('label_errors_left_impute', []).append(sum(1 for (i, j) in A if j == lab and i in kept['impute'] and (i, j) not in fl))
            p.setdefault('label_errors_left_delete', []).append(sum(1 for (i, j) in A if j == lab and i in kept['delete_model'] and (i, j) not in fl))
            p.setdefault('rows_with_model_error_in_train', []).append(len(rowsA_model & trs))
        # feature cells flagged among impute-kept rows (adult HoloClean)
        if ds == 'adult':
            fl = F['holoclean']
            kept_rows = trs - ({i for i, j in fl if j == lab} & trs)
            nflag = sum(1 for (i, j) in fl if j in feat_cols and i in kept_rows)
            per['holoclean'].setdefault('impute_kept_feature_cells_flagged_frac', []).append(nflag / (len(kept_rows) * len(feat_cols)))
    rep['n_train'] = len(tr)
    rep['per_seed'] = per
    print('  n_train', len(tr))
    print('  %-17s | %-13s %-13s %-13s | minority(impute) | degenerate' % ('config', 'del all-cols', 'del model', 'impute'))
    for c in F:
        p = per[c]
        rng = lambda k: '%d-%d' % (min(p[k]), max(p[k]))
        degs = [k for k in ('delete_all', 'delete_model', 'impute') if any(p[k + '_degenerate'])]
        mino = rng('impute_minority') if cfg['task'] == 'clf' else '-'
        print('  %-17s | %-13s %-13s %-13s | %-16s | %s' % (c, rng('delete_all'), rng('delete_model'), rng('impute'), mino, ','.join(degs) or '-'))
    for c in ('raha', 'holoclean', 'perfect'):
        print('  label errors left (impute, train) %-10s %s' % (c, '%d-%d' % (min(per[c]['label_errors_left_impute']), max(per[c]['label_errors_left_impute']))))
    if ds == 'adult':
        print('  adult holoclean: fraction of feature cells flagged among impute-kept rows: %.3f-%.3f' % (min(per['holoclean']['impute_kept_feature_cells_flagged_frac']), max(per['holoclean']['impute_kept_feature_cells_flagged_frac'])))

    # ---- '= floor' under impute: build the featurized training matrices (bc, nasa: all numeric)
    if ds in ('breast_cancer', 'nasa'):
        fidx = sorted(feat_cols)
        vals = dirty.values[:, fidx]
        numeric_cols = [numeric[j] for j in fidx]
        fmap = {j: k for k, j in enumerate(fidx)}
        floor_eq = {}
        for c in ('ge_dirty_profiled', 'ge_clean_profiled', 'ge_hand_written', 'raha', 'perfect'):
            fl = F[c]
            flagged = {(i, fmap[j]) for (i, j) in fl if j in feat_cols}
            lab_rows = {i for (i, j) in fl if j == lab}
            diffs, same_rows = [], []
            for seed in range(10):
                tr, _ = train_test_split(np.arange(n), test_size=0.2, random_state=seed, stratify=yb)
                tr = sorted(int(x) for x in tr)
                r0, X0 = featurize_train(vals, tr, numeric_cols)
                r1, X1 = featurize_train(vals, tr, numeric_cols, flagged=flagged, label_flag_rows=lab_rows)
                same_rows.append(r0 == r1)
                diffs.append(int((X0 != X1).sum()) if r0 == r1 else -1)
            floor_eq[c] = dict(cells_differing_from_floor_per_seed=diffs, same_rows=all(same_rows))
            print('  impute vs floor  %-18s cells differing per seed %s' % (c, diffs))
        rep['impute_vs_floor'] = floor_eq
    report[ds] = rep

# ---- nasa thickness statistics (full column and training rows)
clean, dirty = load('nasa')
num = lambda s: pd.to_numeric(s, errors='coerce')
report['nasa_thickness'] = dict(dirty_mean=float(num(dirty.thickness).mean()), clean_mean=float(num(clean.thickness).mean()),
                                dirty_median=float(num(dirty.thickness).median()), clean_median=float(num(clean.thickness).median()),
                                dirty_max=float(num(dirty.thickness).max()), n_unparsable_dirty=int(num(dirty.thickness).isna().sum()))
print('\nnasa thickness: dirty mean %.4g clean mean %.4g | medians %.4g / %.4g | dirty max %.4g | unparsable %d' % tuple(report['nasa_thickness'].values()))

# ---- REIN dropna counts (models.py:431-433 read the version with pandas defaults, then dropna)
for ds in ('breast_cancer', 'nasa', 'bike', 'adult'):
    df = pd.read_csv('{}/{}/dirty.csv'.format(D, ds), low_memory=False)
    report.setdefault('rein_dropna_rows_kept', {})[ds] = int(len(df.dropna()))
print('REIN dropna rows kept:', report['rein_dropna_rows_kept'])

# ---- adult clean label counts
cl = pd.read_csv(D + '/adult/clean.csv', dtype=str, keep_default_na=False)
report['adult_income_counts'] = cl['income'].value_counts().to_dict()
print('adult clean income counts:', report['adult_income_counts'])

json.dump(report, open(OUT + '/fable_measure.json', 'w'), indent=1, default=lambda o: int(o) if isinstance(o, (np.integer,)) else (bool(o) if isinstance(o, np.bool_) else str(o)))
print('\nwritten', OUT + '/fable_measure.json')
