"""Do the reference rankings change when flags are restricted to model columns (fix 1)?
Four references per dataset: cell F1 all columns (Table 3), cell F1 schema columns only,
row F1 (Table 7 style), model-visible cell F1 (schema columns, truth = errors whose parsed value differs).
Run in the rein container; reuses the flag-set builders of measure_fixes.py.
"""
import importlib.util, math, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings('ignore'); sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('mf_src', '/rein/reports/block_d_final_plan_2026-10-09/checks/measure_fixes.py')
src = open(spec.origin).read().split('report = {}')[0]      # helpers + CFG only, no measurement loop
ns = {}
exec(compile(src, spec.origin, 'exec'), ns)
D, CFG, CONFIGS = ns['D'], ns['CFG'], ns['CONFIGS']


def f1(det, truth):
    tp = len(det & truth)
    if not det or not truth or tp == 0:
        return 0.0
    p, r = tp / len(det), tp / len(truth)
    return 2 * p * r / (p + r)


def parsed(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except ValueError:
        return None


for ds, cfg in CFG.items():
    clean = pd.read_csv('{}/{}/clean.csv'.format(D, ds), dtype=str, keep_default_na=False)
    dirty = pd.read_csv('{}/{}/dirty.csv'.format(D, ds), dtype=str, keep_default_na=False)
    A = ns['read_cells']('{}/{}/actual_errors.csv'.format(D, ds))
    cols = list(dirty.columns); d = len(cols)
    excl = {cols.index(c) for c in cfg['excl']}
    schema = set(range(d)) - excl
    F = {'ge_dirty_profiled': ns['ge'](dirty, ns['prof'].profile_expectations(dirty)),
         'ge_clean_profiled': ns['ge'](dirty, ns['prof'].profile_expectations(clean)),
         'ge_hand_written': ns['ge'](dirty, ns['hw'].get(ds, {}).get('hand_written', [])),
         'holoclean': ns['holo'](dirty, ds),
         'raha': ns['read_cells']('{}/{}/raha/detections.csv'.format(D, ds))}
    A_s = {x for x in A if x[1] in schema}
    # model-visible truth: schema error cells whose numeric value (or text, for non-numeric) really changes
    A_mv = set()
    for (i, j) in A_s:
        a, b = parsed(dirty.iat[i, j]), parsed(clean.iat[i, j])
        if a is None or b is None or not math.isclose(a, b, rel_tol=1e-6):
            A_mv.add((i, j))
    rowsA = {i for i, _ in A}
    out = []
    for c in CONFIGS:
        fl = F[c]; fs = {x for x in fl if x[1] in schema}
        out.append((c, f1(fl, A), f1(fs, A_s), f1({i for i, _ in fl}, rowsA), f1(fs, A_mv)))
    df = pd.DataFrame(out, columns=['config', 'cell_all(T3)', 'cell_schema', 'row(T7)', 'model_visible']).set_index('config')
    print('\n==', ds, '| errors all', len(A), 'schema', len(A_s), 'model-visible', len(A_mv))
    print(df.round(4).to_string())
    for col in df.columns:
        order = df[col].sort_values(ascending=False)
        print('  %-14s %s' % (col, ' > '.join('%s(%.3f)' % (k.replace('ge_', '').replace('_profiled', '').replace('_written', ''), v) for k, v in order.items())))
