"""Minimal Block D driver for the D2-D8 decision experiments (not the real driver).

Builds the training version of an item under a policy, featurizes it as plan section 2, trains the
three models and scores S2 on the clean test split. Options exposed so the decisions can be compared:
  model_seed ('fixed' -> random_state=0, 'split' -> random_state=split seed)      D3
  numeric_rule ('90' -> >=90 % of clean values parse, 'all' -> every value)         D4
  fill ('mean' | 'median') for featurization and impute                            D5
Impute statistics come from the kept training rows (D2, decided 9 Oct).
Imported by the d3..d8 scripts; run them inside the rein container.
"""
import sys
sys.dont_write_bytecode = True
import hashlib, itertools, math, warnings
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
D, CFG, CONFIGS, isnum = ns['D'], ns['CFG'], ns['CONFIGS'], ns['isnum']
SHORT = dict(ge_dirty_profiled='GE-dirty', ge_clean_profiled='GE-clean', ge_hand_written='GE-hand', holoclean='HoloClean', raha='Raha')


def num(s):
    return pd.to_numeric(s.where(s.map(isnum)), errors='coerce')


class Data:
    def __init__(self, ds, numeric_rule='90'):
        cfg = self.cfg = CFG[ds]; self.ds = ds
        self.clean = pd.read_csv('{}/{}/clean.csv'.format(D, ds), dtype=str, keep_default_na=False)
        self.dirty = pd.read_csv('{}/{}/dirty.csv'.format(D, ds), dtype=str, keep_default_na=False)
        self.A = ns['read_cells']('{}/{}/actual_errors.csv'.format(D, ds))
        self.cols = list(self.dirty.columns); self.lab = cfg['label']
        excl = set(cfg['excl'])
        self.feats = [c for c in self.cols if c not in excl and c != self.lab]
        share = {c: self.clean[c].map(isnum).mean() for c in self.feats}
        self.numeric = [c for c in self.feats if share[c] >= (0.9 if numeric_rule == '90' else 1.0)]
        self.cat = [c for c in self.feats if c not in self.numeric]
        self.clf = cfg['task'] == 'clf'
        self.y_clean = self._y(self.clean[self.lab])
        model_cols = {self.cols.index(c) for c in self.feats + [self.lab]}
        F = {'ge_dirty_profiled': ns['ge'](self.dirty, ns['prof'].profile_expectations(self.dirty)),
             'ge_clean_profiled': ns['ge'](self.dirty, ns['prof'].profile_expectations(self.clean)),
             'ge_hand_written': ns['ge'](self.dirty, ns['hw'].get(ds, {}).get('hand_written', [])),
             'holoclean': ns['holo'](self.dirty, ds),
             'raha': ns['read_cells']('{}/{}/raha/detections.csv'.format(D, ds))}
        self.F = {c: {(i, j) for i, j in s if j in model_cols} for c, s in F.items()}
        self.perfect = {(i, j) for i, j in self.A if j in model_cols}
        groups = {}
        for c in CONFIGS:
            groups.setdefault(frozenset(self.F[c]), []).append(c)
        self.items = {'='.join(SHORT[c] for c in g): self.F[g[0]] for g in groups.values()}

    def _y(self, s):
        return (s == self.cfg['pos']).astype(int).values if self.clf else pd.to_numeric(s, errors='coerce').values

    def split(self, seed):
        tr, te = train_test_split(np.arange(len(self.dirty)), test_size=0.2, random_state=seed,
                                  stratify=self.y_clean if self.clf else None)
        return np.sort(tr), np.sort(te)

    def version(self, flags, policy, tr, fill='mean'):
        """Training rows (string frame of features) and labels of one version; flags already model columns."""
        by_col = {c: set() for c in self.cols}
        for i, j in flags:
            by_col[self.cols[j]].add(i)
        lab = self.lab
        if policy == 'floor':
            kept = tr
        elif policy == 'delete':
            bad = set().union(*by_col.values())
            kept = np.array([i for i in tr if i not in bad], dtype=int)
        elif policy in ('impute', 'gt'):
            kept = np.array([i for i in tr if i not in by_col[lab]], dtype=int) if policy == 'impute' else tr
        X = self.dirty.loc[kept, self.feats].copy()
        y_raw = self.dirty.loc[kept, lab].copy()
        if policy == 'gt':
            for c in self.feats + [lab]:
                rows = [i for i in kept if i in by_col[c]]
                if c == lab:
                    y_raw.loc[rows] = self.clean.loc[rows, lab]
                else:
                    X.loc[rows, c] = self.clean.loc[rows, c]
        elif policy == 'impute':
            keptset = set(kept)
            for c in self.feats:
                fr = [i for i in kept if i in by_col[c]]
                if not fr:
                    continue
                pool = self.dirty.loc[[i for i in kept if i not in by_col[c]], c]
                if c in self.numeric:
                    v = num(pool).dropna()
                    X.loc[fr, c] = repr(float(v.mean() if fill == 'mean' else v.median())) if len(v) else '0.0'
                else:
                    m = pool.mode()
                    X.loc[fr, c] = m.iloc[0] if len(m) else '__none__'
        return X, self._y(y_raw), kept

    def featurize(self, X, te, fill='mean'):
        Xn = X[self.numeric].apply(num)
        mu = Xn.mean() if fill == 'mean' else Xn.median()
        mu = mu.fillna(0.0)
        Xn = Xn.fillna(mu)
        Tn = self.clean.loc[te, self.numeric].apply(num).fillna(mu)
        parts, tparts = [Xn.values.astype(float)], [Tn.values.astype(float)]
        if self.cat:
            oh = OneHotEncoder(handle_unknown='ignore', sparse=False).fit(X[self.cat])
            parts.append(oh.transform(X[self.cat])); tparts.append(oh.transform(self.clean.loc[te, self.cat]))
        return np.hstack(parts), np.hstack(tparts)


def train_hash(Xtr, ytr):
    r = np.array([float('%.12g' % v) for v in Xtr.ravel()]) if Xtr.size else np.array([])
    return hashlib.sha256(r.tobytes() + np.asarray(ytr, dtype=float).tobytes()).hexdigest()[:16]


def models(clf, rs):
    if clf:
        return [('linear', LogisticRegression(max_iter=5000), True), ('rf', RandomForestClassifier(random_state=rs, n_jobs=1), False),
                ('xgb', XGBClassifier(random_state=rs, n_jobs=1, use_label_encoder=False, eval_metric='logloss', verbosity=0), False)]
    return [('linear', Ridge(), True), ('rf', RandomForestRegressor(random_state=rs, n_jobs=1), False),
            ('xgb', XGBRegressor(random_state=rs, n_jobs=1, verbosity=0), False)]


def s2(data, flags, policy, seed, model_seed='fixed', fill='mean', which=('linear', 'rf', 'xgb')):
    """S2 per model (oriented: F1, or -RMSE); None if degenerate. Also returns rows kept and the hash."""
    tr, te = data.split(seed)
    X, ytr, kept = data.version(flags, policy, tr, fill)
    if len(kept) < 50 or (data.clf and len(set(ytr)) < 2) or np.isnan(ytr).any():
        return {m: None for m in which}, len(kept), None
    Xtr, Xte = data.featurize(X, te, fill)
    yte = data.y_clean[te]
    sc = StandardScaler().fit(Xtr)
    out = {}
    for name, m, scale in models(data.clf, 0 if model_seed == 'fixed' else seed):
        if name not in which:
            continue
        m.fit(sc.transform(Xtr) if scale else Xtr, ytr)
        p = m.predict(sc.transform(Xte) if scale else Xte)
        out[name] = f1_score(yte, p) if data.clf else -math.sqrt(mean_squared_error(yte, p))
    return out, len(kept), train_hash(Xtr, ytr)


def signflip_p(d):
    a = np.abs(d)
    order = a.argsort(); ranks = np.empty(len(a))
    ranks[order] = np.arange(1, len(a) + 1)
    for v in np.unique(a):                       # midranks
        ranks[a == v] = ranks[a == v].mean()
    T = abs(np.sum(np.sign(d) * ranks))
    hits = sum(1 for s in itertools.product((-1, 1), repeat=len(d)) if abs(np.dot(s, ranks)) >= T - 1e-12)
    return hits / 2 ** len(d)


def verdict(sa, sb, ha=None, hb=None):
    """Pair rule of plan 8.2 on per-seed oriented scores; '>' means a better than b."""
    if ha is not None and list(ha) == list(hb):         # same rounded training data on every seed
        return 'tie'
    d = np.array(sa) - np.array(sb)
    d[np.abs(d) < 1e-9] = 0
    d = d[d != 0]
    if len(d) <= 5:
        return 'tie'
    return ('>' if np.median(d) > 0 or (np.median(d) == 0 and d.sum() > 0) else '<') if signflip_p(d) < 0.05 else 'tie'
