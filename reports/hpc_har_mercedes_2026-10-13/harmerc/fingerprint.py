import csv, sys, collections, re
base = "/Users/ghassen.aicha@caronsale.de/Desktop/BA/rein-benchmark/rein-datasets"
def load(p):
    with open(p, newline='', encoding='utf-8') as f:
        r = csv.reader(f); h = next(r); return h, [row for row in r]
def ndig(s): return len(re.sub(r"[^0-9]", "", s))
for ds in sys.argv[1:]:
    dh, d = load(f"{base}/{ds}/dirty.csv"); ch, c = load(f"{base}/{ds}/clean.csv")
    idx = [ch.index(h) for h in dh]
    n, m = len(d), len(dh)
    err = collections.defaultdict(list); unt = collections.defaultdict(list)
    for i in range(n):
        for j in range(m):
            dv, cv = d[i][j].strip(), c[i][idx[j]].strip()
            (err if dv != cv else unt)[j].append((dv, cv))
    kinds = collections.Counter(); longer = 0; nonblank = 0; dig = collections.Counter()
    percol = []
    for j in range(m):
        maxlen_unt = max((len(v) for v, _ in unt[j]), default=0)
        maxdig_unt = max((ndig(v) for v, _ in unt[j]), default=0)
        cl = 0; nb = 0
        for dv, cv in err[j]:
            if dv == '': kinds['blank'] += 1; continue
            try: float(dv); k = 'numeric'
            except ValueError: k = 'text'
            kinds[k] += 1; nb += 1
            dig[min(ndig(dv), 25)] += 1
            if len(dv) > maxlen_unt: cl += 1
        longer += cl; nonblank += nb
        percol.append((dh[j], len(err[j]), nb, cl, maxlen_unt, maxdig_unt))
    print(f"== {ds}: error cells by kind {dict(kinds)}")
    print(f"  non-blank error cells longer than ANY untouched value of their column: {longer}/{nonblank} ({longer/max(nonblank,1):.3f})")
    print(f"  digit-count histogram of non-blank dirty error values: {sorted(dig.items())}")
    show = percol if m <= 10 else percol[:12] + [('...',)] + percol[-3:]
    for p in show: print("   ", p)
    if m > 10:
        # summary for binary columns
        b = [p for p in percol if p[4] == 1]
        print(f"  columns whose untouched values all have length 1 (binary 0/1): {len(b)}; their non-blank err {sum(p[2] for p in b)}, longer {sum(p[3] for p in b)}")
    # sample errors
    ex = [(dh[j], dv, cv) for j in range(m) for dv, cv in err[j][:2]][:12]
    print("  examples (col, dirty, clean):", ex)
