"""D4: a column is numeric if >= 90 % of its clean values parse (proposal) vs only if every value parses.
Only breast_cancer `Bare Nuclei` differs (16 `?` in clean.csv). Train bc both ways, all policies and models.
Run: docker exec -w /rein/reports/block_d_final_plan_2026-10-09/checks/decisions rein-benchmark-rein-1 python3 d4_numeric_rule.py
"""
import itertools, numpy as np
from mini_driver import Data, s2, verdict, isnum

d90, dall = Data('breast_cancer', '90'), Data('breast_cancer', 'all')
c = 'Bare Nuclei'
print('Bare Nuclei under the 90 %% rule: %s | under the strict rule: %s' % (
    'numeric' if c in d90.numeric else 'categorical', 'numeric' if c in dall.numeric else 'categorical'))
v = d90.dirty[c]
print('dirty Bare Nuclei, values that do not parse:', v[~v.map(isnum)].value_counts().to_dict())
print('distinct dirty values (= one-hot columns under the strict rule):', v.nunique())
items = dict(d90.items); items['perfect'] = d90.perfect
models = ('linear', 'rf', 'xgb')
S = {}
for rule, data in (('90', d90), ('all', dall)):
    for pol in ('floor', 'gt', 'delete', 'impute'):
        for it, fl in (items.items() if pol != 'floor' else [('floor', set())]):
            res = [s2(data, fl, pol, seed) for seed in range(10)]
            for m in models:
                S[rule, pol, it, m] = [r[0][m] for r in res]
            S[rule, pol, it, 'hash'] = [r[2] for r in res]
    res = [s2(data, d90.perfect, 'gt', seed) for seed in range(10)]
print('\nmean S2 minority F1 over 10 seeds (90 %% rule -> strict rule)')
print('%-8s %-10s %s' % ('policy', 'item', '   '.join('%-17s' % m for m in models)))
for pol in ('floor', 'gt', 'delete', 'impute'):
    for it in (items if pol != 'floor' else ['floor']):
        if None in S['90', pol, it, 'linear']:
            print('%-8s %-10s degenerate' % (pol, it)); continue
        print('%-8s %-10s %s' % (pol, it, '   '.join('%.4f -> %.4f' % (np.mean(S['90', pol, it, m]), np.mean(S['all', pol, it, m])) for m in models)))
changed = total = 0
print('\npair verdicts that change (detector items only, as in the analysis):')
for pol in ('gt', 'delete', 'impute'):
    for a, b in itertools.combinations(d90.items, 2):
        for m in models:
            if None in S['90', pol, a, m] or None in S['90', pol, b, m]:
                continue
            v1 = verdict(S['90', pol, a, m], S['90', pol, b, m], S['90', pol, a, 'hash'], S['90', pol, b, 'hash'])
            v2 = verdict(S['all', pol, a, m], S['all', pol, b, m], S['all', pol, a, 'hash'], S['all', pol, b, 'hash'])
            total += 1
            if v1 != v2:
                changed += 1
                print('  %-7s %-6s %-22s 90 %%: %-4s strict: %s' % (pol, m, '%s vs %s' % (a, b), v1, v2))
print('=> %d of %d pair verdicts change' % (changed, total))
