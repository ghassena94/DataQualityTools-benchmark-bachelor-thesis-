import json, sys, itertools
import numpy as np
from scipy.stats import wilcoxon, kendalltau

res = {}
for line in sys.stdin:
    if line.strip():
        d = json.loads(line)
        if d["dataset"] in res:  # second file: merge extra arms into the same records
            for m, rec in d["result"].items():
                res[d["dataset"]][m] += rec
        else:
            res[d["dataset"]] = d["result"]
        if "seconds" in d:
            print("meta", d["dataset"], d["seconds"], "s", d["meta"])
ARMS = ["default", "own_s0", "own_s1", "gt"]

for ds, by_model in res.items():
    better_high = ds == "breast_cancer"  # F1 higher is better; nasa RMSE lower is better
    sgn = 1 if better_high else -1
    for mname, rec in by_model.items():
        S = {}  # (version, arm) -> array over splits
        rows = {}
        for s, v, arm, sc, n in rec:
            rows[v] = n
            if sc is None:
                continue
            S.setdefault((v, arm), {})[s] = sc
        versions = [v for v in dict.fromkeys(r[1] for r in rec) if (v, "default") in S]
        degenerate = [v for v in dict.fromkeys(r[1] for r in rec) if (v, "default") not in S]
        splits = sorted(S[(versions[0], "default")])
        A = {k: np.array([S[k][s] for s in splits]) for k in S}
        print(f"\n=== {ds} / {mname}  ({'F1 malignant' if better_high else 'RMSE'}; degenerate: {degenerate})")
        print("version".ljust(16) + "".join(a.rjust(10) for a in ARMS) + "  tune gain")
        for v in versions:
            m = [A[(v, a)].mean() for a in ARMS]
            gain = sgn * (A[(v, 'own_s0')].mean() - A[(v, 'default')].mean())
            print(v.ljust(16) + "".join(f"{x:10.4f}" for x in m) + f"  {gain:+.4f}")
        # rankings by mean per arm
        rank = {}
        for a in ARMS:
            order = sorted(versions, key=lambda v: -sgn * A[(v, a)].mean())
            rank[a] = order
            print(f"  order[{a}]: " + " > ".join(order))
        def tau(a, b):
            ra = [rank[a].index(v) for v in versions]; rb = [rank[b].index(v) for v in versions]
            return kendalltau(ra, rb)[0]
        print(f"  tau(default, own_s0)={tau('default','own_s0'):.2f}  tau(own_s0, own_s1)={tau('own_s0','own_s1'):.2f}  tau(default, gt)={tau('default','gt'):.2f}")
        # search noise vs between-version gaps
        noise = np.mean([np.abs(A[(v, 'own_s0')] - A[(v, 'own_s1')]).mean() for v in versions])
        pairs = list(itertools.combinations(versions, 2))
        gaps_def = {p: abs((A[(p[0], 'default')] - A[(p[1], 'default')]).mean()) for p in pairs}
        print(f"  mean |own_s0 - own_s1| on the same data and split (search noise): {noise:.4f}")
        if (versions[0], "default_r1") in A:
            mnoise = np.mean([np.abs(A[(v, 'default')] - A[(v, 'default_r1')]).mean() for v in versions])
            print(f"  mean |default rs0 - default rs1| (the model's own seed noise, no tuning): {mnoise:.4f}")
        print(f"  between-version mean gaps under defaults: " + ", ".join(f"{p[0]}-{p[1]} {g:.4f}" for p, g in gaps_def.items()))
        print(f"  pairs whose default gap is smaller than the search noise: {sum(g < noise for g in gaps_def.values())}/{len(pairs)}")
        # per-split pairwise order flips between the two search seeds (same data, same split)
        flips = tot = 0
        for p in pairs:
            d0 = A[(p[0], 'own_s0')] - A[(p[1], 'own_s0')]
            d1 = A[(p[0], 'own_s1')] - A[(p[1], 'own_s1')]
            for x, y in zip(d0, d1):
                if x == 0 or y == 0:
                    continue
                tot += 1; flips += (np.sign(x) != np.sign(y))
        print(f"  per-split pair orders flipped by the search seed alone: {flips}/{tot}")
        # significance verdicts per pair: default vs own_s0 vs own_s1
        def verdict(arm, p):
            d = A[(p[0], arm)] - A[(p[1], arm)]
            if np.allclose(d, 0):
                return "tie"
            try:
                pv = wilcoxon(d).pvalue
            except ValueError:
                return "tie"
            if pv >= 0.05:
                return "tie"
            return ">" if sgn * d.mean() > 0 else "<"
        changed = 0
        for p in pairs:
            vs = [verdict(a, p) for a in ("default", "own_s0", "own_s1")]
            if len(set(vs)) > 1:
                changed += 1
                print(f"    verdict differs {p[0]} vs {p[1]}: default {vs[0]}, own_s0 {vs[1]}, own_s1 {vs[2]}")
        print(f"  pairs whose Wilcoxon verdict changes with tuning or search seed: {changed}/{len(pairs)}")
        for a in ("default", "own_s0", "own_s1", "gt"):
            vs = [verdict(a, p) for p in pairs]
            print(f"    significant pairs under {a}: {sum(v != 'tie' for v in vs)}/{len(pairs)}")
        # REIN-style tuning on ground truth vs own tuning
        leak = np.mean([sgn * (A[(v, 'gt')].mean() - A[(v, 'own_s0')].mean()) for v in versions])
        print(f"  mean advantage of params tuned on CLEAN data over params tuned on the version itself: {leak:+.4f}")
