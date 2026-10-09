"""SciPy 1.7.1 exact Wilcoxon vs an exact sign-flip test on midranks: order dependence, invariance checks.
Run: docker exec -w /rein rein-benchmark-rein-1 python3 reports/block_d_final_plan_2026-10-09/fable/fable_wilcoxon.py
"""
import inspect
import itertools

import numpy as np
import scipy
import scipy.stats
from scipy.stats import rankdata, wilcoxon

print('scipy', scipy.__version__)


def signflip_p(d):
    d = np.asarray([x for x in d if x != 0], float)
    n = len(d)
    if n == 0:
        return 1.0
    r = rankdata(np.abs(d))               # midranks
    T = abs(float(np.sum(np.sign(d) * r)))
    cnt = 0
    for s in itertools.product((1.0, -1.0), repeat=n):
        if abs(float(np.dot(s, r))) >= T - 1e-9:
            cnt += 1
    return cnt / 2 ** n


examples = [
    [4, 2, 4, 1, 3, 4, -3, 2, 1, -1],
    [2, 3, -1, 3, -2, 1, 1, 1, 2, 5],
    [5, -1, -1, 3, 3, 1, -2, 4, 2, 3],
]
print('%-45s %-9s %-9s %-9s %-9s %-9s' % ('d', 'p(d)', 'p(-d)', 'p(shuf)', 'signflip', 'sf(-d)'))
rs = np.random.default_rng(1)
for d in examples:
    d = np.array(d, float)
    p1 = wilcoxon(d, mode='exact').pvalue
    p2 = wilcoxon(-d, mode='exact').pvalue
    p3 = wilcoxon(rs.permutation(d), mode='exact').pvalue
    print('%-45s %-9.4f %-9.4f %-9.4f %-9.4f %-9.4f' % (d.tolist(), p1, p2, p3, signflip_p(d), signflip_p(-d)))

# how often does the SciPy exact p differ between d and -d, and how often does the verdict flip (random tied data)
flip, differ, tot = 0, 0, 0
for _ in range(5000):
    d = rs.integers(-3, 6, size=10).astype(float)
    if (d == 0).any():
        continue
    tot += 1
    p1, p2 = wilcoxon(d, mode='exact').pvalue, wilcoxon(-d, mode='exact').pvalue
    differ += abs(p1 - p2) > 1e-12
    flip += (p1 < 0.05) != (p2 < 0.05)
print('random integer d (n=10, ties common): p(d) != p(-d) in %d of %d; verdict flips in %d' % (differ, tot, flip))

# invariance of the sign-flip test under index permutation and sign reversal, and symmetry check on untied data vs SciPy
ok = True
for _ in range(200):
    d = rs.integers(-4, 5, size=8).astype(float)
    d = d[d != 0]
    if len(d) < 2:
        continue
    a, b, c = signflip_p(d), signflip_p(-d), signflip_p(rs.permutation(d))
    ok &= abs(a - b) < 1e-12 and abs(a - c) < 1e-12
print('sign-flip p invariant under reversal and index permutation on 200 random vectors:', ok)
agree = True
for _ in range(100):
    d = rs.normal(size=9)
    agree &= abs(signflip_p(d) - wilcoxon(d, mode='exact').pvalue) < 1e-9
print('sign-flip p == SciPy exact p on untied data (100 random vectors):', agree)

# smallest two-sided p by n (all same sign): the "<= 5 non-zero = tie" rule
print('smallest p by n:', {n: 2 / 2 ** n for n in range(4, 11)})

# the int() truncation in SciPy's exact branch
src = inspect.getsource(wilcoxon)
for i, line in enumerate(src.splitlines()):
    if 'int(' in line or 'r_plus' in line and 'exact' in src and ('rankdata' in line or 'cnt' in line):
        print('wilcoxon src:', line.strip())
