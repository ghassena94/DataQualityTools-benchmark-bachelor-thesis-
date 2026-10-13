import csv, sys
for base in sys.argv[1:]:
    d=list(csv.reader(open(base+'/dirty.csv',encoding='utf-8',errors='replace'))); c=list(csv.reader(open(base+'/clean.csv',encoding='utf-8',errors='replace')))
    dh,ch=d[0],c[0]; d,c=d[1:],c[1:]
    idx={h:k for k,h in enumerate(ch)}
    if not all(h in idx for h in dh): print(base,'header mismatch'); continue
    ae=[(int(r[0]),int(r[1])) for r in csv.reader(open(base+'/actual_errors.csv'))]
    maxlen=[max(len(r[idx[dh[j]]].strip()) for r in c) for j in range(len(dh))]
    nb=[(i,j) for i,j in ae if d[i][j].strip()!='']
    longer=sum(1 for i,j in nb if len(d[i][j].strip())>maxlen[j])
    print(base,'AE',len(ae),'nonblank',len(nb),'longer',longer, round(longer/max(len(nb),1)*100,1),'% of nonblank,', round(longer/len(ae)*100,1),'% of all')
