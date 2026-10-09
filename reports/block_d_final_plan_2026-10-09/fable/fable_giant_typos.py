"""Which parsable errors lie far outside the clean range (fill-mean pollution), and which configurations flag them.
Run: docker exec -w /rein rein-benchmark-rein-1 python3 reports/block_d_final_plan_2026-10-09/fable/fable_giant_typos.py
"""
import importlib.util
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')
spec = importlib.util.spec_from_file_location('fm', '/rein/reports/block_d_final_plan_2026-10-09/fable/fable_measure.py')
src = open(spec.origin).read().split('report = {}')[0]
ns = {}
exec(compile(src, spec.origin, 'exec'), ns)
load, fnum, ge_real, holo_own, read_cells, prof, HW = (ns[k] for k in ['load', 'fnum', 'ge_real', 'holo_own', 'read_cells', 'prof', 'HW'])
D = '/rein/datasets'
for ds in ['nasa', 'breast_cancer', 'bike']:
    clean, dirty = load(ds)
    cols = list(dirty.columns)
    A = read_cells('%s/%s/actual_errors.csv' % (D, ds))
    F = {'dirty_prof': ge_real(dirty, prof.profile_expectations(dirty)), 'clean_prof': ge_real(dirty, prof.profile_expectations(clean)),
         'hand': ge_real(dirty, HW[ds]['hand_written']), 'holo': holo_own(dirty, ds)[0], 'raha': read_cells('%s/%s/raha/detections.csv' % (D, ds))}
    print('\n==', ds)
    for j, c in enumerate(cols):
        cl = pd.to_numeric(clean[c], errors='coerce')
        if cl.isna().mean() > 0.1:
            continue
        lo, hi = cl.min(), cl.max()
        errs = [(i, fnum(dirty.iat[i, j])) for (i, jj) in A if jj == j]
        if not errs:
            continue
        pars = [(i, v) for i, v in errs if v is not None]
        far = [(i, v) for i, v in pars if v > hi + 10 * (hi - lo) or v < lo - 10 * (hi - lo)]
        print('  %-28s clean range [%.4g, %.4g]  errors %d parsable %d  >10 ranges outside %d' % (c, lo, hi, len(errs), len(pars), len(far)))
        for i, v in sorted(far, key=lambda t: -abs(t[1]))[:4]:
            print('      row %5d dirty=%-18s clean=%-14s flagged by: %s' % (i, dirty.iat[i, j], clean.iat[i, j], [k for k, fl in F.items() if (i, j) in fl]))
        if far:
            d = pd.to_numeric(dirty[c], errors='coerce')
            keep = d.copy()
            keep[[i for i, _ in far]] = np.nan
            print('      dirty column mean %.4g; without the %d far cells %.4g; clean mean %.4g; how many far cells each config flags: %s' % (
                d.mean(), len(far), keep.mean(), cl.mean(), {k: sum(1 for i, _ in far if (i, j) in fl) for k, fl in F.items()}))
