"""D7: how long does one training take per dataset and model? (floor version, split 0, n_jobs=1)
Run: docker exec -w /rein/reports/block_d_final_plan_2026-10-09/checks/decisions rein-benchmark-rein-1 python3 d7_fit_times.py
"""
import sys
sys.dont_write_bytecode = True
import time
from sklearn.preprocessing import StandardScaler
import mini_driver as md

for ds in ('breast_cancer', 'nasa', 'bike', 'adult'):
    data = md.Data(ds)
    tr, te = data.split(0)
    t0 = time.time(); X, y, kept = data.version(set(), 'floor', tr); Xtr, Xte = data.featurize(X, te); prep = time.time() - t0
    out = []
    for name, m, scale in md.models(data.clf, 0):
        t0 = time.time()
        Z = StandardScaler().fit(Xtr).transform(Xtr) if scale else Xtr
        m.fit(Z, y); out.append('%s %.1f s' % (name, time.time() - t0))
    print('%-14s %6d x %3d features | prepare %.1f s | %s' % (ds, Xtr.shape[0], Xtr.shape[1], prep, ' | '.join(out)))
