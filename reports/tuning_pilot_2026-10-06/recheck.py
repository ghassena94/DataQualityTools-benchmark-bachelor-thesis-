import json, itertools, sys
import numpy as np
from scipy.stats import wilcoxon
res = {}
for f in ("tuning_out.jsonl", "seed_control.jsonl"):
    for line in open(f):
        d = json.loads(line)
        for m, rec in d["result"].items():
            res.setdefault((d["dataset"], m), []).extend(rec)
ARMS = ["default", "default_r1", "own_s0", "own_s1", "gt"]
def exact_verdict(d, sgn):
    nz = d[d != 0]
    if len(nz) <= 5:
        return "tie", len(nz), None
    p = wilcoxon(nz, mode="exact").pvalue
    return ("tie" if p >= 0.05 else (">" if sgn * nz.mean() > 0 else "<")), len(nz), round(p, 4)
for (ds, m), rec in res.items():
    sgn = 1 if ds == "breast_cancer" else -1
    S = {}
    for s, v, arm, sc, n in rec:
        if sc is not None:
            S.setdefault((v, arm), {})[s] = sc
    vers = [v for v in dict.fromkeys(r[1] for r in rec) if (v, "default") in S]
    A = {k: np.array([S[k][s] for s in sorted(S[k])]) for k in S}
    pairs = list(itertools.combinations(vers, 2))
    def mean_flips(a, b):
        return sum(np.sign((A[(p[0], a)] - A[(p[1], a)]).mean()) != np.sign((A[(p[0], b)] - A[(p[1], b)]).mean()) for p in pairs)
    print(f"\n{ds}/{m}: mean-level pair-order flips  model seed (def rs0 vs rs1): {mean_flips('default','default_r1')}/{len(pairs)}"
          f"  search seed (own_s0 vs own_s1): {mean_flips('own_s0','own_s1')}/{len(pairs)}"
          f"  default vs own_s0: {mean_flips('default','own_s0')}/{len(pairs)}")
    sig = {a: [] for a in ARMS}
    for p in pairs:
        row = []
        for a in ARMS:
            v, n, pv = exact_verdict(A[(p[0], a)] - A[(p[1], a)], sgn)
            sig[a].append(v != "tie"); row.append(f"{a}:{v}(n={n},p={pv})")
        if len({r.split(':')[1].split('(')[0] for r in row}) > 1:
            print("   verdict differs", p, " | ".join(row))
    print("   significant pairs (exact, zeros dropped): " + ", ".join(f"{a} {sum(sig[a])}/{len(pairs)}" for a in ARMS))
    gain = {v: round(sgn * (A[(v,'own_s0')].mean() - A[(v,'default')].mean()), 4) for v in vers}
    print("   tune gain own_s0 by version:", gain)
