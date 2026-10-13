import csv, re, collections
base = "/Users/ghassen.aicha@caronsale.de/Desktop/BA/rein-benchmark/rein-datasets"
def load(p):
    with open(p, newline='') as f:
        r = csv.reader(f); h = next(r); return h, [row for row in r]
miss = [25, 72, 121, 149, 188, 193, 303, 381]
binary = ['X' + str(i) for i in range(10, 386) if i not in miss]
suites = {
 'mercedes': dict([('ID', r'^\d+$'), ('y', r'^\d+(\.\d+)?$')] + [(c, r'^[a-z]{1,2}$') for c in ['X0','X1','X2','X3','X4','X5','X6','X8']] + [(c, r'^[01]$') for c in binary]),
 'har': {'Index': r'^\d+$', 'gt': r'^(null|sit|stand)$', 'x': r'^-?([0-9]|1[0-9]|20)(\.\d+)?$', 'y': r'^-?([0-9]|1[0-9]|20)(\.\d+)?$', 'z': r'^-?([0-9]|1[0-9]|20)(\.\d+)?$'},
 'nasa': None}
uniq = {'mercedes': 'ID', 'har': 'Index'}
for ds in ('mercedes', 'har'):
    for f in ('clean', 'dirty'):
        h, rows = load(f"{base}/{ds}/{f}.csv")
        s = suites[ds]
        cov = [c for c in h if c in s]; uncovered = [c for c in h if c not in s]
        viol = 0; percol = collections.Counter()
        for r in rows:
            for j, c in enumerate(h):
                if c in s and not re.match(s[c], r[j]): viol += 1; percol[c] += 1
        u = uniq[ds]; j = h.index(u); cnt = collections.Counter(r[j] for r in rows); dup = sum(v for v in cnt.values() if v > 1)
        print(f"{ds} {f}: columns covered {len(cov)}/{len(h)} uncovered={uncovered[:5]} regex-violating cells={viol} top={percol.most_common(3)} {u} cells in duplicate groups={dup}")
