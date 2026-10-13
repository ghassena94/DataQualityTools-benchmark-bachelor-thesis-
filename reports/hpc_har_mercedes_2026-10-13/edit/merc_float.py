import csv, re, collections
base='mercedes'
d = list(csv.reader(open(base + '/dirty.csv', encoding='utf-8')))
c = list(csv.reader(open(base + '/clean.csv', encoding='utf-8')))
dh, ch = d[0], c[0]; d, c = d[1:], c[1:]
idx = {h: k for k, h in enumerate(ch)}
ae = [(int(r[0]), int(r[1])) for r in csv.reader(open(base + '/actual_errors.csv'))]
ncol=len(dh)
cleanvals=[set(row[idx[dh[j]]].strip() for row in c) for j in range(ncol)]
bset={j for j in range(ncol) if cleanvals[j] <= {'0','1'}}
def kind(v):
    v=v.strip()
    if v=='': return 'blank'
    try: f=float(v)
    except: return 'text'
    if re.fullmatch(r'-?\d+', v): return 'int'
    return 'float'
cnt=collections.Counter(); cntb=collections.Counter(); odd=collections.Counter()
for i,j in ae:
    k=kind(d[i][j]); cnt[k]+=1
    if j in bset: cntb[k]+=1
    if k=='float' and not re.fullmatch(r'-?\d+\.\d*', d[i][j].strip()): odd[d[i][j][:12]]+=1
print('all', cnt); print('binary', cntb); print('odd floats', sum(odd.values()), odd.most_common(5))
print('float in bin share of all AE', round(cntb['float']/len(ae)*100,2), cntb['float'], 'float any', cnt['float'], round(cnt['float']/len(ae)*100,2))
