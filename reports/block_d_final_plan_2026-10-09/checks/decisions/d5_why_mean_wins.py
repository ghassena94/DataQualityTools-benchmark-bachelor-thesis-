"""D5 follow-up: why does the polluted mean beat the median on the nasa floor for trees?
Hypothesis: the polluted mean puts unparsable cells far outside the normal range, so trees can split them off
(a 'missing' marker). Test: fill with mean / median / a far-away constant (1e12) / median + a missing-indicator column.
Run: docker exec -w /rein/reports/block_d_final_plan_2026-10-09/checks/decisions rein-benchmark-rein-1 python3 d5_why_mean_wins.py
"""
import math, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from xgboost import XGBRegressor
from mini_driver import Data, num

data = Data('nasa')
tr0, _ = data.split(0)
Xd = data.dirty.loc[tr0, data.numeric].apply(num)
row = Xd[Xd['thickness'].isna()].index[0]
print('example training row %d (split 0), dirty text:' % row, data.dirty.loc[row, data.numeric].to_dict())
print('   clean:', data.clean.loc[row, data.numeric].to_dict())
print('   thickness filled with mean %.4g | median %.4g | clean value %s' % (Xd['thickness'].mean(), Xd['thickness'].median(), data.clean.loc[row, 'thickness']))
res = {}
for seed in range(10):
    tr, te = data.split(seed)
    X = data.dirty.loc[tr, data.numeric].apply(num); y = num(data.dirty.loc[tr, data.lab]).values
    T = data.clean.loc[te, data.numeric].apply(num); yt = data.y_clean[te]
    for name, fx in (('mean', lambda X: X.fillna(X.mean())), ('median', lambda X: X.fillna(X.median())),
                     ('1e12', lambda X: X.fillna(1e12)),
                     ('median+indicator', lambda X: pd.concat([X.fillna(X.median()), X.isna().astype(float).add_suffix('_na')], axis=1))):
        Xf = fx(X); Tf = T.copy()
        if name == 'median+indicator':
            Tf = pd.concat([T, T.isna().astype(float).add_suffix('_na')], axis=1)
        for mname, m in (('rf', RandomForestRegressor(random_state=0, n_jobs=1)), ('xgb', XGBRegressor(random_state=0, n_jobs=1, verbosity=0))):
            m.fit(Xf.values, y)
            res.setdefault((name, mname), []).append(math.sqrt(mean_squared_error(yt, m.predict(Tf.values))))
print('\nnasa floor (dirty as shipped), S2 RMSE over 10 seeds (lower better):')
for name in ('mean', 'median', '1e12', 'median+indicator'):
    print('  fill %-17s rf %.4f   xgb %.4f' % (name, np.mean(res[name, 'rf']), np.mean(res[name, 'xgb'])))
