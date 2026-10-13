"""Block D step 3: the downstream driver (plan v2.1, reports/block_d_final_plan_2026-10-09.md).

Builds the training data of every version (frozen flag set x repair policy, floor, clean, random-deletion
controls), featurizes it, trains three models per version and scores scenarios S1-S4 on the splits.
Requirements: reports/block_d/driver_requirements_2026-10-13.md (R1-R113, cited as "Rn"). The version,
featurization, model and pair logic is copied from checks/decisions/mini_driver.py (tested for D2-D8),
not imported from the reports folder.

Inputs (read-only; copied into <out>/inputs/ first and read only from the copies):
    <data_root>/<ds>/{dirty,clean,actual_errors}.csv
    <flags_dir>/<ds>/{ge_dirty_profiled,ge_clean_profiled,ge_hand_written,holoclean,raha}.csv, <flags_dir>/MANIFEST.csv
Outputs in <out>, a new or empty folder under reports/block_d/runs/:
    results.csv (full runs), manifest.json, checks.txt, run.log, dryrun.txt (every mode), inputs/
Modes:
    full (default)  checks 1-4, then trains every version and writes results.csv
    --dry_run       no fitting; dryrun.txt holds only data-derived text, so two machines' files can be diffed
    --check         the dry run plus the training part of check 2 (perfect/always-positive + GT = S4)

Run in the rein container from /rein with the Block D thread settings:
    docker compose run --rm -T --no-deps --entrypoint python3 -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 \
        -e MKL_NUM_THREADS=1 -e PYTHONHASHSEED=0 -e REIN_IMAGE_ID=<image id> rein scripts/blockd_driver.py \
        --flags_dir reports/block_d/flags --datasets breast_cancer nasa [--fill median] [--dry_run|--check] \
        --out reports/block_d/runs/<date>_<tag>
    python3 scripts/blockd_driver.py --selftest      (synthetic tests of scripts/tests/test_blockd.py)
"""
import sys
sys.dont_write_bytecode = True
import argparse
import csv
import datetime
import hashlib
import importlib.util
import itertools
import json
import math
import multiprocessing
import os
import platform
import shutil
import socket
import subprocess
import time
import traceback
import warnings

import numpy as np
import pandas as pd

R = '/rein'
CHECKS = R + '/reports/block_d_final_plan_2026-10-09/checks'
MF_SRC = CHECKS + '/measure_fixes.py'
ns = {}
exec(compile(open(MF_SRC).read().split('report = {}')[0], MF_SRC, 'exec'), ns)   # replay helpers, CFG, Table 3 (R3)

from sklearn.model_selection import train_test_split                  # noqa: E402
from sklearn.linear_model import LogisticRegression, Ridge             # noqa: E402
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor   # noqa: E402
from sklearn.preprocessing import StandardScaler, OneHotEncoder        # noqa: E402
from sklearn.metrics import f1_score, precision_score, recall_score, mean_squared_error, r2_score   # noqa: E402
from sklearn.exceptions import ConvergenceWarning                      # noqa: E402
from xgboost import XGBClassifier, XGBRegressor                        # noqa: E402

# ---------------------------------------------------------------- constants (module-level dicts: the self-tests
# substitute a synthetic dataset by adding entries)
CFG = ns['CFG']
TABLE3 = ns['TABLE3']
CONFIGS = list(ns['CONFIGS'])
isnum, tp_fp = ns['isnum'], ns['tp_fp']
SHORT = dict(ge_dirty_profiled='GE-dirty', ge_clean_profiled='GE-clean', ge_hand_written='GE-hand',
             holoclean='HoloClean', raha='Raha')
DATASETS = ['breast_cancer', 'nasa', 'bike', 'adult']
POLICIES = ['gt', 'delete', 'impute']
MODELS = ['linear', 'rf', 'xgb']
EXTRA_SETS = ['perfect', 'always_positive']
D6_NAME = 'raha_minus_format_only'
D6 = {'nasa': (710, 0)}                                  # R35: expected TP / FP of the diagnostic version
PUBLISHED_F1 = {                                         # R87: Table 3 cell F1 as published (IP L26-31)
    'breast_cancer': dict(ge_dirty_profiled=.554, ge_clean_profiled=.603, ge_hand_written=.803, holoclean=.132, raha=.618),
    'nasa': dict(ge_dirty_profiled=.079, ge_clean_profiled=.689, ge_hand_written=.964, holoclean=.159, raha=.430),
    'bike': dict(ge_dirty_profiled=0., ge_clean_profiled=0., ge_hand_written=.829, holoclean=.216, raha=.769),
    'adult': dict(ge_dirty_profiled=0., ge_clean_profiled=0., ge_hand_written=0., holoclean=.005, raha=.226),
}
EXPECT = {   # R24, R25, R32, R34, R47: any other count aborts (width is printed only)
    'breast_cancer': dict(features=9, numeric=9, items=5, pairs=10, n_train=559, width=9),
    'nasa': dict(features=5, numeric=5, items=5, pairs=10, n_train=1202, width=5),
    'bike': dict(features=12, numeric=12, items=4, pairs=6, n_train=13903, width=12),
    'adult': dict(features=14, numeric=6, items=3, pairs=3, n_train=36177, width=104),
}
EXPECTED_DEGENERATE = {ds: {('holoclean', 'delete'), ('always_positive', 'delete'), ('always_positive', 'impute')}
                       for ds in DATASETS}                # R53 (Raha run 1), reported, not an abort
EXPECTED_DEGENERATE['breast_cancer'] |= {('holoclean', 'impute')}
EXPECTED_DEGENERATE['bike'] |= {('holoclean', 'impute')}
EXPECTED_DEGENERATE['nasa'] |= {('raha', 'delete')}
POOLED_SECTION9 = {'gt': (19, 10, 0), 'delete': (16, 4, 9), 'impute': (12, 1, 16)}   # plan §9 (read only)
MECH_SEEDS = range(10)                                   # mechanism (d) uses the MF degenerate rule over seeds 0-9

RUNS_ROOT = R + '/reports/block_d/runs'
FROZEN_VERDICTS = CHECKS + '/expected_pair_verdicts.csv'
ADDENDUM_VERDICTS = CHECKS + '/addendum_raha_run1/expected_pair_verdicts_raha_run1.csv'
ADDENDUM_MF = CHECKS + '/addendum_raha_run1/measure_fixes.json'
FROZEN_COMMIT = 'c61ee72'
HASHED_ONLY = ['rein/auxiliaries/expectations_profiler.py', 'rein/auxiliaries/expectations_dictionary_local.py',
               'reports/block_d_final_plan_2026-10-09/checks/measure_fixes.py',
               'reports/block_d_final_plan_2026-10-09/checks/expected_pair_verdicts.csv',
               'reports/block_d_final_plan_2026-10-09/checks/addendum_raha_run1/expected_pair_verdicts_raha_run1.csv',
               'reports/block_d_final_plan_2026-10-09/checks/addendum_raha_run1/measure_fixes.json']
THREAD_VARS = {'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'PYTHONHASHSEED': '0'}
RESULT_COLS = ['dataset', 'task', 'fill', 'version', 'item', 'configuration', 'policy', 'model', 'seed', 'scenario',
               'score', 'f1', 'rmse', 'r2', 'precision', 'recall', 'rows_kept', 'test_rows', 'cells_changed',
               'excl_col_flags', 'format_only_fp', 'rows_touched_without_format_only', 'parsable_tp', 'parsable_fp',
               'errors_left_in_features', 'label_errors_left', 'flagged_label_cells', 'degenerate', 'test_degenerate',
               'train_hash', 'fit_s', 'timestamp']
FLAG_COLS = ['excl_col_flags', 'format_only_fp', 'rows_touched_without_format_only', 'parsable_tp', 'parsable_fp',
             'flagged_label_cells']


class Abort(Exception):
    """A failed check or rule: the run stops, manifest status 'failed', exit code 1 (R6, R57)."""

    def __init__(self, check, msg):
        super().__init__(check, msg)
        self.check, self.msg = check, msg


# ---------------------------------------------------------------- reading and parsing (R17, R18, R26)
def read_table(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def read_cells_array(path):
    """Flag / error file without header -> int array (k, 2) of (row, col); a 0-byte file is the empty set."""
    try:
        f = pd.read_csv(path, header=None)
    except pd.errors.EmptyDataError:
        return np.zeros((0, 2), dtype=np.int64)
    return np.column_stack([f[0].astype(int).values, f[1].astype(int).values]).astype(np.int64)


def cell_set(arr):
    return set(zip(arr[:, 0].tolist(), arr[:, 1].tolist()))


def parse_values(texts):
    """float(text) where isnum(text) (MF L117-124), NaN otherwise."""
    texts = np.asarray(texts, dtype=object)
    if texts.size == 0:
        return np.zeros(texts.shape, dtype=float)
    u, inv = np.unique(texts, return_inverse=True)
    pu = np.array([float(v) if isnum(v) else np.nan for v in u], dtype=float)
    return pu[inv].reshape(texts.shape)


def close(a, b):
    """math.isclose(a, b, rel_tol=1e-6) elementwise (False where either is NaN)."""
    with np.errstate(invalid='ignore', over='ignore'):
        return np.abs(a - b) <= 1e-6 * np.maximum(np.abs(a), np.abs(b))


def same_value(a, b):
    """Value comparator of R65 for parsed values: both NaN, or both finite and close."""
    an, bn = np.isnan(a), np.isnan(b)
    return (an & bn) | (~an & ~bn & close(a, b))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------- dataset, schema and labels (R24-R27)
def load_data(ds, cfg, files):
    """Everything the versions need, as numpy arrays over the n x d table."""
    clean, dirty = read_table(files['clean']), read_table(files['dirty'])
    if list(clean.columns) != list(dirty.columns) or clean.shape != dirty.shape:
        raise Abort('check1', 'CHECK 1 FAIL {} clean.csv and dirty.csv differ in columns or shape'.format(ds))
    cols = list(dirty.columns)
    n, d = dirty.shape
    lab_j = cols.index(cfg['label'])
    excl_j = sorted(cols.index(c) for c in cfg['excl'])
    feat_j = [j for j in range(d) if j not in excl_j and j != lab_j]
    dirty_txt, clean_txt = dirty.values.astype(object), clean.values.astype(object)
    dirty_num = np.column_stack([parse_values(dirty_txt[:, j]) for j in range(d)])
    clean_num = np.column_stack([parse_values(clean_txt[:, j]) for j in range(d)])
    share = {j: float(np.mean(~np.isnan(clean_num[:, j]))) for j in feat_j}
    num_j = [j for j in feat_j if share[j] >= 0.9]           # D4: >= 90 % of the clean values parse
    cat_j = [j for j in feat_j if share[j] < 0.9]
    clf = cfg['task'] == 'clf'
    pos = neg = None
    if clf:                                                  # R27: one fixed encoder for every array
        classes = sorted(set(clean_txt[:, lab_j]))
        pos = cfg['pos']
        if len(classes) != 2 or pos not in classes:
            raise Abort('labels', 'LABEL FAIL {} clean classes {} (positive {!r})'.format(ds, classes, pos))
        neg = [c for c in classes if c != pos][0]
        enc = {pos: 1.0, neg: 0.0}
        y_clean = np.array([enc.get(v, np.nan) for v in clean_txt[:, lab_j]], dtype=float)
        y_dirty = np.array([enc.get(v, np.nan) for v in dirty_txt[:, lab_j]], dtype=float)
    else:
        y_clean, y_dirty = clean_num[:, lab_j].copy(), dirty_num[:, lab_j].copy()
    if np.isnan(y_clean).any():
        raise Abort('labels', 'LABEL FAIL {} {} clean labels do not parse'.format(ds, int(np.isnan(y_clean).sum())))
    err = read_cells_array(files['errors'])
    A, problems = cells_mask(n, d, err)
    if problems:
        raise Abort('check1', 'CHECK 1 FAIL {} actual_errors.csv: {}'.format(ds, '; '.join(problems)))
    col_model = np.zeros(d, bool)
    col_model[feat_j + [lab_j]] = True
    col_feat = np.zeros(d, bool)
    col_feat[feat_j] = True
    col_excl = np.zeros(d, bool)
    col_excl[excl_j] = True
    dn_nan, cn_nan = np.isnan(dirty_num), np.isnan(clean_num)
    A_mv = A & col_model[None, :] & (dn_nan | cn_nan | ~close(dirty_num, clean_num))   # RR L46-50, IP L51-56
    textdiff = dirty_txt != clean_txt
    return dict(ds=ds, cfg=cfg, cols=cols, n=n, d=d, lab_j=lab_j, excl_j=excl_j, feat_j=np.array(feat_j, int),
                num_j=np.array(num_j, int), cat_j=np.array(cat_j, int), clf=clf, pos=pos, neg=neg,
                dirty_txt=dirty_txt, clean_txt=clean_txt, dirty_num=dirty_num, clean_num=clean_num,
                y_clean=y_clean, y_dirty=y_dirty, A=A, A_mv=A_mv, err_cells=err,
                col_model=col_model, col_feat=col_feat, col_excl=col_excl, parsable=~dn_nan,
                fmt_cand=textdiff & ~A & col_model[None, :], splits={})


def cells_mask(n, d, cells):
    """n x d mask of a cell list, plus the problems of check 1b (R20)."""
    problems = []
    if len(cells):
        dup = len(cells) - len(np.unique(cells, axis=0))
        if dup:
            problems.append('{} duplicate cells'.format(dup))
        out = (cells[:, 0] < 0) | (cells[:, 0] >= n) | (cells[:, 1] < 0) | (cells[:, 1] >= d)
        if out.any():
            problems.append('{} cells outside the {} x {} table'.format(int(out.sum()), n, d))
            cells = cells[~out]
    m = np.zeros((n, d), bool)
    if len(cells):
        m[cells[:, 0], cells[:, 1]] = True
    return m, problems


def split(data, seed):
    """R47: shared by every version, stratified by the clean labels for classification, both sides sorted."""
    if seed not in data['splits']:
        tr, te = train_test_split(np.arange(data['n']), test_size=0.2, random_state=seed,
                                  stratify=data['y_clean'].astype(int) if data['clf'] else None)
        data['splits'][seed] = (np.sort(tr), np.sort(te))
    return data['splits'][seed]


# ---------------------------------------------------------------- flag sets, statistics, items (R33-R36)
def flag_masks(data, files):
    """Full (all-column) and restricted (model-column) masks of the 7 flag sets (+ the D6 version)."""
    n, d = data['n'], data['d']
    full = {}
    for c in CONFIGS:
        m, problems = cells_mask(n, d, read_cells_array(files[c]))
        if problems:
            raise Abort('check1', 'CHECK 1 FAIL {} {} {}'.format(data['ds'], c, '; '.join(problems)))
        full[c] = m
    full['perfect'] = data['A'].copy()
    full['always_positive'] = np.ones((n, d), bool)
    restricted = {k: m & data['col_model'][None, :] for k, m in full.items()}
    if data['ds'] in D6:
        restricted[D6_NAME] = restricted['raha'] & ~data['fmt_cand']
        full[D6_NAME] = restricted[D6_NAME].copy()
    return full, restricted


def flag_stats(data, full, rmask):
    """Whole-dataset properties of one flag set (R65, A2), plus the MF quantities R62 compares."""
    A, lab_j = data['A'], data['lab_j']
    fmt = rmask & data['fmt_cand']
    fi, fj = np.nonzero(fmt)
    dv, cv = data['dirty_num'][fi, fj], data['clean_num'][fi, fj]
    feat_flags = rmask & data['col_feat'][None, :] & data['parsable']
    return dict(detections=int(full.sum()), tp=int((full & A).sum()), fp=int((full & ~A).sum()),
                model_flags=int(rmask.sum()), excl_col_flags=int((full & data['col_excl'][None, :]).sum()),
                format_only_fp=int(fmt.sum()),
                format_only_not_equal=int((np.isnan(dv) | np.isnan(cv) | ~close(dv, cv)).sum()),
                rows_touched_without_format_only=int((rmask & ~data['fmt_cand']).any(axis=1).sum()),
                flagged_label_cells=int(full[:, lab_j].sum()),
                parsable_tp=int((feat_flags & data['A_mv']).sum()), parsable_fp=int((feat_flags & ~data['A_mv']).sum()),
                feature_tp_parsable=int((feat_flags & A).sum()))


def make_items(restricted):
    """R34: configurations with identical model-column sets form one item, in CONFIGS order."""
    groups = []
    for c in CONFIGS:
        for g in groups:
            if np.array_equal(restricted[g[0]], restricted[c]):
                g.append(c)
                break
        else:
            groups.append([c])
    return [('='.join(SHORT[c] for c in g), g) for g in groups]


# ---------------------------------------------------------------- policies (R40-R46)
def kept_rows(data, rmask, policy, rows):
    if policy in ('floor', 'clean', 'gt'):
        return rows
    if policy == 'delete':
        return rows[~rmask[rows].any(axis=1)]
    if policy == 'impute':                                   # labels are never imputed: a flagged label costs the row
        return rows[~rmask[rows, data['lab_j']]]
    raise ValueError(policy)


def impute_stats(data, rmask, kept, fill):
    """D2: per feature column, mean (median) of the unflagged parsable cells of the kept training rows, 0.0 if none;
    categorical: mode of the unflagged cells (pandas order on ties), '__none__' if none."""
    stats = {}
    for j in data['num_j']:
        v = data['dirty_num'][kept, j]
        v = v[~rmask[kept, j] & ~np.isnan(v)]
        s = pd.Series(v, dtype=float)
        stats[int(j)] = float(s.mean() if fill == 'mean' else s.median()) if len(v) else 0.0
    for j in data['cat_j']:
        m = pd.Series(data['dirty_txt'][kept, j][~rmask[kept, j]], dtype=object).mode()
        stats[int(j)] = m.iloc[0] if len(m) else '__none__'
    return stats


def apply_policy(data, rmask, policy, rows, stats=None, kept=None):
    """Model-column values of `rows` after `policy`: kept rows, numeric block (parsed, NaN = unparsable),
    categorical block (text), encoded labels. 'floor' = dirty as shipped, 'clean' = clean.csv."""
    if kept is None:
        kept = kept_rows(data, rmask, policy, rows)
    nj, cj, lj = data['num_j'], data['cat_j'], data['lab_j']
    if policy == 'clean':
        num, cat, y = data['clean_num'][np.ix_(kept, nj)], data['clean_txt'][np.ix_(kept, cj)], data['y_clean'][kept]
    else:
        num, cat, y = data['dirty_num'][np.ix_(kept, nj)], data['dirty_txt'][np.ix_(kept, cj)], data['y_dirty'][kept]
    num, cat, y = num.copy(), cat.copy(), y.copy()
    if policy == 'gt':
        f = rmask[np.ix_(kept, nj)]
        num[f] = data['clean_num'][np.ix_(kept, nj)][f]
        f = rmask[np.ix_(kept, cj)]
        cat[f] = data['clean_txt'][np.ix_(kept, cj)][f]
        f = rmask[kept, lj]
        y[f] = data['y_clean'][kept][f]
    elif policy == 'impute':
        for p, j in enumerate(nj):
            num[rmask[kept, j], p] = stats[int(j)]
        for p, j in enumerate(cj):
            cat[rmask[kept, j], p] = stats[int(j)]
    return kept, num, cat, y


def fit_featurizer(num, cat, fill):
    """R29: numeric NaN -> the version's mean (median) of its kept training rows (0.0 if none); one-hot, sorted."""
    df = pd.DataFrame(num)
    mu = (df.mean() if fill == 'mean' else df.median()).fillna(0.0).values.astype(float)
    ohe = OneHotEncoder(handle_unknown='ignore', sparse=False).fit(cat) if cat.shape[1] else None
    return dict(mu=mu, ohe=ohe, width=len(mu) + (sum(len(c) for c in ohe.categories_) if ohe else 0))


def featurize(feat, num, cat):
    """Dense float64 [numeric | one-hot]; unknown categories become all-zero (R30)."""
    if len(num) == 0:
        return np.zeros((0, feat['width']), dtype=float)
    parts = [np.where(np.isnan(num), feat['mu'][None, :], num).astype(float)]
    if feat['ohe'] is not None:
        parts.append(feat['ohe'].transform(cat))
    return np.ascontiguousarray(np.hstack(parts), dtype=float)


def round12(a):
    """float('%.12g' % v) per value, -0.0 -> 0.0 (R54); 0.0 and 1.0 are fixed points."""
    a = np.asarray(a, dtype=float)
    out = a.copy()
    other = ~((a == 0.0) | (a == 1.0))
    if other.any():
        u, inv = np.unique(a[other], return_inverse=True)
        out[other] = np.array([float('%.12g' % v) for v in u], dtype=float)[inv]
    out[out == 0.0] = 0.0
    return out


def train_hash(X, y):
    """R54: sha256 over the shape, the rounded matrix (C order) and the rounded labels; 64 hex digits."""
    X = np.ascontiguousarray(X, dtype=float)
    h = hashlib.sha256()
    h.update(np.array(X.shape, dtype=np.int64).tobytes())
    h.update(np.ascontiguousarray(round12(X)).tobytes())
    h.update(np.ascontiguousarray(round12(np.asarray(y, dtype=float))).tobytes())
    return h.hexdigest()


def is_degenerate(clf, y):
    """R52: fewer than 50 training rows, or one class."""
    return len(y) < 50 or (clf and len(np.unique(y)) < 2)


def test_degenerate(clf, y):
    return len(y) == 0 or (clf and len(np.unique(y)) < 2) or (not clf and len(y) < 2)


def version_counts(data, kept, num, cat, y):
    """Per-seed data columns (R65): cells changed vs dirty, feature errors left, label errors left."""
    nj, cj = data['num_j'], data['cat_j']
    if data['clf']:
        lab_changed = y != data['y_dirty'][kept]
        lab_err = y != data['y_clean'][kept]
    else:
        lab_changed = ~same_value(y, data['y_dirty'][kept])
        lab_err = ~same_value(y, data['y_clean'][kept])
    changed = ((~same_value(num, data['dirty_num'][np.ix_(kept, nj)])).sum()
               + (cat != data['dirty_txt'][np.ix_(kept, cj)]).sum() + lab_changed.sum())
    left = (~same_value(num, data['clean_num'][np.ix_(kept, nj)])).sum() + (cat != data['clean_txt'][np.ix_(kept, cj)]).sum()
    return dict(cells_changed=int(changed), errors_left_in_features=int(left), label_errors_left=int(lab_err.sum()))


# ---------------------------------------------------------------- versions of one seed (R37-R39)
def canonical_versions(d6):
    """R39 order of every possible version: (name, configuration, policy)."""
    out = [('clean', 'none', 'none'), ('floor', 'none', 'none')]
    for pol in POLICIES:
        for c in CONFIGS + EXTRA_SETS + ([D6_NAME] if d6 else []):
            out.append(('{}/{}'.format(c, pol), c, pol))
    out += [('control/' + c, c, 'control') for c in CONFIGS]
    return out


def version_specs(d6, policies):
    """The output versions of a run (R37): clean, floor, the flag sets under the selected policies, and the
    controls when delete is selected."""
    return [v for v in canonical_versions(d6)
            if v[2] == 'none' or v[2] in policies or (v[2] == 'control' and 'delete' in policies)]


def build_version(data, name, config, policy, rmask, tr, te, fill, kept=None, delete_degenerate=False):
    """One version: training values, counts, degenerate flag, featurizer, matrix, hash, and its test rows."""
    pol = {'none': name, 'control': 'floor'}.get(policy, policy)          # 'clean' / 'floor' / a policy
    stats = None
    if pol == 'impute':
        kept = kept_rows(data, rmask, 'impute', tr)
        stats = impute_stats(data, rmask, kept, fill)
    kept, num, cat, y = apply_policy(data, rmask, pol, tr, stats, kept)
    if np.isnan(y).any():                                     # R28: never mapped, never "degenerate" instead
        raise Abort('labels', 'LABEL FAIL {} {}: {} kept training rows have an unparsable label'.format(
            data['ds'], name, int(np.isnan(y).sum())))
    v = dict(name=name, configuration=config, policy=policy, kept=kept, rows_kept=len(kept), num=num, cat=cat, y=y,
             stats=stats, degenerate=bool(delete_degenerate or is_degenerate(data['clf'], y)), train_hash='',
             X=None, feat=None, test=None)
    v.update(version_counts(data, kept, num, cat, y))
    if not v['degenerate']:
        v['feat'] = fit_featurizer(num, cat, fill)
        v['X'] = featurize(v['feat'], num, cat)
        if not np.isfinite(v['X']).all():
            raise Abort('features', 'FEATURE FAIL {} {}: non-finite value in the training matrix'.format(data['ds'], name))
        v['train_hash'] = train_hash(v['X'], y)
    if policy not in ('none', 'control') or name == 'floor':    # S1/S3 test rows (R45)
        tk, tn, tc, ty = apply_policy(data, rmask, pol, te, stats)
        if np.isnan(ty).any():
            raise Abort('labels', 'LABEL FAIL {} {}: {} scored test rows have an unparsable label'.format(
                data['ds'], name, int(np.isnan(ty).sum())))
        v['test'] = (tk, tn, tc, ty)
    return v


def identical(a, b):
    """Same training matrix and labels before rounding (both non-degenerate)."""
    return a['X'] is not None and b['X'] is not None and a['X'].shape == b['X'].shape \
        and np.array_equal(a['X'], b['X']) and np.array_equal(a['y'], b['y'])


def seed_versions(data, restricted, seed, fill, policies, d6):
    """Every output version of one seed in R39 order, plus the check-only versions; runs checks 2 (hash), 3, 4."""
    tr, te = split(data, seed)
    ds, n_train = data['ds'], len(tr)
    empty = np.zeros_like(restricted['perfect'])
    vs, extra = {}, {}
    for name, config, policy in version_specs(d6, policies):
        if policy == 'control':
            dv = vs['{}/delete'.format(config)]
            k = n_train - dv['rows_kept']
            rng = np.random.default_rng([seed, CONFIGS.index(config)])        # R14
            drop = rng.choice(tr, size=k, replace=False)
            kept = np.setdiff1d(tr, drop)
            v = build_version(data, name, config, policy, empty, tr, te, fill, kept=kept,
                              delete_degenerate=dv['degenerate'])
            v['k'] = k
        else:
            rm = empty if policy == 'none' else restricted[config]
            v = build_version(data, name, config, policy, rm, tr, te, fill)
        vs[name] = v
    for name, config, policy in [('perfect/gt', 'perfect', 'gt'), ('always_positive/gt', 'always_positive', 'gt'),
                                 ('perfect/delete', 'perfect', 'delete'), ('perfect/impute', 'perfect', 'impute')]:
        if name not in vs:
            extra[name] = build_version(data, name, config, policy, restricted[config], tr, te, fill)
    for pol in POLICIES:
        extra['empty/' + pol] = build_version(data, 'empty/' + pol, 'empty', pol, empty, tr, te, fill)
    get = lambda nm: vs[nm] if nm in vs else extra[nm]
    floor, clean = vs['floor'], vs['clean']
    lines = []
    # check 2, hash part (R58)
    for nm in ('perfect/gt', 'always_positive/gt'):
        v = get(nm)
        if not identical(v, clean) or v['train_hash'] != clean['train_hash']:
            raise Abort('check2', 'CHECK 2 FAIL {} seed {} {} differs from clean before rounding or by hash'.format(ds, seed, nm))
    lines.append('check 2(hash) {} seed {} PASS'.format(ds, seed))
    # check 3 (R59): the empty set, zero-flag configurations and k = 0 controls equal the floor
    same = [get('empty/' + p) for p in POLICIES]
    same += [v for v in vs.values() if v['policy'] in POLICIES and not restricted[v['configuration']].any()]
    same += [v for v in vs.values() if v['policy'] == 'control' and v['k'] == 0]
    for v in same:
        if not identical(v, floor):
            raise Abort('check3', 'CHECK 3 FAIL {} seed {} {} is not the floor'.format(ds, seed, v['name']))
    lines.append('check 3 {} seed {} PASS ({} versions = floor)'.format(ds, seed, len(same)))
    lines.append(check4(data, get('perfect/delete'), get('perfect/impute'), tr, seed, fill))
    for v in vs.values():
        if v['degenerate'] or v['name'] == 'floor':
            v['eq_floor'] = ''
        elif identical(v, floor):
            v['eq_floor'] = '='
        else:
            v['eq_floor'] = '~' if v['train_hash'] == floor['train_hash'] else ''
    r62 = {}
    for c in CONFIGS + EXTRA_SETS:
        dk = kept_rows(data, restricted[c], 'delete', tr)
        ik = kept_rows(data, restricted[c], 'impute', tr)
        r62[c] = dict(delete=len(dk), impute=len(ik), label_errors_left_impute=version_counts(
            data, ik, data['dirty_num'][np.ix_(ik, data['num_j'])], data['dirty_txt'][np.ix_(ik, data['cat_j'])],
            data['y_dirty'][ik])['label_errors_left'])
    return vs, lines, r62


def check4(data, vdel, vimp, tr, seed, fill):
    """R60, R61, recomputed from actual_errors.csv cell by cell (independent of the masks)."""
    ds = data['ds']
    A = [(i, j) for i, j in data['err_cells'].tolist() if data['col_model'][j]]
    trs = set(tr.tolist())
    bad_rows = {i for i, j in A if i in trs}
    if vdel['rows_kept'] != len(tr) - len(bad_rows):
        raise Abort('check4', 'CHECK 4 FAIL {} seed {} perfect/delete keeps {} rows, expected {}'.format(
            ds, seed, vdel['rows_kept'], len(tr) - len(bad_rows)))
    lab_rows = {i for i, j in A if j == data['lab_j'] and i in trs}
    want_kept = sorted(trs - lab_rows)
    if vimp['kept'].tolist() != want_kept:
        raise Abort('check4', 'CHECK 4 FAIL {} seed {} perfect/impute keeps the wrong rows'.format(ds, seed))
    kept = vimp['kept']
    pos = {r: p for p, r in enumerate(kept.tolist())}
    flagged = {(i, j) for i, j in A if i in pos and j != data['lab_j']}
    nj, cj = data['num_j'].tolist(), data['cat_j'].tolist()
    parsable_written = 0
    for jj, j in enumerate(nj):                               # every numeric cell: flagged -> statistic, else dirty
        fl = {i for i, c in flagged if c == j}
        pool = [data['dirty_num'][i, j] for i in kept.tolist() if i not in fl and isnum(data['dirty_txt'][i, j])]
        s = pd.Series(pool, dtype=float)
        stat = float(s.mean() if fill == 'mean' else s.median()) if pool else 0.0
        col = vimp['num'][:, jj]
        for i in kept.tolist():
            got, dirty = col[pos[i]], data['dirty_num'][i, j]
            if i in fl:
                parsable_written += isnum(data['dirty_txt'][i, j])
                if got != stat:
                    raise Abort('check4', 'CHECK 4 FAIL {} seed {} cell ({}, {}) = {!r}, statistic {!r}'.format(
                        ds, seed, i, j, got, stat))
            elif not (got == dirty or (np.isnan(got) and np.isnan(dirty))):
                raise Abort('check4', 'CHECK 4 FAIL {} seed {} unflagged cell ({}, {}) changed'.format(ds, seed, i, j))
    for jj, j in enumerate(cj):
        fl = {i for i, c in flagged if c == j}
        m = pd.Series([data['dirty_txt'][i, j] for i in kept.tolist() if i not in fl], dtype=object).mode()
        stat = m.iloc[0] if len(m) else '__none__'
        for i in kept.tolist():
            want = stat if i in fl else data['dirty_txt'][i, j]
            if vimp['cat'][pos[i], jj] != want:
                raise Abort('check4', 'CHECK 4 FAIL {} seed {} categorical cell ({}, {})'.format(ds, seed, i, j))
            parsable_written += i in fl and isnum(data['dirty_txt'][i, j])
    return 'check 4 {} seed {} PASS (delete keeps {}, impute keeps {}, cells written {}, parsable {})'.format(
        ds, seed, vdel['rows_kept'], len(want_kept), len(flagged), parsable_written)


# ---------------------------------------------------------------- models and scores (R48-R52)
def make_models(clf):
    if clf:
        return [('linear', LogisticRegression(max_iter=5000), True),
                ('rf', RandomForestClassifier(random_state=0, n_jobs=1), False),
                ('xgb', XGBClassifier(random_state=0, n_jobs=1, use_label_encoder=False, eval_metric='logloss',
                                      verbosity=0), False)]
    return [('linear', Ridge(), True), ('rf', RandomForestRegressor(random_state=0, n_jobs=1), False),
            ('xgb', XGBRegressor(random_state=0, n_jobs=1, verbosity=0), False)]


def fit_all(clf, X, y):
    out = {}
    for name, model, scale in make_models(clf):
        scaler = StandardScaler().fit(X) if scale else None
        ts = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        t0 = time.perf_counter()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            model.fit(scaler.transform(X) if scaler else X, y.astype(int) if clf else y)
        out[name] = dict(model=model, scaler=scaler, fit_s=time.perf_counter() - t0, timestamp=ts,
                         conv=sum(1 for x in w if issubclass(x.category, ConvergenceWarning)))
    return out


def predict(m, X):
    return m['model'].predict(m['scaler'].transform(X) if m['scaler'] else X)


def score(clf, y, p):
    if clf:
        y = y.astype(int)
        f1 = f1_score(y, p, pos_label=1, zero_division=0)
        return dict(score=f1, f1=f1, precision=precision_score(y, p, pos_label=1, zero_division=0),
                    recall=recall_score(y, p, pos_label=1, zero_division=0))
    rmse = math.sqrt(mean_squared_error(y, p))
    return dict(score=-rmse, rmse=rmse, r2=r2_score(y, p))


# ---------------------------------------------------------------- one (dataset, seed) task
_CACHE = {}


def cached(ds, cfg, files):
    """Per-process cache of the loaded dataset and its flag masks (one entry per dataset and input set)."""
    key = (ds, tuple(sorted(files.items())))
    if key not in _CACHE:
        data = load_data(ds, cfg, files)
        _CACHE[key] = (data,) + flag_masks(data, files)
    return _CACHE[key]


def run_seed(task):
    """Phase A (train=False): versions, hashes and checks. Phase B: the same versions, then fitting and scoring."""
    ds, seed, fill = task['ds'], task['seed'], task['fill']
    data, full, restricted = cached(ds, task['cfg'], task['files'])
    t0 = time.time()
    vs, lines, r62 = seed_versions(data, restricted, seed, fill, task['policies'], task['d6'])
    summary = [dict(name=v['name'], configuration=v['configuration'], policy=v['policy'], rows_kept=v['rows_kept'],
                    degenerate=v['degenerate'], train_hash=v['train_hash'], eq_floor=v['eq_floor'], k=v.get('k'),
                    width=v['X'].shape[1] if v['X'] is not None else None)
               for v in vs.values()]
    res = dict(ds=ds, seed=seed, summary=summary, lines=lines, r62=r62, rows=[], conv={m: 0 for m in MODELS},
               reuse={}, build_s=time.time() - t0)
    if task['mode'] == 'check':
        res['lines'].append(check2_training(data, restricted, vs, seed, fill))
    elif task['mode'] == 'full':
        res['rows'], res['reuse'], res['conv'] = train_seed(data, vs, task)
    res['elapsed_s'] = time.time() - t0
    return res


def check2_training(data, restricted, vs, seed, fill):
    """R58 training part: clean, perfect + GT and always-positive + GT fitted separately; S2 == S4 exactly."""
    tr, te = split(data, seed)
    clean = vs['clean']
    S2X = lambda v: featurize(v['feat'], data['clean_num'][np.ix_(te, data['num_j'])], data['clean_txt'][np.ix_(te, data['cat_j'])])
    yte = data['y_clean'][te]
    s4 = {m: score(data['clf'], yte, predict(f, S2X(clean)))['score'] for m, f in fit_all(data['clf'], clean['X'], clean['y']).items()}
    for nm in ('perfect/gt', 'always_positive/gt'):
        v = vs.get(nm) or build_version(data, nm, nm.split('/')[0], 'gt', restricted[nm.split('/')[0]], tr, te, fill)
        for m, f in fit_all(data['clf'], v['X'], v['y']).items():
            s2 = score(data['clf'], yte, predict(f, S2X(v)))['score']
            if s2 != s4[m]:
                raise Abort('check2', 'CHECK 2 FAIL {} seed {} {} {}: S2 {!r} != S4 {!r}'.format(data['ds'], seed, nm, m, s2, s4[m]))
    return 'check 2(train) {} seed {} PASS (S2 = S4 for perfect/gt, always_positive/gt, {} models)'.format(
        data['ds'], seed, len(MODELS))


def train_seed(data, vs, task):
    """R50, R55: fit once per train_hash group (representative = first in R39 order) and score every member with
    that model on its own test matrices; groups are fitted one at a time, only the clean model is kept."""
    seed = task['seed']
    te = split(data, seed)[1]
    groups, dead = {}, []
    for v in vs.values():
        (dead if v['degenerate'] else groups.setdefault(v['train_hash'], [])).append(v)
    conv = {m: 0 for m in MODELS}
    clean = vs['clean']
    clean_fit = fit_all(data['clf'], clean['X'], clean['y'])
    rows = []
    for h, members in groups.items():
        fit = clean_fit if members[0] is clean else fit_all(data['clf'], members[0]['X'], members[0]['y'])
        for m in MODELS:
            conv[m] += fit[m]['conv']
        for v in members:
            rows += score_version(data, task, v, fit, v is members[0], clean_fit, clean['feat'], te)
    for v in dead:
        rows += score_version(data, task, v, None, False, clean_fit, clean['feat'], te)
    reuse = {h: [v['name'] for v in members] for h, members in groups.items() if len(members) > 1}
    return rows, reuse, conv


def score_version(data, task, v, fit, rep, clean_fit, clean_feat, te):
    """The result rows of one version: S4 (clean), S2 (controls) or S1/S2/S3 (R50-R52, R64-R65)."""
    clf = data['clf']
    te_num, te_cat, yte = data['clean_num'][np.ix_(te, data['num_j'])], data['clean_txt'][np.ix_(te, data['cat_j'])], data['y_clean'][te]
    mats = {}                                                  # each test matrix once per version (R30)
    if fit is not None:
        mats['S2'] = featurize(clean_feat if v['name'] == 'clean' else v['feat'], te_num, te_cat)
        if v['test'] is not None:
            mats['S1'] = featurize(v['feat'], v['test'][1], v['test'][2])
            mats['S3'] = featurize(clean_feat, v['test'][1], v['test'][2])
    base = dict(dataset=task['ds'], task='classification' if clf else 'regression', fill=task['fill'], version=v['name'],
                item=task['item_of'].get(v['configuration'], v['name'] if v['policy'] == 'none' else v['configuration']),
                configuration=v['configuration'], policy=v['policy'], seed=task['seed'], rows_kept=v['rows_kept'],
                cells_changed=v['cells_changed'], errors_left_in_features=v['errors_left_in_features'],
                label_errors_left=v['label_errors_left'], degenerate=int(v['degenerate']), train_hash=v['train_hash'])
    stats = task['flag_stats'].get(v['configuration']) if v['policy'] in POLICIES else None
    for col in FLAG_COLS:
        base[col] = stats[col] if stats else ''
    scen = ['S4'] if v['name'] == 'clean' else ['S2'] if v['policy'] == 'control' else ['S1', 'S2', 'S3']
    rows = []
    for m in MODELS:
        f = fit[m] if fit is not None else None
        for s in scen:
            row = dict(base, model=m, scenario=s, fit_s=f['fit_s'] if f and rep else '',
                       timestamp=f['timestamp'] if f else '', test_degenerate=0)
            if s in ('S2', 'S4'):
                row['test_rows'] = len(te)
                if f:
                    row.update(score(clf, yte, predict(clean_fit[m] if s == 'S4' else f, mats['S2'])))
            else:
                ty = v['test'][3]
                row['test_rows'] = len(ty)
                row['test_degenerate'] = int(test_degenerate(clf, ty))
                if f and not row['test_degenerate']:
                    row.update(score(clf, ty, predict(f if s == 'S1' else clean_fit[m], mats[s])))
            rows.append(row)
    return rows


# ---------------------------------------------------------------- references and expected verdicts (R86-R90)
def f1_counts(det, truth, tp):
    if not det or not truth or tp == 0:
        return 0.0
    p, r = tp / det, tp / truth
    return 2 * p * r / (p + r)


def mech_degenerate(data, rmask, policy):
    """MF's degenerate rule (rows < 50 or one clean class among the kept rows) on every seed 0-9."""
    for seed in MECH_SEEDS:
        tr, _ = split(data, seed)
        kept = kept_rows(data, rmask, policy, tr)
        if not (len(kept) < 50 or (data['clf'] and len(np.unique(data['y_clean'][kept])) < 2)):
            return False
    return True


def mechanism(data, rmask):
    """Mechanism score (d) per policy, exactly as IP L75-102."""
    A_mv, lab_j = data['A_mv'], data['lab_j']
    n_mv = int(A_mv.sum())
    gt = int((rmask & A_mv).sum()) / n_mv if n_mv else 0.0
    if mech_degenerate(data, rmask, 'delete'):
        dl = -math.inf
    elif not rmask.any():
        dl = 'floor'
    else:
        frows = rmask.any(axis=1)
        dl = int((frows & A_mv.any(axis=1)).sum()) / int(frows.sum())
    if mech_degenerate(data, rmask, 'impute'):
        im = -math.inf
    else:
        fp_ = rmask & data['col_feat'][None, :] & data['parsable']
        net = int((fp_ & A_mv).sum()) - int((fp_ & ~A_mv).sum())
        lrows, lerr = rmask[:, lab_j], A_mv[:, lab_j]
        if lrows.any():
            net += int((lrows & lerr).sum()) - int((lrows & ~lerr).sum())
        im = 'floor' if (net == 0 and not lrows.any()) else net
    return dict(gt=gt, delete=dl, impute=im)


def references(data, full, restricted, items):
    """(a) published and recomputed, (b) row F1, (c) model-visible F1, (d) mechanism, per item (R86-R90)."""
    ds, A, A_mv = data['ds'], data['A'], data['A_mv']
    rows_err = A.any(axis=1)
    per = {}
    for c in CONFIGS:
        f, r = full[c], restricted[c]
        rows = f.any(axis=1)
        per[c] = dict(a=PUBLISHED_F1[ds][c], a_re=f1_counts(int(f.sum()), int(A.sum()), int((f & A).sum())),
                      b=f1_counts(int(rows.sum()), int(rows_err.sum()), int((rows & rows_err).sum())),
                      c=f1_counts(int(r.sum()), int(A_mv.sum()), int((r & A_mv).sum())))
        if round(per[c]['a_re'], 3) != per[c]['a']:
            raise Abort('references', 'REFERENCE FAIL {} {}: published F1 {} but the frozen flags give {:.4f}'.format(
                ds, c, per[c]['a'], per[c]['a_re']))
    ref = {}
    for name, members in items:
        vals = {k: [per[c][k] for c in members] for k in ('a', 'a_re', 'b', 'c')}
        mech = [mechanism(data, restricted[c]) for c in members]
        if any(len(set(v)) > 1 for v in vals.values()) or any(m != mech[0] for m in mech):
            raise Abort('references', 'REFERENCE FAIL {} item {}: members disagree (A24)'.format(ds, name))
        ref[name] = dict({k: max(v) for k, v in vals.items()}, d=mech[0])
    a = [ref[nm]['a'] for nm, _ in items]
    if len(set(a)) != len(a):
        raise Abort('references', 'REFERENCE FAIL {}: tied items under (a) {}'.format(ds, a))
    return ref


def fmt_mech(v):
    return v if isinstance(v, str) else ('degenerate' if v == -math.inf else round(v, 3))


def cmp_mech(x, y):
    if x == 'floor' or y == 'floor':
        return None if x != y else 0
    return (x > y) - (x < y)


def expected_verdicts(ds, items, ref):
    """Expected verdict of every pair x policy against (a), as IP L99-119."""
    out = []
    for pol in POLICIES:
        for (na, _), (nb, _) in itertools.combinations(items, 2):
            ra, rb = ref[na]['a'], ref[nb]['a']
            r = (ra > rb) - (ra < rb)
            m = cmp_mech(ref[na]['d'][pol], ref[nb]['d'][pol])
            verdict = 'undetermined' if (m is None or m == 0 or r == 0) else 'concordant' if m == r else 'discordant'
            out.append(dict(dataset=ds, policy=pol, pair='{} vs {}'.format(na, nb),
                            reference_a='{} > {}'.format(*((na, nb) if r > 0 else (nb, na))) if r else 'tie',
                            mechanism_a=fmt_mech(ref[na]['d'][pol]), mechanism_b=fmt_mech(ref[nb]['d'][pol]),
                            expected=verdict))
    return out


def same_mech(csv_value, value):
    if isinstance(value, str) or csv_value in ('floor', 'degenerate'):
        return str(value) == csv_value
    return abs(float(csv_value) - float(value)) <= 5e-4 + 1e-12


def compare_verdicts(ds, rows, path, strict):
    """Rows vs a committed verdict file: (matching rows, total, verdict differences). strict: mechanism too."""
    if not os.path.exists(path):
        return None
    f = pd.read_csv(path, dtype=str, keep_default_na=False)
    f = f[f['dataset'] == ds]
    if len(f) == 0:
        return None
    want = {(r['policy'], r['pair']): r for _, r in f.iterrows()}
    ok, diff = 0, []
    for r in rows:
        w = want.get((r['policy'], r['pair']))
        if w is None:
            diff.append('{} {}: not in the file'.format(r['policy'], r['pair']))
            continue
        good = w['expected'] == r['expected'] and w['reference_a'] == r['reference_a']
        if strict:
            good = good and same_mech(w['mechanism_a'], r['mechanism_a']) and same_mech(w['mechanism_b'], r['mechanism_b'])
        if good:
            ok += 1
        else:
            diff.append('{} {}: file {}/{}/{} vs {}/{}/{}'.format(r['policy'], r['pair'], w['mechanism_a'], w['mechanism_b'],
                                                                 w['expected'], r['mechanism_a'], r['mechanism_b'], r['expected']))
    return ok, max(len(f), len(rows)), diff


# ---------------------------------------------------------------- environment and inputs (R8-R12, R16)
def parse_seeds(tokens):
    seeds = []
    for t in tokens:
        if '-' in t:
            a, b = t.split('-')
            seeds += list(range(int(a), int(b) + 1))
        else:
            seeds.append(int(t))
    if len(set(seeds)) != len(seeds):
        raise SystemExit('FAIL args: duplicate seeds {}'.format(seeds))
    return sorted(seeds)


def resolve_out(path):
    """R8: a new or empty directory inside reports/block_d/runs/."""
    out, root = os.path.realpath(path), os.path.realpath(RUNS_ROOT)
    if out == root or os.path.commonpath([out, root]) != root:
        raise SystemExit('FAIL out: {} is not inside {}'.format(path, RUNS_ROOT))
    if os.path.exists(out) and (not os.path.isdir(out) or os.listdir(out)):
        raise SystemExit('FAIL out: {} exists and is not empty'.format(path))
    return out


def git(*cmd):
    try:
        p = subprocess.run(['git', '-C', R] + list(cmd), capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout.strip()
    except Exception as e:                                    # noqa: BLE001
        return None, str(e)


def check_environment(mode, say):
    """R10-R12: thread settings, one thread per pool, the fingerprint and git state."""
    bad = {k: os.environ.get(k) for k, v in THREAD_VARS.items() if os.environ.get(k) != v}
    if bad:
        raise Abort('env', 'ENV FAIL thread settings must be {}; got {}'.format(THREAD_VARS, bad))
    import scipy
    import scipy.linalg                                       # noqa: F401
    import sklearn
    import xgboost
    import threadpoolctl
    info = threadpoolctl.threadpool_info()
    if any(p.get('num_threads') != 1 for p in info):
        raise Abort('env', 'ENV FAIL a thread pool has more than one thread: {}'.format(
            [(p.get('internal_api'), p.get('num_threads')) for p in info]))
    if mode != 'dry_run' and not os.environ.get('REIN_IMAGE_ID'):
        raise Abort('env', 'ENV FAIL REIN_IMAGE_ID is required for full and --check runs')
    try:
        from numpy.core._multiarray_umath import __cpu_features__ as cpu
    except ImportError:
        cpu = {}
    # hostname is the container ID under docker compose run, so it changes with every run; the
    # analysis compares host_fingerprint (architecture + the CPU features numpy sees) instead.
    feats = sorted(k for k, v in dict(cpu).items() if v)
    host_fp = '{}:{}'.format(platform.machine(), hashlib.sha256(','.join(feats).encode()).hexdigest()[:12])
    env = dict(hostname=socket.gethostname(), host_fingerprint=host_fp, machine=platform.machine(),
               platform=platform.platform(),
               versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                             sklearn=sklearn.__version__, scipy=scipy.__version__, xgboost=xgboost.__version__,
                             threadpoolctl=threadpoolctl.__version__),
               threadpool_info=info, cpu_features=dict(cpu), sched_affinity=len(os.sched_getaffinity(0)),
               cpu_count_unreliable=os.cpu_count(),
               variables={k: os.environ.get(k) for k in list(THREAD_VARS) + ['OPENBLAS_CORETYPE', 'REIN_IMAGE_ID']})
    rc, head = git('rev-parse', 'HEAD')
    env['git_head'] = head if rc == 0 else 'unknown'
    rc, st = git('status', '--porcelain')
    env['git_status'] = st if rc == 0 else 'unknown'
    rc, _ = git('diff', '--quiet', FROZEN_COMMIT, '--', FROZEN_VERDICTS[len(R) + 1:])
    if rc == 1:
        raise Abort('env', 'ENV FAIL {} differs from {}'.format(FROZEN_VERDICTS, FROZEN_COMMIT))
    env['frozen_verdicts_vs_c61ee72'] = 'unchanged' if rc == 0 else 'unknown'
    if rc != 0:
        say('WARNING git could not compare the frozen verdict file with {} (recorded as unknown)'.format(FROZEN_COMMIT))
    return env


def copy_inputs(out, datasets, data_root, flags_dir):
    """R16: copy every input, hash the copies, hash the replay and reference files without copying them."""
    files, sha = {}, {}
    os.makedirs(os.path.join(out, 'inputs'))
    for ds in datasets:
        dst = os.path.join(out, 'inputs', ds)
        os.makedirs(dst)
        f = {}
        for key, name, src in [('dirty', 'dirty.csv', data_root), ('clean', 'clean.csv', data_root),
                               ('errors', 'actual_errors.csv', data_root)] + [(c, c + '.csv', flags_dir) for c in CONFIGS]:
            s = os.path.join(src, ds, name)
            if not os.path.exists(s):
                raise Abort('check1', 'CHECK 1 FAIL {} missing input {}'.format(ds, s))
            shutil.copyfile(s, os.path.join(dst, name))
            f[key] = os.path.join(dst, name)
            sha['inputs/{}/{}'.format(ds, name)] = sha256_file(f[key])
        files[ds] = f
    man = os.path.join(out, 'inputs', 'MANIFEST.csv')
    if not os.path.exists(os.path.join(flags_dir, 'MANIFEST.csv')):
        raise Abort('check1', 'CHECK 1 FAIL missing input {}'.format(os.path.join(flags_dir, 'MANIFEST.csv')))
    shutil.copyfile(os.path.join(flags_dir, 'MANIFEST.csv'), man)
    sha['inputs/MANIFEST.csv'] = sha256_file(man)
    hashed = {}
    for p in ['{}/{}/constraints/{}_dcs.txt'.format(data_root, ds, ds) for ds in datasets] + [R + '/' + h for h in HASHED_ONLY]:
        hashed[p] = sha256_file(p) if os.path.exists(p) else 'missing'
    return files, man, sha, hashed


def replay(ds, config, dirty, clean):
    """The replay of plan check 1c (freeze L40-49); None for Raha."""
    if config == 'ge_dirty_profiled':
        return ns['ge'](dirty, ns['prof'].profile_expectations(dirty))
    if config == 'ge_clean_profiled':
        return ns['ge'](dirty, ns['prof'].profile_expectations(clean))
    if config == 'ge_hand_written':
        return ns['ge'](dirty, ns['hw'].get(ds, {}).get('hand_written', []))
    if config == 'holoclean':
        return ns['holo'](dirty, ds)
    return None


def check1(ds, data, files, manifest_rows, full):
    """R19-R21: MANIFEST row, sha256, Table 3 counts, replay identity."""
    A = cell_set(data['err_cells'])
    dirty, clean = read_table(files['dirty']), read_table(files['clean'])
    counts = {}
    for c in CONFIGS:
        rows = [r for r in manifest_rows if r['dataset'] == ds and r['config'] == c]
        if len(rows) != 1:
            raise Abort('check1', 'CHECK 1 FAIL {} {} {} MANIFEST rows'.format(ds, c, len(rows)))
        r = rows[0]
        if sha256_file(files[c]) != r['sha256']:
            raise Abort('check1', 'CHECK 1 FAIL {} {} sha256 differs from MANIFEST'.format(ds, c))
        cells = cell_set(read_cells_array(files[c]))
        got = tuple(tp_fp(cells, A))
        man = (int(r['tp']), int(r['fp']), int(r['detections']))
        if not (got == man == tuple(TABLE3[ds][c])):
            raise Abort('check1', 'CHECK 1 FAIL {} {} TP/FP/det file {} MANIFEST {} Table 3 {}'.format(
                ds, c, got, man, tuple(TABLE3[ds][c])))
        rep = replay(ds, c, dirty, clean)
        if rep is not None and rep != cells:
            raise Abort('check1', 'CHECK 1 FAIL {} {} replay differs: {} cells only in the file, {} only in the replay'.format(
                ds, c, len(cells - rep), len(rep - cells)))
        counts[c] = dict(expected=list(TABLE3[ds][c]), recomputed=list(got), sha12=r['sha256'][:12],
                         replay='n/a' if rep is None else 'identical')
    return counts


# ---------------------------------------------------------------- dry-run text (R69, R70)
def rng_text(vals):
    return '{}-{}'.format(min(vals), max(vals)) if vals else '-'


def seeds_text(seeds):
    """Sorted seeds as runs: [0..9] -> '0-9', [0, 2] -> '0,2', [0, 1, 2, 5] -> '0-2,5'."""
    runs = []
    for s in sorted(seeds):
        if runs and s == runs[-1][1] + 1:
            runs[-1][1] = s
        else:
            runs.append([s, s])
    return ','.join(str(a) if a == b else '{}-{}'.format(a, b) for a, b in runs) or '-'


def dataset_text(ds, prep, results, seeds):
    """Sections 1-11 of dryrun.txt for one dataset (data-derived only)."""
    data, st, items, ref = prep['data'], prep['stats'], prep['items'], prep['ref']
    E = EXPECT.get(ds, {})
    by = {}
    for res in results:
        for s in res['summary']:
            by.setdefault(s['name'], []).append(dict(s, seed=res['seed']))
    L = ['', '=' * 100, ds, '=' * 100, '[1] schema']
    tr, te = split(data, seeds[0])
    cols = data['cols']
    L.append('  n {}  n_train {}  n_test {}'.format(data['n'], len(tr), len(te)))
    if data['clf']:
        L.append('  label {} (classification; {!r} -> 1, {!r} -> 0)'.format(cols[data['lab_j']], data['pos'], data['neg']))
    else:
        L.append('  label {} (regression)'.format(cols[data['lab_j']]))
    for nm, js in (('numeric', data['num_j']), ('categorical', data['cat_j']), ('excluded', data['excl_j'])):
        L.append('  {} ({}): {}'.format(nm, len(js), ', '.join(cols[j] for j in js) or '-'))
    width = by['floor'][0]['width']
    L.append('  featurized width (floor, seed {}): {}{}'.format(seeds[0], width, '' if E.get('width') in (None, width)
                                                               else '  MISMATCH expected {}'.format(E['width'])))
    L.append('[2] flag sets (det/TP/FP all columns; the rest model columns; label = flagged label cells)')
    L.append('  {:<24}{:>8}{:>7}{:>8}{:>8}{:>7}{:>8}{:>5}{:>9}{:>7}{:>7}{:>7}  {:<13}{}'.format(
        'set', 'det', 'TP', 'FP', 'model', 'excl', 'fmtFP', 'neq', 'rows-fmt', 'label', 'pTP', 'pFP', 'sha256', 'check 1'))
    for c in CONFIGS + EXTRA_SETS + ([D6_NAME] if ds in D6 else []):
        s = st[c]
        L.append('  {:<24}{:>8}{:>7}{:>8}{:>8}{:>7}{:>8}{:>5}{:>9}{:>7}{:>7}{:>7}  {:<13}{}'.format(
            c, s['detections'], s['tp'], s['fp'], s['model_flags'], s['excl_col_flags'], s['format_only_fp'],
            s['format_only_not_equal'], s['rows_touched_without_format_only'], s['flagged_label_cells'], s['parsable_tp'],
            s['parsable_fp'], prep['check1'][c]['sha12'] if c in CONFIGS else '-',
            'PASS (replay {})'.format(prep['check1'][c]['replay']) if c in CONFIGS else '-'))
    if any(st[c]['format_only_not_equal'] for c in st):
        L.append('  WARNING format-only FPs that are not numerically equal (R36): {}'.format(
            {c: st[c]['format_only_not_equal'] for c in st if st[c]['format_only_not_equal']}))
    L.append('[3] items and pairs: {} items, {} pairs'.format(len(items), len(items) * (len(items) - 1) // 2))
    for nm, members in items:
        L.append('  {:<34} {}'.format(nm, '+'.join(members)))
    L.append('[4] versions: training rows kept min-max over seeds {}; D = degenerate on all seeds, D(k/n) on some;'.format(
        seeds_text(seeds)))
    L.append('    = floor: identical to the floor before rounding on every seed; ~ floor: same rounded hash on every seed')
    pols = [p for p in POLICIES if any(k.endswith('/' + p) for k in by)]
    L.append('  {:<24}'.format('set') + ''.join('{:<26}'.format(p) for p in pols))

    def cell(name):
        if name not in by:
            return '-'
        ss = by[name]
        t = rng_text([s['rows_kept'] for s in ss])
        nd = sum(s['degenerate'] for s in ss)
        if nd:
            t += ' D' if nd == len(ss) else ' D({}/{})'.format(nd, len(ss))
        if all(s['eq_floor'] == '=' for s in ss):
            t += ' = floor'
        elif all(s['eq_floor'] in ('=', '~') for s in ss):
            t += ' ~ floor'
        return t
    for c in CONFIGS + EXTRA_SETS + ([D6_NAME] if ds in D6 else []):
        L.append('  {:<24}'.format(c) + ''.join('{:<26}'.format(cell('{}/{}'.format(c, p))) for p in pols))
    if 'control/' + CONFIGS[0] in by:
        L.append('  random controls (k = rows the delete version removes):')
        for c in CONFIGS:
            ss = by['control/' + c]
            L.append('    control/{:<20} k {:<14} {}'.format(c, rng_text([s['k'] for s in ss]), cell('control/' + c)))
    deg_all = {(s['configuration'], s['policy']) for nm, ss in by.items() for s in ss[:1]
               if all(x['degenerate'] for x in ss) and s['policy'] in POLICIES}
    L.append('[5] items left after removing degenerate items')
    for p in ('delete', 'impute'):
        if any(k.endswith('/' + p) for k in by):
            left = [nm for nm, members in items if (members[0], p) not in deg_all]
            L.append('  {:<7} {} of {}: {}'.format(p, len(left), len(items), ', '.join(left)))
    L.append('[6] degenerate versions')
    for nm, ss in by.items():
        nd = sum(s['degenerate'] for s in ss)
        if nd:
            L.append('  {:<34} {}/{} seeds'.format(nm, nd, len(ss)))
    if ds in EXPECTED_DEGENERATE:
        sel = {(c, p) for (c, p) in EXPECTED_DEGENERATE[ds] if p in pols}
        got = {x for x in deg_all if x[0] != D6_NAME}
        some = sorted(nm for nm, ss in by.items() if 0 < sum(s['degenerate'] for s in ss) < len(ss))
        L.append('  expected list (R53): {}'.format('match' if got == sel and not some else 'MISMATCH unexpected {} missing {} partial {}'.format(
            sorted(got - sel), sorted(sel - got), some)))
    s = st['raha']
    L.append('[7] Raha (frozen run 1): TP/FP/det {}/{}/{}; format-only FPs {}; label flags {}; rows kept {}'.format(
        s['tp'], s['fp'], s['detections'], s['format_only_fp'], s['flagged_label_cells'],
        '; '.join('{} {}'.format(p, cell('raha/' + p)) for p in pols)))
    it = [nm for nm, members in items if 'raha' in members][0]
    L.append('    references: (a) {:.3f} (b) {:.4f} (c) {:.4f}'.format(ref[it]['a'], ref[it]['b'], ref[it]['c']))
    L.append('[8] references (item: (a) published / recomputed, (b) row F1, (c) model-visible cell F1)')
    for nm, _ in items:
        r = ref[nm]
        L.append('  {:<34} (a) {:.3f} / {:.4f}  (b) {:.4f}  (c) {:.4f}'.format(nm, r['a'], r['a_re'], r['b'], r['c']))
    for k in ('a', 'b', 'c'):
        order = sorted(ref, key=lambda nm: -ref[nm][k])
        L.append('  order ({}) {}'.format(k, ' > '.join('{}({:.3f})'.format(nm, ref[nm][k]) for nm in order)))
    L.append('[9] expected verdicts: mechanism (d) per item and policy, verdict per pair against (a)')
    for nm, _ in items:
        L.append('  {:<34} gt {:<10} delete {:<12} impute {}'.format(nm, *[str(fmt_mech(ref[nm]['d'][p])) for p in POLICIES]))
    for r in prep['verdicts']:
        L.append('  {:<7}{:<46}{:<46}{:>12}{:>12}  {}'.format(r['policy'], r['pair'], r['reference_a'], str(r['mechanism_a']),
                                                           str(r['mechanism_b']), r['expected']))
    L.append('  addendum match: {}'.format(prep['addendum_text']))
    L.append('  verdicts differing from c61ee72 file: {}'.format(prep['frozen_text']))
    for p in POLICIES:
        L.append('  {:<7} C/D/U {}/{}/{}'.format(p, *prep['cdu'][p]))
    L.append('[10] checks')
    L += ['  ' + x for x in prep['check_lines']]
    L.append('[11] train_hash digest {} {}'.format(ds, prep['digest']))
    return L


def digest(results):
    """R70: sha256 of the sorted lines version|policy|seed|rows_kept|degenerate|train_hash."""
    lines = sorted('{}|{}|{}|{}|{}|{}'.format(s['name'], s['policy'], res['seed'], s['rows_kept'], int(s['degenerate']),
                                               s['train_hash']) for res in results for s in res['summary'])
    return hashlib.sha256('\n'.join(lines).encode()).hexdigest()


# ---------------------------------------------------------------- main
def fmt_value(v):
    if v is None or v == '':
        return ''
    if isinstance(v, (bool, np.bool_)):
        return str(int(v))
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return repr(float(v))
    return str(v)


def write_atomic(path, text):
    with open(path + '.tmp', 'w', newline='') as f:
        f.write(text)
    os.replace(path + '.tmp', path)


def parse_args(argv):
    ap = argparse.ArgumentParser(description='Block D downstream driver (plan v2.1).')
    ap.add_argument('--datasets', nargs='+', default=['breast_cancer', 'nasa'])
    ap.add_argument('--flags_dir', required=True)
    ap.add_argument('--data_root', default=R + '/datasets')
    ap.add_argument('--out', required=True)
    ap.add_argument('--policies', nargs='+', default=list(POLICIES), choices=POLICIES)
    ap.add_argument('--fill', default='mean', choices=['mean', 'median'])
    ap.add_argument('--seeds', nargs='+', default=['0-9'])
    ap.add_argument('--jobs', type=int, default=1)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--dry_run', action='store_true')
    g.add_argument('--check', action='store_true')
    args = ap.parse_args(argv)
    bad = [ds for ds in args.datasets if ds not in CFG]
    if bad or len(set(args.datasets)) != len(args.datasets):
        ap.error('unknown or repeated datasets: {}'.format(args.datasets))
    args.policies = [p for p in POLICIES if p in args.policies]
    args.seeds = parse_seeds(args.seeds)
    if args.jobs < 1:
        ap.error('--jobs must be >= 1')
    return args


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ['--selftest']:
        return selftest()
    args = parse_args(argv)
    mode = 'dry_run' if args.dry_run else 'check' if args.check else 'full'
    try:
        out = resolve_out(args.out)
    except SystemExit as e:                                  # refused before anything is written (R8)
        print(str(e), flush=True)
        return 2
    os.makedirs(out, exist_ok=True)
    log, dry, check_lines = [], [], []

    def say(line, to_dry=False):
        print(line, flush=True)
        log.append(line)
        if to_dry:
            dry.append(line)
    manifest = dict(mode=mode, status='running', fill=args.fill, datasets=args.datasets, seeds=args.seeds,
                    policies=args.policies, argv=sys.argv, args=vars(args), started=datetime.datetime.utcnow().isoformat() + 'Z')
    t_start = time.time()
    try:
        manifest['environment'] = check_environment(mode, say)
        ns['D'] = args.data_root                              # the HoloClean replay reads <data_root>/<ds>/constraints
        files, man_path, manifest['inputs'], manifest['hashed_inputs'] = copy_inputs(out, args.datasets, args.data_root,
                                                                                     args.flags_dir)
        manifest_rows = list(csv.DictReader(open(man_path)))
        add_mf = json.load(open(ADDENDUM_MF)) if os.path.exists(ADDENDUM_MF) else {}
        say('Block D driver, mode {}, fill {}, datasets {}, seeds {}, policies {}'.format(
            mode, args.fill, ' '.join(args.datasets), seeds_text(args.seeds), ' '.join(args.policies)))
        prep, wall = {}, {}
        for ds in args.datasets:                              # check 1 and everything flag-derived, before any version
            t0 = time.time()
            prep[ds] = prepare(ds, files[ds], manifest_rows, add_mf, say)
            wall[ds] = time.time() - t0
            say('prepared {} ({:.1f} s)'.format(ds, wall[ds]))
        tasks = [dict(ds=ds, cfg=CFG[ds], files=files[ds], seed=s, fill=args.fill, policies=args.policies,
                      d6=ds in D6, mode='dry_run', item_of=prep[ds]['item_of'],
                      flag_stats={k: {c: v[c] for c in FLAG_COLS} for k, v in prep[ds]['stats'].items()})
                 for ds in args.datasets for s in args.seeds]
        resA = run_tasks(tasks, args.jobs, say)               # phase A: versions and checks 2 (hash), 3, 4 for every seed
        for ds in args.datasets:
            res = [r for r in resA if r['ds'] == ds]
            finish_dataset(ds, prep[ds], res, add_mf, args, say)
            wall[ds] += sum(r['elapsed_s'] for r in res)
        pooled = {p: [sum(prep[ds]['cdu'][p][i] for ds in args.datasets) for i in range(3)] for p in POLICIES}
        n_add = sum(prep[ds]['addendum'][0] for ds in args.datasets if prep[ds]['addendum'])
        n_all = sum(prep[ds]['addendum'][1] for ds in args.datasets if prep[ds]['addendum'])
        for ds in args.datasets:
            for line in dataset_text(ds, prep[ds], [r for r in resA if r['ds'] == ds], args.seeds):
                say(line, True)
            check_lines += prep[ds]['check_lines']
        say('', True)
        say('=' * 100, True)
        say('pooled expected verdicts over {} (C/D/U; plan §9 for four datasets: GT 19/10/0, delete 16/4/9, impute 12/1/16)'.format(
            ' '.join(args.datasets)), True)
        for p in POLICIES:
            C, D_, U = pooled[p]
            say('  {:<7} C {} D {} U {} of {} -> concordant among determined {:.2f}, of all pairs {:.2f}'.format(
                p, C, D_, U, C + D_ + U, C / max(C + D_, 1), C / max(C + D_ + U, 1)), True)
        say('  addendum match: {}/{}'.format(n_add, n_all) if n_all else '  addendum match: n/a', True)
        if set(args.datasets) == set(DATASETS):
            if any(tuple(pooled[p]) != POOLED_SECTION9[p] for p in POLICIES):
                raise Abort('verdicts', 'VERDICT FAIL pooled C/D/U {} differ from plan §9 {}'.format(pooled, POOLED_SECTION9))
            say('  pooled = plan §9: yes', True)
        manifest['flag_counts'] = {ds: prep[ds]['check1'] for ds in args.datasets}
        manifest['items'] = {ds: prep[ds]['items'] for ds in args.datasets}
        manifest['flag_stats'] = {ds: prep[ds]['stats'] for ds in args.datasets}
        manifest['degenerate'] = {ds: prep[ds]['degenerate'] for ds in args.datasets}
        manifest['digest'] = {ds: prep[ds]['digest'] for ds in args.datasets}
        manifest['d6'] = {ds: prep[ds]['stats'][D6_NAME] for ds in args.datasets if ds in D6}
        manifest['expected_verdict_files'] = {p: manifest['hashed_inputs'].get(p) for p in (FROZEN_VERDICTS, ADDENDUM_VERDICTS)}
        write_atomic(os.path.join(out, 'dryrun.txt'), '\n'.join(dry) + '\n')
        if mode != 'dry_run':                                  # phase B: only after every check has passed
            for t in tasks:
                t['mode'] = mode
            resB = run_tasks(tasks, args.jobs, say)
            for rb in resB:
                ra = [r for r in resA if r['ds'] == rb['ds'] and r['seed'] == rb['seed']][0]
                if [s['train_hash'] for s in ra['summary']] != [s['train_hash'] for s in rb['summary']]:
                    raise Abort('determinism', 'DETERMINISM FAIL {} seed {}: phase B hashes differ'.format(rb['ds'], rb['seed']))
                check_lines += [x for x in rb['lines'] if x.startswith('check 2(train)')]
            for ds in args.datasets:
                wall[ds] += sum(r['elapsed_s'] for r in resB if r['ds'] == ds)
            manifest['convergence_warnings'] = {ds: {m: sum(r['conv'][m] for r in resB if r['ds'] == ds) for m in MODELS}
                                                for ds in args.datasets}
            manifest['reuse'] = {'{} seed {}'.format(r['ds'], r['seed']): r['reuse'] for r in resB}
            if mode == 'full':
                write_results(out, resB, args, say)
        manifest['wall_s'] = dict(wall, total=time.time() - t_start)   # per dataset: summed task seconds
        manifest['status'] = 'ok'
        write_atomic(os.path.join(out, 'checks.txt'), '\n'.join(check_lines) + '\n')
        say('DONE {} {} datasets, {} seeds, {:.0f} s'.format(mode, len(args.datasets), len(args.seeds), time.time() - t_start))
        code = 0
    except Abort as e:
        say(e.msg)
        manifest['status'] = 'failed'
        manifest['failure'] = e.msg
        write_atomic(os.path.join(out, 'checks.txt'), '\n'.join(check_lines + [e.msg]) + '\n')
        say('FAIL {} {}'.format(e.check, e.msg))
        code = 1
    except Exception as e:                                    # noqa: BLE001  R6, R57: any other failure is recorded too
        tb = traceback.format_exc()
        sys.stderr.write(tb)
        sys.stderr.flush()
        msg = 'unexpected {!r}'.format(e)
        manifest['status'] = 'failed'
        manifest['failure'] = msg
        manifest['traceback'] = tb
        write_atomic(os.path.join(out, 'checks.txt'), '\n'.join(check_lines + [msg]) + '\n')
        say('FAIL ' + msg)
        code = 1
    write_atomic(os.path.join(out, 'manifest.json'), json.dumps(manifest, indent=1, default=str, sort_keys=True))
    write_atomic(os.path.join(out, 'run.log'), '\n'.join(log) + '\n')
    return code


def prepare(ds, files, manifest_rows, add_mf, say):
    """Main process, before any version: load, schema checks, check 1, flag statistics, items, references, verdicts."""
    cfg, E = CFG[ds], EXPECT.get(ds, {})
    data, full, restricted = cached(ds, cfg, files)
    lines = []
    n_feat, n_num = len(data['feat_j']), len(data['num_j'])
    if E and (n_feat != E['features'] or n_num != E['numeric']):
        raise Abort('schema', 'SCHEMA FAIL {}: {} features ({} numeric), expected {} ({})'.format(
            ds, n_feat, n_num, E['features'], E['numeric']))
    n_train = len(split(data, 0)[0])
    if E and n_train != E['n_train']:
        raise Abort('schema', 'SCHEMA FAIL {}: n_train {} expected {}'.format(ds, n_train, E['n_train']))
    c1 = check1(ds, data, files, manifest_rows, full)
    lines.append('check 1 {} PASS (MANIFEST, sha256, Table 3, no duplicate or outside cell, replay identity)'.format(ds))
    stats = {k: flag_stats(data, full[k], restricted[k]) for k in full}
    items = make_items(restricted)
    npairs = len(items) * (len(items) - 1) // 2
    if E and (len(items), npairs) != (E['items'], E['pairs']):
        raise Abort('items', 'ITEMS FAIL {}: {} items / {} pairs, expected {} / {}'.format(ds, len(items), npairs, E['items'], E['pairs']))
    if ds in D6:
        s = stats[D6_NAME]
        got = (int((restricted[D6_NAME] & data['A']).sum()), int((restricted[D6_NAME] & ~data['A']).sum()))
        if got != D6[ds] or np.array_equal(restricted[D6_NAME], restricted['perfect']):
            raise Abort('d6', 'D6 FAIL {}: Raha minus format-only TP/FP {} (expected {}), equal to perfect: {}'.format(
                ds, got, D6[ds], np.array_equal(restricted[D6_NAME], restricted['perfect'])))
        lines.append('D6 {} PASS ({} = Raha minus {} format-only FPs: TP {} FP {}, not perfect)'.format(
            ds, D6_NAME, stats['raha']['format_only_fp'], s['tp'], s['fp']))
    ref = references(data, full, restricted, items)
    verdicts = expected_verdicts(ds, items, ref)
    add = compare_verdicts(ds, verdicts, ADDENDUM_VERDICTS, strict=True)
    if add and add[0] != add[1]:
        raise Abort('verdicts', 'VERDICT FAIL {} addendum match {}/{}: {}'.format(ds, add[0], add[1], '; '.join(add[2][:5])))
    frozen = compare_verdicts(ds, verdicts, FROZEN_VERDICTS, strict=False)
    cdu = {p: tuple(sum(1 for r in verdicts if r['policy'] == p and r['expected'] == k)
                    for k in ('concordant', 'discordant', 'undetermined')) for p in POLICIES}
    mf = add_mf.get(ds, {}).get('configs')
    if mf:                                                     # R62, per configuration
        keys = [('excl_col_flags', 'excl_col_flags'), ('format_only_fp', 'format_only_fp_schema'),
                ('flagged_label_cells', 'label_flags'),
                ('rows_touched_without_format_only', 'rows_touched_schema_without_format_only'),
                ('feature_tp_parsable', 'feature_tp_parsable')]
        for c in CONFIGS + EXTRA_SETS:
            for mine, theirs in keys:
                if stats[c][mine] != mf[c][theirs]:
                    raise Abort('r62', 'R62 FAIL {} {} {} = {}, addendum {} = {}'.format(ds, c, mine, stats[c][mine], theirs, mf[c][theirs]))
    item_of = {c: nm for nm, members in items for c in members}
    item_of.update({k: k for k in EXTRA_SETS + [D6_NAME]})
    return dict(data=data, stats=stats, items=items, ref=ref, verdicts=verdicts, cdu=cdu, check1=c1, item_of=item_of,
                addendum=add[:2] if add else None, check_lines=lines,
                addendum_text='{}/{}'.format(*add[:2]) if add else 'n/a (dataset not in the addendum)',
                frozen_text=str(len(frozen[2])) if frozen else 'n/a', has_mf=bool(mf))


def finish_dataset(ds, p, res, add_mf, args, say):
    """After phase A: R62 per seed, the degenerate list, the digest and the check lines."""
    for r in res:
        p['check_lines'] += r['lines']
    per = add_mf.get(ds, {}).get('per_seed')
    if per:
        for r in res:
            s = r['seed']
            if s >= len(per[CONFIGS[0]]['delete_schema']):
                continue
            for c in CONFIGS + EXTRA_SETS:
                got = r['r62'][c]
                want = dict(delete=per[c]['delete_schema'][s], impute=per[c]['impute'][s],
                            label_errors_left_impute=per[c]['label_errors_left_impute'][s])
                if got != want:
                    raise Abort('r62', 'R62 FAIL {} seed {} {}: driver {} addendum {}'.format(ds, s, c, got, want))
        p['check_lines'].append('R62 {} PASS (rows kept under delete/impute, label errors left, flag statistics = addendum)'.format(ds))
    p['degenerate'] = {}
    for r in res:
        for s in r['summary']:
            if s['degenerate']:
                p['degenerate'].setdefault(s['name'], []).append(r['seed'])
    p['digest'] = digest(res)


def run_tasks(tasks, jobs, say):
    t0 = time.time()
    if jobs == 1:
        out = []
        for t in tasks:
            out.append(run_seed(t))
            say('  {} seed {} {} ({:.1f} s)'.format(t['ds'], t['seed'], t['mode'], out[-1]['elapsed_s']))
    else:
        ctx = multiprocessing.get_context('spawn')            # R13: no fork after OpenMP has started
        with ctx.Pool(jobs) as pool:
            out = pool.map(run_seed, tasks, chunksize=1)
    say('  {} tasks ({}) in {:.1f} s'.format(len(tasks), tasks[0]['mode'] if tasks else '-', time.time() - t0))
    return out


def write_results(out, resB, args, say):
    """R63-R66: sorted rows, floats by repr(), row count asserted per dataset."""
    order = {name: i for i, (name, _, _) in enumerate(canonical_versions(True))}
    rows = [r for res in resB for r in res['rows']]
    for ds in args.datasets:
        P = len(args.policies)
        want = (1 + 3 + 21 * P + (3 * P if ds in D6 else 0) + (5 if 'delete' in args.policies else 0)) * len(MODELS) * len(args.seeds)
        got = sum(1 for r in rows if r['dataset'] == ds)
        if got != want:
            raise Abort('rows', 'ROWS FAIL {}: {} result rows, expected {}'.format(ds, got, want))
    ds_idx = {ds: i for i, ds in enumerate(DATASETS + sorted(set(CFG) - set(DATASETS)))}
    rows.sort(key=lambda r: (ds_idx[r['dataset']], order[r['version']], MODELS.index(r['model']), r['seed'], r['scenario']))
    with open(os.path.join(out, 'results.csv.tmp'), 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(RESULT_COLS)
        w.writerows([fmt_value(r.get(c, '')) for c in RESULT_COLS] for r in rows)
    os.replace(os.path.join(out, 'results.csv.tmp'), os.path.join(out, 'results.csv'))
    say('results.csv: {} rows'.format(len(rows)))


def selftest():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests', 'test_blockd.py')
    spec = importlib.util.spec_from_file_location('test_blockd', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_all('driver')


if __name__ == '__main__':
    sys.exit(main())
