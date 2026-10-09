"""Expected pair verdicts for the Block D prediction (fix for Fable B1).

For every dataset x policy, rank the items by a pre-registered *mechanism score* computed
from the flags alone, then compare each pair with the primary reference (a) = published
Table 3 cell F1. Output: expected concordant / discordant / undetermined pairs.

Mechanism scores (higher = better S2 expected), items whose model-column flag sets are identical merged:
  GT repair : recall on model-visible errors (false flags cost nothing)
  delete    : degenerate on all 10 seeds -> last; zero flags -> equals the floor ('floor');
              otherwise row precision = share of flagged rows (model columns) that hold a model-visible error
  impute    : degenerate -> last; otherwise net parsable repairs = parsable feature TPs - parsable feature FPs
              (an FP overwrites a correct value; a fully flagged column becomes constant), plus, when
              labels are flagged, the label row precision as in delete; zero net and no label flags -> 'floor'
'floor' items are undetermined against every non-floor item (the sign of their difference to the floor is
exactly what training decides). Raha uses the disk file (not run 1); regenerate after step 2.
Run in the rein container.
"""
import importlib.util, itertools, json, math, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings('ignore'); sys.dont_write_bytecode = True
SRC = '/rein/reports/block_d_final_plan_2026-10-09/checks/measure_fixes.py'
ns = {}
exec(compile(open(SRC).read().split('report = {}')[0], SRC, 'exec'), ns)
D, CFG, CONFIGS = ns['D'], ns['CFG'], ns['CONFIGS']
MF = json.load(open('/rein/reports/block_d_final_plan_2026-10-09/checks/measure_fixes.json'))
T3 = {  # published Table 3 cell F1 (thesis), primary reference (a)
    'breast_cancer': dict(ge_dirty_profiled=.554, ge_clean_profiled=.603, ge_hand_written=.803, holoclean=.132, raha=.618),
    'nasa': dict(ge_dirty_profiled=.079, ge_clean_profiled=.689, ge_hand_written=.964, holoclean=.159, raha=.430),
    'bike': dict(ge_dirty_profiled=0., ge_clean_profiled=0., ge_hand_written=.829, holoclean=.216, raha=.769),
    'adult': dict(ge_dirty_profiled=0., ge_clean_profiled=0., ge_hand_written=0., holoclean=.005, raha=.226),
}
SHORT = dict(ge_dirty_profiled='GE-dirty', ge_clean_profiled='GE-clean', ge_hand_written='GE-hand', holoclean='HoloClean', raha='Raha')


def num(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except ValueError:
        return None


rows_out, summary = [], {}
for ds, cfg in CFG.items():
    clean = pd.read_csv('{}/{}/clean.csv'.format(D, ds), dtype=str, keep_default_na=False)
    dirty = pd.read_csv('{}/{}/dirty.csv'.format(D, ds), dtype=str, keep_default_na=False)
    A = ns['read_cells']('{}/{}/actual_errors.csv'.format(D, ds))
    cols = list(dirty.columns); d = len(cols)
    lab = cols.index(cfg['label']); excl = {cols.index(c) for c in cfg['excl']}
    schema = set(range(d)) - excl; feats = schema - {lab}
    A_mv = set()
    for (i, j) in A:
        if j in schema:
            a, b = num(dirty.iat[i, j]), num(clean.iat[i, j])
            if a is None or b is None or not math.isclose(a, b, rel_tol=1e-6):
                A_mv.add((i, j))
    rows_err = {i for i, _ in A_mv}
    F = {'ge_dirty_profiled': ns['ge'](dirty, ns['prof'].profile_expectations(dirty)),
         'ge_clean_profiled': ns['ge'](dirty, ns['prof'].profile_expectations(clean)),
         'ge_hand_written': ns['ge'](dirty, ns['hw'].get(ds, {}).get('hand_written', [])),
         'holoclean': ns['holo'](dirty, ds),
         'raha': ns['read_cells']('{}/{}/raha/detections.csv'.format(D, ds))}
    F = {c: {x for x in s if x[1] in schema} for c, s in F.items()}
    # merge identical sets into items
    items = {}
    for c in CONFIGS:
        key = frozenset(F[c])
        items.setdefault(key, []).append(c)
    items = [v for v in items.values()]
    per = MF[ds]['per_seed']

    def deg(c, pol):
        return all(per[c][pol + '_degenerate'])

    mech = {}
    for it in items:
        c = it[0]; fl = F[c]
        rec = len(fl & A_mv) / len(A_mv) if A_mv else 0.0
        frows = {i for i, _ in fl}
        if deg(c, 'delete_schema'):
            dl = -math.inf
        elif not fl:
            dl = 'floor'
        else:
            dl = len(frows & rows_err) / len(frows)
        if deg(c, 'impute'):
            im = -math.inf
        else:
            tp_p = sum(1 for (i, j) in fl & A_mv if j in feats and num(dirty.iat[i, j]) is not None)
            fp_p = sum(1 for (i, j) in fl - A_mv if j in feats and num(dirty.iat[i, j]) is not None)
            lrows = {i for i, j in fl if j == lab}
            net = tp_p - fp_p
            if lrows:      # label flags drop rows: score them like delete (row precision), scaled to cells
                net += len(lrows & {i for i, j in A_mv if j == lab}) - len(lrows - {i for i, j in A_mv if j == lab})
            im = 'floor' if (net == 0 and not lrows) else net
        mech[tuple(it)] = dict(gt=rec, delete=dl, impute=im)
    ref = {tuple(it): max(T3[ds][c] for c in it) for it in items}

    def cmp(x, y):
        if x == 'floor' or y == 'floor':
            return None if x != y else 0
        return (x > y) - (x < y)

    summary[ds] = {}
    for pol in ('gt', 'delete', 'impute'):
        C = Dd = U = 0
        for a, b in itertools.combinations(ref, 2):
            r = (ref[a] > ref[b]) - (ref[a] < ref[b])
            m = cmp(mech[a][pol], mech[b][pol])
            if m is None or m == 0 or r == 0:
                verdict = 'undetermined'; U += 1
            elif m == r:
                verdict = 'concordant'; C += 1
            else:
                verdict = 'discordant'; Dd += 1
            name = lambda it: '='.join(SHORT[c] for c in it)
            rows_out.append(dict(dataset=ds, policy=pol, pair='%s vs %s' % (name(a), name(b)),
                                 reference_a='%s > %s' % ((name(a), name(b)) if r > 0 else (name(b), name(a))) if r else 'tie',
                                 mechanism_a=mech[a][pol], mechanism_b=mech[b][pol], expected=verdict))
        summary[ds][pol] = (C, Dd, U)

df = pd.DataFrame(rows_out)
fmt = lambda v: v if isinstance(v, str) else ('degenerate' if v == -math.inf else round(v, 3))
df['mechanism_a'] = df['mechanism_a'].map(fmt); df['mechanism_b'] = df['mechanism_b'].map(fmt)
df.to_csv('/rein/reports/block_d_final_plan_2026-10-09/checks/expected_pair_verdicts.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
print(df.to_string(index=False))
print()
for pol in ('gt', 'delete', 'impute'):
    C = sum(summary[ds][pol][0] for ds in summary); Dd = sum(summary[ds][pol][1] for ds in summary); U = sum(summary[ds][pol][2] for ds in summary)
    print('%-7s per dataset (C/D/U) %s | pooled C %d D %d U %d of %d -> concordant among determined %.2f, of all pairs %.2f' % (
        pol, {k: v[pol] for k, v in summary.items()}, C, Dd, U, C + Dd + U, C / max(C + Dd, 1), C / (C + Dd + U)))
