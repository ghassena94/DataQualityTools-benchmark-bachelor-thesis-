"""D5 follow-up: why median beats mean on bike under impute. Per model column, split 0, perfect detector:
flagged cells, fill value (mean vs median of the unflagged kept cells), and what the clean values look like.
Then drop-one-column test: impute with median everywhere except one column (mean there), RF, 10 seeds.
Run: docker exec -w /rein/reports/block_d_final_plan_2026-10-09/checks/decisions rein-benchmark-rein-1 python3 d5_bike_columns.py
"""
import math, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from mini_driver import Data, num

data = Data('bike')
tr, te = data.split(0)
fl = data.perfect
by = {}
for i, j in fl:
    by.setdefault(data.cols[j], set()).add(i)
print('%-11s %7s %10s %10s  %-28s %s' % ('column', 'flagged', 'fill mean', 'fill med', 'clean values of flagged cells', 'distinct clean values'))
for c in data.numeric:
    f = [i for i in tr if i in by.get(c, ())]
    pool = num(data.dirty.loc[[i for i in tr if i not in by.get(c, ())], c]).dropna()
    cv = num(data.clean.loc[f, c]) if f else pd.Series(dtype=float)
    print('%-11s %7d %10.4g %10.4g  mean %-8.4g sd %-8.4g        %d' % (c, len(f), pool.mean(), pool.median(),
          cv.mean() if len(cv) else float('nan'), cv.std() if len(cv) else float('nan'), data.clean[c].nunique()))
ex = [i for i in tr if i in by.get('hr', ())][:3]
print('\nexample flagged hr cells (dirty -> clean):', [(data.dirty.loc[i, 'hr'], data.clean.loc[i, 'hr']) for i in ex])

# swap test: impute every column with the mean except ONE column with the median (RF, perfect detector, seeds 0-2)
def rmse_with(median_cols, seeds=(0, 1, 2)):
    out = []
    for seed in seeds:
        tr, te = data.split(seed)
        kept = np.array([i for i in tr if i not in by.get(data.lab, ())], dtype=int)
        X = data.dirty.loc[kept, data.numeric].copy()
        for c in data.numeric:
            f = [i for i in kept if i in by.get(c, ())]
            if not f:
                continue
            pool = num(data.dirty.loc[[i for i in kept if i not in by.get(c, ())], c]).dropna()
            X.loc[f, c] = pool.median() if c in median_cols else pool.mean()
        Xn = X.apply(num); T = data.clean.loc[te, data.numeric].apply(num)
        m = RandomForestRegressor(random_state=0, n_jobs=1).fit(Xn.values, num(data.dirty.loc[kept, data.lab]).values)
        out.append(math.sqrt(mean_squared_error(data.y_clean[te], m.predict(T.values))))
    return np.mean(out)

print('\nRF S2 RMSE, perfect detector under impute, seeds 0-2:')
print('  all mean   %.2f' % rmse_with(set()))
print('  all median %.2f' % rmse_with(set(data.numeric)))
for c in data.numeric:
    print('  median only on %-11s %.2f' % (c, rmse_with({c})))
