import csv, collections
base='har'
d=list(csv.reader(open(base+'/dirty.csv'))); c=list(csv.reader(open(base+'/clean.csv')))
dh,ch=d[0],c[0]; d,c=d[1:],c[1:]
assert dh==ch, (dh,ch)
ae=[(int(r[0]),int(r[1])) for r in csv.reader(open(base+'/actual_errors.csv'))]
def dec(v):
    v=v.strip()
    return len(v.split('.')[1]) if '.' in v else 0
def isnum(v):
    try: float(v); return True
    except: return False
maxdec=[max(dec(r[j]) for r in c if isnum(r[j])) if any(isnum(r[j]) for r in c) else None for j in range(len(dh))]
print('clean max decimals', dict(zip(dh,maxdec)))
num=[(i,j) for i,j in ae if d[i][j].strip()!='' and isnum(d[i][j])]
more=[(i,j) for i,j in num if maxdec[j] is not None and dec(d[i][j])>maxdec[j]]
print('non-blank numeric errors', len(num), 'more decimals than any clean', len(more), round(len(more)/len(num)*100,1))
percol=collections.Counter(dh[j] for i,j in ae)
print('errors per column', percol)
for col in ['Index','x','y','z']:
    j=dh.index(col)
    e=[d[i][j] for i,jj in ae if jj==j and d[i][j].strip()!='' and isnum(d[i][j])]
    cd=collections.Counter(dec(r[j]) for r in c if isnum(r[j])); ed=collections.Counter(dec(v) for v in e)
    print(col, 'num errs', len(e), 'err dec dist', sorted(ed.items()), 'clean dec dist top', sorted(cd.items()))
