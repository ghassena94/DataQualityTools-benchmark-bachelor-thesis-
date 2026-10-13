import csv, re, sys
base = sys.argv[1]
d = list(csv.reader(open(base + '/dirty.csv', encoding='utf-8')))
c = list(csv.reader(open(base + '/clean.csv', encoding='utf-8')))
dh, ch = d[0], c[0]; d, c = d[1:], c[1:]
idx = {h: k for k, h in enumerate(ch)}
ae = [(int(r[0]), int(r[1])) for r in csv.reader(open(base + '/actual_errors.csv'))]
print('AE', len(ae))
def isfloat(v):
    return re.fullmatch(r'-?\d+\.\d*', v.strip()) is not None
def isnum(v):
    try: float(v); return True
    except: return False
# clean values per column (by dirty column order, aligned by name)
ncol = len(dh)
cleanvals = [set() for _ in range(ncol)]
for row in c:
    for j in range(ncol):
        cleanvals[j].add(row[idx[dh[j]]].strip())
binary = [j for j in range(ncol) if cleanvals[j] <= {'0','1'}]
print('binary cols', len(binary), 'of', ncol)
bset = set(binary)
fl_any = sum(1 for i,j in ae if isfloat(d[i][j]))
fl_bin = sum(1 for i,j in ae if j in bset and isfloat(d[i][j]))
in_bin = sum(1 for i,j in ae if j in bset)
blank = sum(1 for i,j in ae if d[i][j].strip()=='')
print('floats any col', fl_any, round(fl_any/len(ae)*100,2))
print('floats in 0/1 cols', fl_bin, round(fl_bin/len(ae)*100,2), 'errors in 0/1 cols', in_bin, 'float share there', round(fl_bin/max(in_bin,1)*100,2))
print('blank errors', blank)
# length check
maxlen = [max(len(v) for v in cleanvals[j]) for j in range(ncol)]
print('clean max lens (first 6)', maxlen[:6])
longer = sum(1 for i,j in ae if d[i][j].strip()!='' and len(d[i][j].strip())>maxlen[j])
nb = len(ae)-blank
print('longer than any clean value', longer, 'non-blank', nb, round(longer/max(nb,1)*100,1), 'of all', round(longer/len(ae)*100,1))
