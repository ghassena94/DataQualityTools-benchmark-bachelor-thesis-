"""D5 follow-up: are the bike rows with a `holiday` error a random sample? (They are not: fewer rentals.)
Run: docker exec -w /rein/reports/block_d_final_plan_2026-10-09/checks/decisions rein-benchmark-rein-1 python3 d5_bike_holiday.py
"""
import numpy as np, pandas as pd
from mini_driver import Data, num
d = Data('bike'); by = {}
for i, j in d.perfect: by.setdefault(d.cols[j], set()).add(i)
cnt = d.y_clean
for c in ('holiday', 'season', 'mnth'):
    f = np.array(sorted(by[c])); nf = np.setdiff1d(np.arange(len(cnt)), f)
    print('%-8s flagged rows %5d: mean clean cnt %.1f | unflagged rows %5d: mean clean cnt %.1f' % (c, len(f), cnt[f].mean(), len(nf), cnt[nf].mean()))
print('overlap holiday & season %d, holiday & mnth %d' % (len(by['holiday'] & by['season']), len(by['holiday'] & by['mnth'])))
f = sorted(by['holiday'])
print('dirty holiday values of flagged cells:', d.dirty.loc[f, 'holiday'].value_counts().head(6).to_dict())
print('clean hr of holiday-flagged rows (top):', d.clean.loc[f, 'hr'].value_counts().head(6).to_dict())
print('clean hr of all rows (top):', d.clean['hr'].value_counts().head(3).to_dict())
print('clean holiday of flagged rows:', d.clean.loc[f, 'holiday'].value_counts().to_dict())
