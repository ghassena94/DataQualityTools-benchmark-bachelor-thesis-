"""Follow-up checks: (1) magnitude and cause of impute-vs-floor matrix differences and whether they change
model scores (Ridge/Logit, RF, XGB) in S2; (2) my adult HoloClean cell set vs the plan's replay (checks/measure_fixes.holo);
(3) per-seed label_errors_left comparison.
Run: docker exec -w /rein rein-benchmark-rein-1 python3 reports/block_d_final_plan_2026-10-09/fable/fable_check2.py
"""
import importlib.util
import math
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import f1_score, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor

warnings.filterwarnings('ignore')
sys.dont_write_bytecode = True
D = '/rein/datasets'
spec = importlib.util.spec_from_file_location('fm', '/rein/reports/block_d_final_plan_2026-10-09/fable/fable_measure.py')
src = open(spec.origin).read().split('report = {}')[0]
ns = {}
exec(compile(src, spec.origin, 'exec'), ns)
load, fnum, isnum, ge_real, holo_own, read_cells, prof, HW, CFG = (ns[k] for k in ['load', 'fnum', 'isnum', 'ge_real', 'holo_own', 'read_cells', 'prof', 'HW', 'CFG'])

# ---------- (2) adult HoloClean: my cells vs the plan's replay
spec2 = importlib.util.spec_from_file_location('mf', '/rein/reports/block_d_final_plan_2026-10-09/checks/measure_fixes.py')
src2 = open(spec2.origin).read().split('report = {}')[0]
ns2 = {}
exec(compile(src2, spec2.origin, 'exec'), ns2)
for ds in ('adult', 'breast_cancer'):
    clean, dirty = load(ds)
    mine, _ = holo_own(dirty, ds)
    theirs = ns2['holo'](dirty, ds)
    print('%s holoclean: mine %d cells, plan replay %d cells, identical: %s, sym-diff %d' % (ds, len(mine), len(theirs), mine == theirs, len(mine ^ theirs)))

# ---------- (1) impute vs floor: magnitude, and model scores
def build(dirty_vals, rows, flagged=None):
    X = np.full((len(rows), dirty_vals.shape[1]), np.nan)
    pos = {r: i for i, r in enumerate(rows)}
    for j in range(dirty_vals.shape[1]):
        col = np.array([np.nan if fnum(dirty_vals[r, j]) is None else fnum(dirty_vals[r, j]) for r in rows])
        if flagged is not None:
            fl_idx = [pos[r] for (r, jj) in flagged if jj == j and r in pos]
            if fl_idx:
                mask = np.ones(len(rows), bool)
                mask[fl_idx] = False
                good = col[mask]
                good = good[~np.isnan(good)]
                col[fl_idx] = good.mean() if len(good) else 0.0
        X[:, j] = col
    means = np.nanmean(X, axis=0)
    return X, means


def fill(X, means):
    X = X.copy()
    for j in range(X.shape[1]):
        X[np.isnan(X[:, j]), j] = means[j]
    return X


for ds in ('nasa', 'breast_cancer'):
    cfg = CFG[ds]
    clean, dirty = load(ds)
    cols = list(dirty.columns)
    n = len(dirty)
    lab = cols.index(cfg['label'])
    excl = {cols.index(c) for c in cfg['excl']}
    feat = sorted(set(range(len(cols))) - excl - {lab})
    fmap = {j: k for k, j in enumerate(feat)}
    A = read_cells('{}/{}/actual_errors.csv'.format(D, ds))
    e_dirty, e_clean = prof.profile_expectations(dirty), prof.profile_expectations(clean)
    sets = {'ge_dirty_profiled': ge_real(dirty, e_dirty), 'ge_clean_profiled': ge_real(dirty, e_clean)}
    dv, cv = dirty.values[:, feat], clean.values[:, feat]
    y_clean = clean[cfg['label']].values
    if cfg['task'] == 'clf':
        y_all = (y_clean == cfg['pos']).astype(int)
        y_dirty = (dirty[cfg['label']].values == cfg['pos']).astype(int)
    else:
        y_all = y_clean.astype(float)
        y_dirty = np.array([fnum(v) for v in dirty[cfg['label']].values], float)
    for c, fl in sets.items():
        flagged = {(i, fmap[j]) for (i, j) in fl if j in fmap}
        fp = fl - A
        print('\n%s %s: %d flags, %d FP; FP cells by column %s; FP values %s' % (
            ds, c, len(fl), len(fp), {cols[j]: sum(1 for (_, jj) in fp if jj == j) for j in set(jj for _, jj in fp)},
            sorted({dirty.iat[i, j] for (i, j) in fp})[:8]))
        for seed in range(10):
            tr, te = train_test_split(np.arange(n), test_size=0.2, random_state=seed, stratify=y_all if cfg['task'] == 'clf' else None)
            tr, te = sorted(int(x) for x in tr), sorted(int(x) for x in te)
            X0, m0 = build(dv, tr)
            X1, m1 = build(dv, tr, flagged)
            F0, F1 = fill(X0, m0), fill(X1, m1)
            diff = np.abs(F0 - F1)
            nd = int((diff > 0).sum())
            maxd = float(diff.max())
            # S2: clean test rows featurized with the version's means
            Xt = np.array([[np.nan if fnum(cv[r, j]) is None else fnum(cv[r, j]) for j in range(len(feat))] for r in te])
            T0, T1 = fill(Xt, m0), fill(Xt, m1)
            ytr, yte = y_dirty[tr], y_all[te]
            out = []
            for name in ('linear', 'rf', 'xgb'):
                if cfg['task'] == 'clf':
                    mk = {'linear': lambda: LogisticRegression(max_iter=5000, random_state=0), 'rf': lambda: RandomForestClassifier(random_state=0, n_jobs=1),
                          'xgb': lambda: XGBClassifier(use_label_encoder=False, eval_metric='logloss', verbosity=0, random_state=0, n_jobs=1)}[name]
                    sc = lambda yt, yp: f1_score(yt, yp)
                else:
                    mk = {'linear': lambda: Ridge(random_state=0), 'rf': lambda: RandomForestRegressor(random_state=0, n_jobs=1),
                          'xgb': lambda: XGBRegressor(verbosity=0, random_state=0, n_jobs=1)}[name]
                    sc = lambda yt, yp: -math.sqrt(mean_squared_error(yt, yp))
                s = []
                for Ftr, Fte in ((F0, T0), (F1, T1)):
                    if name == 'linear':
                        ss = StandardScaler().fit(Ftr)
                        Ftr, Fte = ss.transform(Ftr), ss.transform(Fte)
                    m = mk().fit(Ftr, ytr)
                    s.append(sc(yte, m.predict(Fte)))
                out.append('%s d=%.3e' % (name, s[1] - s[0]))
            print('  seed %d: cells differing %3d, max|diff| %.3e | S2 score(impute) - S2 score(floor): %s' % (seed, nd, maxd, '  '.join(out)))
