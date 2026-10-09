"""D5: fill value for missing/unparsable numeric cells (featurization) and flagged numeric cells (impute):
mean (proposal, REIN's mean/mode imputer) vs median. Trains every item + floor + perfect under all policies
and models, both ways; counts verdict changes and concordance with Table 3 (reference a).
Run: docker exec -w /rein/reports/block_d_final_plan_2026-10-09/checks/decisions rein-benchmark-rein-1 python3 d5_fill_statistic.py <dataset> [policies]
bike: every dirty value parses, so floor/gt/delete are identical under both fills by construction; run 'floor,impute'.
"""
import itertools, sys, numpy as np
from mini_driver import Data, s2, verdict, num, SHORT
T3 = {'breast_cancer': dict(ge_dirty_profiled=.554, ge_clean_profiled=.603, ge_hand_written=.803, holoclean=.132, raha=.618),
      'nasa': dict(ge_dirty_profiled=.079, ge_clean_profiled=.689, ge_hand_written=.964, holoclean=.159, raha=.430),
      'bike': dict(ge_dirty_profiled=0., ge_clean_profiled=0., ge_hand_written=.829, holoclean=.216, raha=.769),
      'adult': dict(ge_dirty_profiled=0., ge_clean_profiled=0., ge_hand_written=0., holoclean=.005, raha=.226)}
INV = {v: k for k, v in SHORT.items()}
ds = sys.argv[1]
POLICIES = sys.argv[2].split(',') if len(sys.argv) > 2 else ['floor', 'gt', 'delete', 'impute']   # bike: only impute can differ
data = Data(ds)
ref = {it: max(T3[ds][INV[c]] for c in it.split('=')) for it in data.items}
tr, te = data.split(0)
print('==', ds, '| seed 0 training rows, numeric feature columns: dirty mean / dirty median / clean mean')
for c in data.numeric:
    dv, cv = num(data.dirty.loc[tr, c]).dropna(), num(data.clean.loc[tr, c]).dropna()
    print('  %-28s %-12.6g %-12.6g %-12.6g  unparsable dirty cells %d' % (c, dv.mean(), dv.median(), cv.mean(), (~data.dirty.loc[tr, c].map(lambda v: num(__import__('pandas').Series([v])).notna()[0])).sum()))
items = dict(data.items); items['perfect'] = data.perfect
models = ('linear', 'rf', 'xgb')
S = {}
for fill in ('mean', 'median'):
    for pol in POLICIES:
        for it, fl in (items.items() if pol != 'floor' else [('floor', set())]):
            res = [s2(data, fl, pol, seed, fill=fill) for seed in range(10)]
            for m in models:
                S[fill, pol, it, m] = [r[0][m] for r in res]
            S[fill, pol, it, 'hash'] = [r[2] for r in res]
score = 'minority F1' if data.clf else '-RMSE'
print('\nmean S2 (%s, higher better) over 10 seeds: mean fill -> median fill' % score)
for pol in POLICIES:
    for it in (items if pol != 'floor' else ['floor']):
        if None in S['mean', pol, it, 'linear']:
            print('  %-7s %-20s degenerate' % (pol, it)); continue
        print('  %-7s %-20s %s' % (pol, it, '   '.join('%s %8.4f -> %8.4f' % (m, np.mean(S['mean', pol, it, m]), np.mean(S['median', pol, it, m])) for m in models)))
print('\npair verdicts that change, and concordance with Table 3 (C/D/T = concordant/discordant/tie, degenerate pairs left out):')
changed = total = 0
for pol in [p for p in POLICIES if p != 'floor']:
    for m in models:
        cnt = {}
        for fill in ('mean', 'median'):
            C = Dd = T = 0
            for a, b in itertools.combinations(data.items, 2):
                if None in S[fill, pol, a, m] or None in S[fill, pol, b, m]:
                    continue
                v = verdict(S[fill, pol, a, m], S[fill, pol, b, m], S[fill, pol, a, 'hash'], S[fill, pol, b, 'hash'])
                r = '>' if ref[a] > ref[b] else '<'
                if v == 'tie': T += 1
                elif v == r: C += 1
                else: Dd += 1
                if fill == 'mean':
                    v2 = verdict(S['median', pol, a, m], S['median', pol, b, m], S['median', pol, a, 'hash'], S['median', pol, b, 'hash'])
                    total += 1
                    if v != v2:
                        changed += 1
                        print('  %-7s %-6s %-24s mean: %-4s median: %-4s (Table 3: %s)' % (pol, m, '%s vs %s' % (a, b), v, v2, r))
            cnt[fill] = '%d/%d/%d' % (C, Dd, T)
        print('  -> %-7s %-6s C/D/T mean %s | median %s' % (pol, m, cnt['mean'], cnt['median']))
print('=> %s: %d of %d pair verdicts change' % (ds, changed, total))
