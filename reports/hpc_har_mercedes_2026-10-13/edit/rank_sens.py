import csv
RL='/Users/ghassen.aicha@caronsale.de/Desktop/BA/rein-benchmark/results/runs_log.csv'
CFG={'GreatExpectations (dirty profiled)':'dirty','GreatExpectations (clean profiled)':'clean',
     'GreatExpectations (hand written)':'hand','HoloClean':'holo','Raha':'raha'}
data={}  # ds -> cfg -> (TP,FP,FN,pi)
for r in csv.DictReader(open(RL)):
    if r['tool'] not in CFG: continue
    pi=int(r['injected_errors'])/int(r['cells'])
    data.setdefault(r['dataset'],{})[CFG[r['tool']]]=(int(r['TP']),int(r['FP']),int(r['FN']),pi)
def f1(tp,fp,fn):
    return 0.0 if tp==0 else 2*tp/(2*tp+fp+fn)
def fg1(tp,fp,fn,pi):
    if tp==0: return None
    F=f1(tp,fp,fn); return (F-pi)/((1-pi)*F)
# har / mercedes provisional
har_pi=51845/350000; mer_pi=301972/1591002
data['har']={'dirty':(10502,0,41343,har_pi),'clean':(11142,0,40703,har_pi),'hand':(22400,0,29445,har_pi),'holo':(0,0,51845,har_pi),
             'raha':('F',0.8792,0.97614)}   # 90% rows scalability row 115
data['mercedes']={'dirty':(1774,0,300198,mer_pi),'clean':(1774,0,300198,mer_pi),'hand':(301972,0,0,mer_pi),'holo':(0,0,301972,mer_pi),
             'raha':('F',0.99923,0.99983)} # 40% cols row 125
# exact raha F1 for har/mer from TP/FP/FN of the fraction runs
data['har']['raha']=('F',2*39039/(2*39039+3162+7565),None)
data['mercedes']['raha']=('F',2*117821/(2*117821+19+150),None)
def scores(ds,variant=None):
    out={}
    for c,v in data[ds].items():
        if v[0]=='F':
            F=v[1]
            # FG1 from the fraction's own pi: use the logged FG1
            G={'har':0.976142,'mercedes':0.999828}[ds] if v[2] is None else v[2]
            out[c]=(F,G)
        else:
            out[c]=(f1(*v[:3]),fg1(*v))
    if variant=='mer_zero' and ds=='mercedes': out['raha']=(0.0,None)
    if variant=='mer_oracle' and ds=='mercedes':
        tp=301972; fp=366191; F=2*tp/(2*tp+fp); out['raha']=(F,(F-mer_pi)/((1-mer_pi)*F))
    return out
def ranks(sc):
    items=sorted(sc.items(),key=lambda kv:-kv[1][0]); r={}
    i=0
    while i<len(items):
        j=i
        while j+1<len(items) and abs(items[j+1][1][0]-items[i][1][0])<1e-9: j+=1
        for k in range(i,j+1): r[items[k][0]]=(i+1+j+1)/2
        i=j+1
    return r
def table(dsl,variant=None,label=''):
    cfgs=['raha','hand','clean','holo','dirty']
    mg={c:0 for c in cfgs}; mr={c:0 for c in cfgs}; best={c:0 for c in cfgs}; above={c:0 for c in cfgs}; undef={c:0 for c in cfgs}
    for ds in dsl:
        sc=scores(ds,variant); rk=ranks(sc)
        for c in cfgs:
            G=sc[c][1]; mg[c]+= (G if (G is not None and G>0) else 0); mr[c]+=rk[c]
            if rk[c]==min(rk.values()) or abs(sc[c][0]-max(v[0] for v in sc.values()))<1e-9: best[c]+=1
            if G is not None and G>0.5: above[c]+=1
            if G is None: undef[c]+=1
    n=len(dsl); print(f'--- {label} (n={n})')
    for c in sorted(cfgs,key=lambda c:-mg[c]):
        print(f'{c:6s} meanFG1 {mg[c]/n:.4f}  meanRank {mr[c]/n:.3f}  best(F1 max incl ties) {best[c]}  FG1>0.5 {above[c]}  undefined {undef[c]}')
seven=['beers','soilmoisture','bike','breast_cancer','nasa','smartfactory','adult']
import copy
base=copy.deepcopy(data)
# infeasible = F1 0, FG1 0 (undefined->0), strict last rank vs tie-rank
def run(dsl, infeasible, strict):
    cfgs=['raha','hand','clean','holo','dirty']; mg={c:0 for c in cfgs}; mr={c:0 for c in cfgs}
    for ds in dsl:
        sc=scores(ds)
        if ds in infeasible: sc['raha']=(0.0,None)
        rk=ranks(sc)
        if ds in infeasible and strict: 
            # Raha alone in last place, others keep their order among themselves
            others={c:v for c,v in sc.items() if c!='raha'}; rk=ranks(others); rk['raha']=5
        for c in cfgs:
            G=sc[c][1]; mg[c]+=(G if (G is not None and G>0) else 0); mr[c]+=rk[c]
    n=len(dsl)
    return {c:(round(mg[c]/n,3), round(mr[c]/n,2)) for c in cfgs}
for lab,dsl,inf in [('8 +har infeasible',seven+['har'],{'har'}),('9 both infeasible',seven+['har','mercedes'],{'har','mercedes'})]:
    for strict in (True,False):
        print(lab,'strict' if strict else 'tied', run(dsl,inf,strict))
print('7', run(seven,set(),False))
print('8 largest fraction', run(seven+['har'],set(),False))
