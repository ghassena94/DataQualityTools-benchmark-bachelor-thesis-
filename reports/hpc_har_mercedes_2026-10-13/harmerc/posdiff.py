"""Read-only replica of raha.dataset.Dataset.get_actual_errors_dictionary (raha 1.25/1.26):
pandas.read_csv(header='infer', dtype=str, keep_default_na=False) + value_normalizer, then positional
comparison df1.values != df2.values (column NAMES ignored). Header line = column names, not a data row."""
import csv, html, re, sys, collections
def norm(v):
    v = html.unescape(v); v = re.sub("[\t\n ]+", " ", v, re.UNICODE); return v.strip("\t\n ")
def load(p):
    with open(p, newline='', encoding='utf-8') as f:
        r = csv.reader(f); hdr = next(r); rows = [[norm(x) for x in row] for row in r]
    return hdr, rows
base = "/Users/ghassen.aicha@caronsale.de/Desktop/BA/rein-benchmark/rein-datasets"
for ds in sys.argv[1:]:
    dh, d = load(f"{base}/{ds}/dirty.csv"); ch, c = load(f"{base}/{ds}/clean.csv")
    gt = set()
    for row in csv.reader(open(f"{base}/{ds}/actual_errors.csv")):
        try: gt.add((int(row[0]), int(row[1])))
        except Exception: pass
    n, m = len(d), len(dh)
    pos = set((i, j) for i in range(n) for j in range(m) if d[i][j] != c[i][j])
    print(f"== {ds}: rows={n} cols={m} cells={n*m} header_equal={dh==ch} same_set={set(dh)==set(ch)}")
    print(f"  positional diff={len(pos)} ({len(pos)/(n*m):.4f})  actual_errors={len(gt)} ({len(gt)/(n*m):.4f})")
    print(f"  intersection={len(pos&gt)} extra(pos-gt)={len(pos-gt)} missing(gt-pos)={len(gt-pos)}")
    # metrics of a detector that reproduces the positional oracle perfectly, scored vs actual_errors
    tp = len(pos & gt); P = tp/len(pos) if pos else 0; R = tp/len(gt); F = 2*P*R/(P+R) if P+R else 0
    print(f"  perfect-oracle-copy scored vs actual_errors: P={P:.4f} R={R:.4f} F1={F:.4f}")
    if dh != ch and set(dh) == set(ch):
        idx = [ch.index(h) for h in dh]
        al = set((i, j) for i in range(n) for j in range(m) if d[i][j] != c[i][idx[j]])
        print(f"  after name alignment: diff={len(al)} intersection={len(al&gt)} extra={len(al-gt)} missing={len(gt-al)}")
    # per-column dirty counts (actual_errors)
    pc = collections.Counter(j for _, j in gt)
    print(f"  dirty columns (actual_errors)={len(pc)} of {m}; clean columns={[dh[j] for j in range(m) if j not in pc][:10]}")
    rowsdirty = len(set(i for i, _ in gt)); print(f"  dirty rows={rowsdirty} of {n} (rho={rowsdirty/n:.4f})")
