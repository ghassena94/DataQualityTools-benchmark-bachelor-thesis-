"""Type I error of the pooled permutation test of plan section 8.4 (concordant-pair count, reference scores
permuted within each dataset, one permutation shared by the 3 models, per-dataset distributions convolved,
one-sided p = P(count >= observed)).

Null: downstream verdicts are generated independently of the reference order.
  N1  each model: an independent uniformly random total order of the items
  N2  one random total order shared by the 3 models of a dataset (maximal between-model dependence)
  N3  N1 plus each pair independently declared a tie with probability 0.4
Designs:
  pre-merge  5/5/5/5 items; bike items 3,4 and adult items 2,3,4 are structurally identical
             (always tied downstream AND tied in the reference, as the review's A3 describes)
  post-merge 5/5/4/3 items (plan section 3)
  delete-left-out  bc 4, nasa 3, bike 3, adult 2 (plan section 5 table), no structural ties
Run: docker exec -w /rein rein-benchmark-rein-1 python3 reports/block_d_final_plan_2026-10-09/fable/fable_typeI_sim.py
"""
import itertools
import sys

import numpy as np

rng = np.random.default_rng(20261009)
NMODELS = 3
REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 20000


def pair_dirs(score):
    """dict pair -> +1 / -1 / 0 from a score vector (ties = equal scores)."""
    m = len(score)
    out = {}
    for a, b in itertools.combinations(range(m), 2):
        out[(a, b)] = 0 if score[a] == score[b] else (1 if score[a] > score[b] else -1)
    return out


def concordant(ref_dirs, down_dirs):
    return sum(1 for k in ref_dirs if ref_dirs[k] != 0 and ref_dirs[k] == down_dirs[k])


def perm_distribution(ref_scores, down_list):
    """distribution (dict count -> prob) of the pooled-over-models concordant count when the reference
    scores are permuted uniformly among the items; down_list = list of per-model downstream dir dicts."""
    m = len(ref_scores)
    dist = {}
    perms = list(itertools.permutations(range(m)))
    for p in perms:
        rs = [ref_scores[p[i]] for i in range(m)]
        rd = pair_dirs(rs)
        c = sum(concordant(rd, dd) for dd in down_list)
        dist[c] = dist.get(c, 0) + 1
    tot = len(perms)
    return {k: v / tot for k, v in dist.items()}


def convolve(d1, d2):
    out = {}
    for a, pa in d1.items():
        for b, pb in d2.items():
            out[a + b] = out.get(a + b, 0) + pa * pb
    return out


def downstream(m, identical_groups, null, tie_p=0.4):
    """returns list of NMODELS dir dicts"""
    def one_order():
        s = rng.permutation(m).astype(float)
        for g in identical_groups:          # structurally identical items share one downstream score
            s[list(g)] = s[g[0]]
        dd = pair_dirs(s)
        if null == 'N3':
            for k in dd:
                if rng.random() < tie_p:
                    dd[k] = 0
        return dd
    if null == 'N2':
        o = one_order()
        return [dict(o) for _ in range(NMODELS)]
    return [one_order() for _ in range(NMODELS)]


def design(name):
    if name == 'pre-merge':
        return [dict(m=5, groups=[]), dict(m=5, groups=[]), dict(m=5, groups=[(3, 4)]), dict(m=5, groups=[(2, 3, 4)])]
    if name == 'post-merge':
        return [dict(m=5, groups=[]), dict(m=5, groups=[]), dict(m=4, groups=[]), dict(m=3, groups=[])]
    if name == 'delete-left-out':
        return [dict(m=4, groups=[]), dict(m=3, groups=[]), dict(m=3, groups=[]), dict(m=2, groups=[])]
    raise ValueError(name)


def ref_scores_for(dsd):
    # distinct reference scores, except structurally identical items (tied at 0, like the zero-flag GE tiers)
    s = list(np.arange(dsd['m'], 0, -1, dtype=float))
    for g in dsd['groups']:
        for i in g:
            s[i] = 0.0
    return s


print('reps per cell:', REPS)
print('%-16s %-4s %-10s %-10s %-10s' % ('design', 'null', 'P(p<.05)', 'P(p<=.05)', 'mean p'))
for dname in ('pre-merge', 'post-merge', 'delete-left-out'):
    for null in ('N1', 'N2', 'N3'):
        rej, rej_le, ps = 0, 0, []
        dsl = design(dname)
        for _ in range(REPS):
            total_obs = 0
            dist = {0: 1.0}
            for dsd in dsl:
                ref = ref_scores_for(dsd)
                rd = pair_dirs(ref)
                down = downstream(dsd['m'], dsd['groups'], null)
                total_obs += sum(concordant(rd, dd) for dd in down)
                dist = convolve(dist, perm_distribution(ref, down))
            p = sum(v for k, v in dist.items() if k >= total_obs)
            ps.append(p)
            rej += p < 0.05
            rej_le += p <= 0.05
        print('%-16s %-4s %-10.4f %-10.4f %-10.4f' % (dname, null, rej / REPS, rej_le / REPS, float(np.mean(ps))))
