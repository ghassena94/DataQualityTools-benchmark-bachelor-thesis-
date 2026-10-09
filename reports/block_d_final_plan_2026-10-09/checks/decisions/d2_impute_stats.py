"""D2: impute statistics over the KEPT training rows vs ALL training rows.
Only differs where a flagged label drops rows under impute. Train the real models both ways.
Run: docker exec -i rein-benchmark-rein-1 python3 - [adult] < d2_impute_stats.py
"""
import math, sys, warnings
import numpy as np, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.metrics import f1_score, mean_squared_error
from xgboost import XGBClassifier, XGBRegressor
warnings.filterwarnings('ignore'); sys.dont_write_bytecode = True
SRC = '/rein/reports/block_d_final_plan_2026-10-09/checks/measure_fixes.py'
ns = {}
exec(compile(open(SRC).read().split('report = {}')[0], SRC, 'exec'), ns)
D, CFG, isnum = ns['D'], ns['CFG'], ns['isnum']


def num(s):
    return pd.to_numeric(s.where(s.map(isnum)), errors='coerce')


def run(ds, conf, show_seed=0):
    cfg = CFG[ds]
    clean = pd.read_csv('{}/{}/clean.csv'.format(D, ds), dtype=str, keep_default_na=False)
    dirty = pd.read_csv('{}/{}/dirty.csv'.format(D, ds), dtype=str, keep_default_na=False)
    A = ns['read_cells']('{}/{}/actual_errors.csv'.format(D, ds))
    cols = list(dirty.columns); lab = cfg['label']; j_lab = cols.index(lab)
    excl = set(cfg['excl']); feats = [c for c in cols if c not in excl and c != lab]
    numeric = [c for c in feats if clean[c].map(isnum).mean() >= 0.9]
    cat = [c for c in feats if c not in numeric]
    fl = ns['holo'](dirty, ds) if conf == 'holoclean' else set(A)
    fl = {(i, j) for i, j in fl if cols[j] not in excl}
    flagged = {c: set() for c in cols}
    for i, j in fl:
        flagged[cols[j]].add(i)
    clf = cfg['task'] == 'clf'
    y_clean = (clean[lab] == cfg['pos']).astype(int).values if clf else clean[lab].astype(float).values
    y_dirty = (dirty[lab] == cfg['pos']).astype(int).values if clf else pd.to_numeric(dirty[lab], errors='coerce').values
    res = {'kept': [], 'all': []}
    for seed in range(10):
        tr, te = train_test_split(np.arange(len(dirty)), test_size=0.2, random_state=seed, stratify=y_clean if clf else None)
        tr = np.sort(tr); te = np.sort(te)
        kept = np.array([i for i in tr if i not in flagged[lab]])
        for mode in ('kept', 'all'):
            base = kept if mode == 'kept' else tr
            X = dirty.loc[kept, feats].copy()
            for c in feats:
                fr = [i for i in kept if i in flagged[c]]
                if not fr:
                    continue
                pool = dirty.loc[[i for i in base if i not in flagged[c]], c]
                if c in numeric:
                    v = num(pool).dropna()
                    if seed == show_seed and mode == 'kept':
                        res.setdefault('pool', []).append((c, len(num(dirty.loc[[i for i in kept if i not in flagged[c]], c]).dropna()), len(v if mode == 'all' else num(dirty.loc[[i for i in tr if i not in flagged[c]], c]).dropna())))
                    X.loc[fr, c] = repr(float(v.mean())) if len(v) else '0.0'
                else:
                    X.loc[fr, c] = pool.mode().iloc[0] if len(pool.mode()) else '__none__'
                if seed == show_seed:
                    if c in numeric:
                        a = num(dirty.loc[[i for i in kept if i not in flagged[c]], c]).dropna().mean()
                        b = num(dirty.loc[[i for i in tr if i not in flagged[c]], c]).dropna().mean()
                        tru = num(clean.loc[tr, c]).dropna().mean()
                    else:
                        ma = dirty.loc[[i for i in kept if i not in flagged[c]], c].mode()
                        mb = dirty.loc[[i for i in tr if i not in flagged[c]], c].mode()
                        a = ma.iloc[0] if len(ma) else '(no unflagged value)'
                        b = mb.iloc[0] if len(mb) else '(no unflagged value)'
                        tru = clean.loc[tr, c].mode().iloc[0]
                    if mode == 'kept':
                        res.setdefault('cols', []).append((c, len(fr), a, b, tru))
            # featurize: fitted on the kept rows
            Xn = X[numeric].apply(num); mu = Xn.mean(); Xn = Xn.fillna(mu)
            Tn = clean.loc[te, numeric].apply(num).fillna(mu)
            parts, tparts = [Xn.values], [Tn.values]
            if cat:
                oh = OneHotEncoder(handle_unknown='ignore', sparse=False).fit(X[cat])
                parts.append(oh.transform(X[cat])); tparts.append(oh.transform(clean.loc[te, cat]))
            Xtr, Xte = np.hstack(parts), np.hstack(tparts)
            ytr, yte = y_dirty[kept], y_clean[te]
            sc = StandardScaler().fit(Xtr)
            models = ([('linear', LogisticRegression(max_iter=5000), True), ('rf', RandomForestClassifier(random_state=0, n_jobs=1), False),
                       ('xgb', XGBClassifier(random_state=0, n_jobs=1, use_label_encoder=False, eval_metric='logloss', verbosity=0), False)] if clf else
                      [('linear', Ridge(), True), ('rf', RandomForestRegressor(random_state=0, n_jobs=1), False),
                       ('xgb', XGBRegressor(random_state=0, n_jobs=1, verbosity=0), False)])
            row = {}
            for name, m, scale in models:
                m.fit(sc.transform(Xtr) if scale else Xtr, ytr)
                p = m.predict(sc.transform(Xte) if scale else Xte)
                row[name] = f1_score(yte, p) if clf else math.sqrt(mean_squared_error(yte, p))
            res[mode].append(row)
        if seed == 0:
            res['rows'] = (len(tr), len(kept))
    print('\n==== %s %s | seed 0: %d training rows, %d kept (label flagged on the rest)' % (ds, conf, *res['rows']))
    print('  seed 0 fill values for flagged feature cells:')
    print('  %-16s %7s  %-22s %-22s %-22s' % ('column', 'filled', 'kept rows (proposal)', 'all train rows (alt)', 'clean value (truth)'))
    for c, k, a, b, t in res['cols']:
        f = (lambda v: '%.6g' % v) if c in numeric else str
        print('  %-16s %7d  %-22s %-22s %-22s' % (c, k, f(a), f(b), f(t)))
    score = 'minority F1 (higher better)' if clf else 'RMSE (lower better)'
    if 'pool' in res:
        print('  seed 0 unflagged parsable values the mean is taken from (kept rows / all rows):', res['pool'])
    print('  S2 %s, mean over 10 seeds:' % score)
    for name in ('linear', 'rf', 'xgb'):
        k = np.array([r[name] for r in res['kept']]); a = np.array([r[name] for r in res['all']])
        print('    %-6s kept %.4f   all %.4f   diff %+.4f   seeds identical %d/10   max |diff| %.4f' % (
            name, k.mean(), a.mean(), (a - k).mean(), int((np.abs(a - k) < 1e-9).sum()), np.abs(a - k).max()))


import sys as _s
for ds, conf in ((('adult', 'holoclean'),) if 'adult' in _s.argv else (('nasa', 'holoclean'), ('breast_cancer', 'perfect'))):
    run(ds, conf)
