"""D3: model seed fixed (random_state=0) vs equal to the split seed.
1. Which models react to random_state at all.  2. How big pure model noise is.  3. Pair verdicts on bc and nasa
under all three policies, both ways, counted.
Run: docker exec -w /rein/reports/block_d_final_plan_2026-10-09/checks/decisions rein-benchmark-rein-1 python3 d3_model_seed.py
"""
import itertools, numpy as np
from mini_driver import Data, s2, verdict

for ds in ('breast_cancer', 'nasa'):
    data = Data(ds)
    print('\n' + '=' * 90 + '\n' + ds, '| items:', list(data.items))
    # 1. does random_state change the model? floor version, seed 0, random_state 0 vs 1..4
    base, _, _ = s2(data, set(), 'floor', 0, 'fixed')
    for name in ('linear', 'rf', 'xgb'):
        other = []
        for rs in range(1, 5):
            tr, te = data.split(0)
            from mini_driver import models
            import mini_driver as md
            X, ytr, kept = data.version(set(), 'floor', tr)
            Xtr, Xte = data.featurize(X, te)
            m = dict((n, (mm, sc)) for n, mm, sc in md.models(data.clf, rs))[name]
            from sklearn.preprocessing import StandardScaler
            S = StandardScaler().fit(Xtr)
            m[0].fit(S.transform(Xtr) if m[1] else Xtr, ytr)
            p = m[0].predict(S.transform(Xte) if m[1] else Xte)
            from sklearn.metrics import f1_score, mean_squared_error
            import math
            other.append(f1_score(data.y_clean[te], p) if data.clf else -math.sqrt(mean_squared_error(data.y_clean[te], p)))
        print('  1. floor, seed 0, %-6s random_state 0: %.4f | 1-4: %s' % (name, base[name], ' '.join('%.4f' % v for v in other)))
    # 3. pair verdicts, RF only (the other two do not react, see 1.)
    S = {}
    H = {}
    for pol in ('gt', 'delete', 'impute'):
        for it, fl in data.items.items():
            for opt in ('fixed', 'split'):
                sc, hs = [], []
                for seed in range(10):
                    o, k, h = s2(data, fl, pol, seed, opt, which=('rf',))
                    sc.append(o['rf']); hs.append(h)
                S[pol, it, opt] = sc; H[pol, it] = hs
    changed = total = 0
    for pol in ('gt', 'delete', 'impute'):
        print('  3. %s, RF: pair verdicts (fixed seed | seed = split seed)' % pol)
        for a, b in itertools.combinations(data.items, 2):
            if None in S[pol, a, 'fixed'] or None in S[pol, b, 'fixed']:
                print('     %-32s degenerate' % ('%s vs %s' % (a, b)))
                continue
            v = [verdict(S[pol, a, o], S[pol, b, o], H[pol, a], H[pol, b]) for o in ('fixed', 'split')]
            total += 1; changed += v[0] != v[1]
            gap = np.mean(S[pol, a, 'fixed']) - np.mean(S[pol, b, 'fixed'])
            print('     %-32s %-4s | %-4s  mean diff fixed %+.4f split %+.4f %s' % (
                '%s vs %s' % (a, b), v[0], v[1], gap, np.mean(S[pol, a, 'split']) - np.mean(S[pol, b, 'split']),
                '  <-- CHANGES' if v[0] != v[1] else ''))
    print('  => %s: %d of %d RF pair verdicts change' % (ds, changed, total))
