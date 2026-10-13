"""Does per-version hyperparameter tuning change the downstream ranking of detectors?

Read-only example for the Block D plan. Reads /rein/rein-datasets/<ds>/{clean,dirty,actual_errors}.csv
and <ds>/<detector>/detections.csv, writes nothing; prints a JSON summary to stdout.

Policy: mean/mode impute on flagged feature cells, rows with a flagged label dropped (labels never imputed).
Scenario: S2 = train on the repaired training split, test on the clean test split.
Arms:
  default   - library defaults, fixed random_state
  own_s0/1  - RandomizedSearchCV on the version's own training split (what a practitioner can do),
              two different search seeds on the same data
  gt        - REIN style: search on the CLEAN training split, then refit those params on each version
"""
import json, sys, time, warnings
import numpy as np, pandas as pd
from sklearn.model_selection import train_test_split, RandomizedSearchCV, KFold, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import f1_score, mean_squared_error
from xgboost import XGBClassifier, XGBRegressor

warnings.filterwarnings("ignore")
ROOT = "/rein/rein-datasets"
N_SPLITS, N_ITER, CV = 10, 10, 3

DATASETS = {
    "breast_cancer": dict(label="class", task="clf", drop=["", "Sample code number"],
                          detectors=["greatExpectations", "raha", "holoclean"]),
    "nasa": dict(label="sound_pressure_level", task="reg", drop=[],
                 detectors=["greatExpectations", "raha", "holoclean"]),
}
NAMES = {"greatExpectations": "GE_hand_written", "raha": "Raha", "holoclean": "HoloClean"}


def load(ds, cfg):
    clean = pd.read_csv(f"{ROOT}/{ds}/clean.csv", dtype=str, keep_default_na=False)
    dirty = pd.read_csv(f"{ROOT}/{ds}/dirty.csv", dtype=str, keep_default_na=False)
    clean.columns = ["" if c.startswith("Unnamed") else c for c in clean.columns]
    dirty.columns = clean.columns
    flags = {"no_detection": set()}
    ae = pd.read_csv(f"{ROOT}/{ds}/actual_errors.csv", header=None, dtype=str)
    flags["perfect"] = set(zip(ae[0].astype(int), ae[1].astype(int)))
    for d in cfg["detectors"]:
        det = pd.read_csv(f"{ROOT}/{ds}/{d}/detections.csv", header=None, dtype=str)
        flags[NAMES[d]] = set(zip(det[0].astype(int), det[1].astype(int)))
    return clean, dirty, flags


def repair_impute(dirty, flagged, train_idx, label_col, feat_cols, cols):
    """Mean impute flagged feature cells (stats from unflagged train cells); drop rows with a flagged label."""
    li = cols.index(label_col)
    X = dirty[feat_cols].apply(pd.to_numeric, errors="coerce")  # unparsable -> NaN (featurization)
    mask = pd.DataFrame(False, index=dirty.index, columns=feat_cols)
    for r, c in flagged:
        if c != li and cols[c] in feat_cols:
            mask.iat[r, feat_cols.index(cols[c])] = True
    tr = X.loc[train_idx]
    means = tr.where(~mask.loc[train_idx]).mean()
    X = X.where(~mask, other=np.nan).fillna(means)  # flagged -> train mean; leftover NaN -> train mean too
    # a column whose every training value is flagged has no mean: it carries no information, so it becomes constant
    X = X.fillna(0.0)
    label_flagged = {r for r, c in flagged if c == li}
    keep = [i for i in train_idx if i not in label_flagged]
    return X, keep


def models(task):
    if task == "clf":
        return {
            "linear": (lambda rs: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=rs)),
                       {"logisticregression__C": [0.01, 0.1, 1, 10, 100]}),
            "RF": (lambda rs: RandomForestClassifier(random_state=rs, n_jobs=1),
                   {"n_estimators": [100, 200, 400], "max_depth": [None, 4, 8, 16],
                    "min_samples_leaf": [1, 2, 5, 10], "max_features": ["sqrt", 0.5, None]}),
            "XGB": (lambda rs: XGBClassifier(random_state=rs, n_jobs=1, use_label_encoder=False,
                                             eval_metric="logloss", verbosity=0),
                    {"n_estimators": [100, 200, 400], "max_depth": [3, 6, 9],
                     "learning_rate": [0.03, 0.1, 0.3], "subsample": [0.7, 1.0], "colsample_bytree": [0.7, 1.0]}),
        }
    return {
        "linear": (lambda rs: make_pipeline(StandardScaler(), Ridge(random_state=rs)),
                   {"ridge__alpha": [0.01, 0.1, 1, 10, 100]}),
        "RF": (lambda rs: RandomForestRegressor(random_state=rs, n_jobs=1),
               {"n_estimators": [100, 200, 400], "max_depth": [None, 4, 8, 16],
                "min_samples_leaf": [1, 2, 5, 10], "max_features": ["sqrt", 0.5, None]}),
        "XGB": (lambda rs: XGBRegressor(random_state=rs, n_jobs=1, verbosity=0),
                {"n_estimators": [100, 200, 400], "max_depth": [3, 6, 9],
                 "learning_rate": [0.03, 0.1, 0.3], "subsample": [0.7, 1.0], "colsample_bytree": [0.7, 1.0]}),
    }


def score(task, y, p):
    return f1_score(y, p, pos_label=1) if task == "clf" else float(np.sqrt(mean_squared_error(y, p)))


def search(task, make, space, X, y, seed):
    cv = StratifiedKFold(CV, shuffle=True, random_state=seed) if task == "clf" else KFold(CV, shuffle=True, random_state=seed)
    sc = "f1" if task == "clf" else "neg_root_mean_squared_error"
    rs = RandomizedSearchCV(make(0), space, n_iter=N_ITER, cv=cv, scoring=sc, random_state=seed, n_jobs=10, refit=False)
    rs.fit(X, y)
    return rs.best_params_


def run(ds, cfg):
    clean, dirty, flags = load(ds, cfg)
    cols = list(clean.columns)
    label = cfg["label"]
    feat = [c for c in cols if c != label and c not in cfg["drop"]]
    task = cfg["task"]
    Xc = clean[feat].apply(pd.to_numeric, errors="coerce")
    if task == "clf":
        y = (clean[label].astype(float) == 4).astype(int).values  # malignant = 1
    else:
        y = clean[label].astype(float).values
    out = {}
    for mname, (make, space) in models(task).items():
        rec = []  # rows: split, version, arm, score
        for s in range(N_SPLITS):
            idx = np.arange(len(clean))
            tr, te = train_test_split(idx, test_size=0.2, random_state=s, stratify=y if task == "clf" else None)
            Xte = Xc.iloc[te].fillna(Xc.iloc[tr].mean())
            # REIN-style params: tuned once on the clean training split
            gt_params = search(task, make, space, Xc.iloc[tr].fillna(Xc.iloc[tr].mean()), y[tr], seed=100 + s)
            for v, fl in flags.items():
                X, keep = repair_impute(dirty, fl, list(tr), label, feat, cols)
                if len(keep) < 50 or (task == "clf" and len(set(y[keep])) < 2):
                    for arm in ["default", "own_s0", "own_s1", "gt"]:
                        rec.append((s, v, arm, None, len(keep)))
                    continue
                Xtr, ytr = X.iloc[keep], y[keep]  # labels: dirty labels kept unless flagged -> use dirty label
                ytr = labels_dirty(dirty, label, task)[keep]
                m = make(0); m.fit(Xtr, ytr); rec.append((s, v, "default", score(task, y[te], m.predict(Xte)), len(keep)))
                for k, seed in (("own_s0", 1000 + s), ("own_s1", 2000 + s)):
                    p = search(task, make, space, Xtr, ytr, seed)
                    m = make(0); m.set_params(**p); m.fit(Xtr, ytr)
                    rec.append((s, v, k, score(task, y[te], m.predict(Xte)), len(keep)))
                m = make(0); m.set_params(**gt_params); m.fit(Xtr, ytr)
                rec.append((s, v, "gt", score(task, y[te], m.predict(Xte)), len(keep)))
            print(f"{ds} {mname} split {s} done", file=sys.stderr, flush=True)
        out[mname] = rec
    return out


_LAB = {}
def labels_dirty(dirty, label, task):
    key = (id(dirty), label)
    if key not in _LAB:
        v = pd.to_numeric(dirty[label], errors="coerce")
        if task == "clf":
            _LAB[key] = (v == 4).astype(int).values
        else:
            _LAB[key] = v.fillna(v.mean()).values
    return _LAB[key]



# ---- Full-grid check: how good is the winner of a 10-draw random search on this data? ----
from sklearn.model_selection import ParameterGrid
from joblib import Parallel, delayed
ds, cfg = "nasa", DATASETS["nasa"]
clean, dirty, flags = load(ds, cfg)
cols = list(clean.columns); label = cfg["label"]
feat = [c for c in cols if c != label and c not in cfg["drop"]]
Xc = clean[feat].apply(pd.to_numeric, errors="coerce"); y = clean[label].astype(float).values
make, space = models("reg")["RF"]
grid = list(ParameterGrid(space))
DEFAULT = {"n_estimators": 100, "max_depth": None, "min_samples_leaf": 1, "max_features": None}
d_idx = grid.index(DEFAULT)

def eval_combo(p, Xtr, ytr, Xte, yte, folds):
    cv = []
    for a, b in folds:
        m = make(0); m.set_params(**p); m.fit(Xtr.iloc[a], ytr[a])
        cv.append(np.sqrt(mean_squared_error(ytr[b], m.predict(Xtr.iloc[b]))))
    m = make(0); m.set_params(**p); m.fit(Xtr, ytr)
    return float(np.mean(cv)), float(np.sqrt(mean_squared_error(yte, m.predict(Xte))))

out = {"n_grid": len(grid), "default_index": d_idx, "rows": []}
rng = np.random.RandomState(12345)
for v in ["no_detection", "perfect", "GE_hand_written", "HoloClean"]:
    for s in range(5):
        idx = np.arange(len(clean)); tr, te = train_test_split(idx, test_size=0.2, random_state=s)
        X, keep = repair_impute(dirty, flags[v], list(tr), label, feat, cols)
        Xtr = X.iloc[keep].reset_index(drop=True); ytr = labels_dirty(dirty, label, "reg")[keep]
        Xte = Xc.iloc[te].fillna(Xc.iloc[tr].mean()); yte = y[te]
        folds = list(KFold(3, shuffle=True, random_state=0).split(Xtr))
        res = Parallel(n_jobs=10)(delayed(eval_combo)(p, Xtr, ytr, Xte, yte, folds) for p in grid)
        cvs = np.array([r[0] for r in res]); tests = np.array([r[1] for r in res])
        # simulate 2000 random searches of 10 draws (without replacement) on the same CV table
        wins = []
        for _ in range(2000):
            pick = rng.choice(len(grid), 10, replace=False)
            w = pick[np.argmin(cvs[pick])]
            wins.append((tests[w], int((cvs < cvs[w]).sum()), bool(d_idx in pick)))
        wt = np.array([w[0] for w in wins]); wr = np.array([w[1] for w in wins]); has_def = np.array([w[2] for w in wins])
        top5 = np.argsort(cvs)[: int(round(0.05 * len(grid)))]
        out["rows"].append({
            "version": v, "split": s,
            "default_test": tests[d_idx], "default_cv_rank": int((cvs < cvs[d_idx]).sum()),
            "gridbest_by_cv_test": float(tests[np.argmin(cvs)]), "oracle_best_test": float(tests.min()),
            "search10_test_mean": float(wt.mean()), "search10_test_p10": float(np.percentile(wt, 10)), "search10_test_p90": float(np.percentile(wt, 90)),
            "search10_beats_default_share": float((wt < tests[d_idx]).mean()),
            "search10_winner_cv_rank_mean": float(wr.mean()),
            "search10_contains_top5pct_share": float(np.mean([np.intersect1d(rng.choice(len(grid), 10, replace=False), top5).size > 0 for _ in range(2000)])),
            "search10_contains_default_share": float(has_def.mean()),
        })
        print(v, s, "done", file=sys.stderr, flush=True)
print(json.dumps(out))
