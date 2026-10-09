"""D6: is a separate 'Raha minus format-only FPs' version worth running, or do the counts suffice?
Format-only FP = flagged model cell that the ground truth calls correct but whose text differs (800 vs 800.0).
Trains Raha, Raha minus format-only FPs, and perfect under all three policies (fill = mean, D5).
Run: docker exec -w /rein/reports/block_d_final_plan_2026-10-09/checks/decisions rein-benchmark-rein-1 python3 d6_format_only.py <dataset>
"""
import sys
sys.dont_write_bytecode = True
import numpy as np
from mini_driver import Data, s2, verdict

ds = sys.argv[1]
data = Data(ds)
raha = data.F['raha']
fmt = {(i, j) for (i, j) in raha - data.A if data.dirty.iat[i, j] != data.clean.iat[i, j]}
minus = raha - fmt
ex = sorted(fmt)[:3]
print('== %s | Raha flags %d (model columns): TP %d, FP %d, of which format-only %d' % (
    ds, len(raha), len(raha & data.A), len(raha - data.A), len(fmt)))
print('  examples (row, column, dirty text, clean text):', [(i, data.cols[j], data.dirty.iat[i, j], data.clean.iat[i, j]) for i, j in ex])
print('  Raha minus format-only == perfect detector: %s (TP %d of %d, FP %d)' % (
    minus == data.perfect, len(minus & data.perfect), len(data.perfect), len(minus - data.perfect)))
V = {'Raha': raha, 'Raha minus fmt-only': minus, 'perfect': data.perfect}
models = ('linear', 'rf', 'xgb')
S = {}
for pol in ('gt', 'delete', 'impute'):
    for name, fl in V.items():
        res = [s2(data, fl, pol, seed) for seed in range(10)]
        S[pol, name] = ([r[0] for r in res], [r[1] for r in res], [r[2] for r in res])
floor = [s2(data, set(), 'floor', seed)[0] for seed in range(10)]
score = 'minority F1' if data.clf else '-RMSE'
print('\n  mean S2 (%s, higher better), 10 seeds; rows kept min-max' % score)
print('  %-7s %-20s %-16s %s' % ('', 'floor', '', '   '.join('%s %8.3f' % (m, np.mean([f[m] for f in floor])) for m in models)))
for pol in ('gt', 'delete', 'impute'):
    for name in V:
        sc, kept, _ = S[pol, name]
        if sc[0][models[0]] is None:
            print('  %-7s %-20s rows %5d-%-5d  degenerate' % (pol, name, min(kept), max(kept))); continue
        print('  %-7s %-20s rows %5d-%-5d  %s' % (pol, name, min(kept), max(kept), '   '.join('%s %8.3f' % (m, np.mean([s[m] for s in sc])) for m in models)))
    sa, _, ha = S[pol, 'Raha']; sb, _, hb = S[pol, 'Raha minus fmt-only']
    if sa[0]['linear'] is not None and sb[0]['linear'] is not None:
        print('  %-7s verdict Raha vs Raha-minus-fmt per model: %s' % (pol, ', '.join(
            '%s %s' % (m, verdict([s[m] for s in sa], [s[m] for s in sb], ha, hb)) for m in models)))
