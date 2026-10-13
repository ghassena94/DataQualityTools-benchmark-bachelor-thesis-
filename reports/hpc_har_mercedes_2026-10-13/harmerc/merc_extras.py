import csv, collections
base = "/Users/ghassen.aicha@caronsale.de/Desktop/BA/rein-benchmark/rein-datasets/mercedes"
def load(p):
    with open(p, newline='') as f:
        r = csv.reader(f); h = next(r); return h, [[x.strip() for x in row] for row in r]
dh, d = load(f"{base}/dirty.csv"); ch, c = load(f"{base}/clean.csv")
gt = set()
for row in csv.reader(open(f"{base}/actual_errors.csv")):
    gt.add((int(row[0]), int(row[1])))
n, m = len(d), len(dh)
grp = collections.Counter(); cells = collections.Counter()
val = collections.Counter()  # for binary-vs-binary untouched cells: (dirty value, label)
for j in range(m):
    a, b = dh[j], ch[j]
    if j < 2: g = f"pos{j}: dirty {a} vs clean {b}"
    elif j >= m - 2: g = f"pos{j}: dirty {a} vs clean {b}"
    elif a in ('X0','X1','X2','X3','X4','X5','X6','X8') or b in ('X0','X1','X2','X3','X4','X5','X6','X8'): g = "categorical involved"
    else: g = "binary dirty vs binary clean (shift 2)"
    for i in range(n):
        if (i, j) in gt: continue
        cells[g] += 1
        if d[i][j] != c[i][j]:
            grp[g] += 1
            if g.startswith("binary"): val[(d[i][j], 1)] += 1
        elif g.startswith("binary"): val[(d[i][j], 0)] += 1
for g in cells: print(f"{g}: untouched cells {cells[g]}, oracle extras {grp[g]}")
print("binary-binary untouched: (dirty value, oracle label) counts", dict(val))
for v in ('0', '1'):
    t = val[(v,0)] + val[(v,1)]
    if t: print(f"  P(oracle says error | dirty value {v}) = {val[(v,1)]/t:.3f}  (n={t})")
