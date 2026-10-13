import csv, html, re, sys
def norm(v):
    v = html.unescape(v)
    v = re.sub("[\t\n ]+", " ", v, flags=re.UNICODE)
    return v.strip()
base = sys.argv[1]
d = list(csv.reader(open(base + '/dirty.csv', encoding='utf-8')))
c = list(csv.reader(open(base + '/clean.csv', encoding='utf-8')))
dh, ch = d[0], c[0]
d, c = d[1:], c[1:]
ae = set()
for row in csv.reader(open(base + '/actual_errors.csv')):
    ae.add((int(row[0]), int(row[1])))
print('shape', len(d), len(dh), len(c), len(ch), 'actual_errors', len(ae))
pos = set(); name = set()
idx = {h: k for k, h in enumerate(ch)}
for i in range(len(d)):
    for j in range(len(dh)):
        if norm(d[i][j]) != norm(c[i][j]): pos.add((i, j))
        if norm(d[i][j]) != norm(c[i][idx[dh[j]]]): name.add((i, j))
print('positional diff', len(pos), 'in AE', len(pos & ae), 'not in AE', len(pos - ae))
print('name-aligned diff', len(name), 'in AE', len(name & ae), 'not in AE', len(name - ae), 'AE missed', len(ae - name))
cells = len(d) * len(dh)
print('cells', cells, 'pos share', round(len(pos)/cells, 4), 'name share', round(len(name)/cells, 4))
dirty_rows_pos = len({i for i, j in pos}); print('rows with pos diff', dirty_rows_pos)
