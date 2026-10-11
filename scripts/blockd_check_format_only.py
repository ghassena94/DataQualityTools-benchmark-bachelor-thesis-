"""Block D, decision D6 safeguard: is "Raha run 1 minus its format-only false positives" the perfect detector?

Format-only FP = a flagged model cell that the ground truth calls correct but whose text differs (800 vs 800.0).
Reads the frozen run-1 flags (reports/block_d/flags/<ds>/raha.csv), model columns only (plan section 3).
If the remainder is not the perfect detector, the plan adds "Raha minus format-only" as one unranked
diagnostic version on that dataset (plan section 13, D6).

Run in the rein container from /rein:
    python3 scripts/blockd_check_format_only.py nasa
"""
import sys
sys.dont_write_bytecode = True

import pandas as pd

SRC = '/rein/reports/block_d_final_plan_2026-10-09/checks/measure_fixes.py'
ns = {}
exec(compile(open(SRC).read().split('report = {}')[0], SRC, 'exec'), ns)
D, CFG = ns['D'], ns['CFG']

for ds in sys.argv[1:] or ['nasa']:
    cfg = CFG[ds]
    clean = pd.read_csv('{}/{}/clean.csv'.format(D, ds), dtype=str, keep_default_na=False)
    dirty = pd.read_csv('{}/{}/dirty.csv'.format(D, ds), dtype=str, keep_default_na=False)
    cols = list(dirty.columns)
    model = {j for j, c in enumerate(cols) if c not in cfg['excl']}
    A = {(i, j) for i, j in ns['read_cells']('{}/{}/actual_errors.csv'.format(D, ds)) if j in model}
    raha = {(i, j) for i, j in ns['read_cells']('/rein/reports/block_d/flags/{}/raha.csv'.format(ds)) if j in model}
    fp = raha - A
    fmt = {(i, j) for i, j in fp if dirty.iat[i, j] != clean.iat[i, j]}
    rest = raha - fmt
    print('== {} (Raha run 1, model columns)'.format(ds))
    print('  Raha flags {}: TP {} of {} errors, FP {} (format-only {}, other {})'.format(
        len(raha), len(raha & A), len(A), len(fp), len(fmt), len(fp - fmt)))
    print('  format-only by column: {}'.format(pd.Series([cols[j] for _, j in fmt]).value_counts().to_dict()))
    print('  Raha minus format-only: TP {} of {}, FP {}'.format(len(rest & A), len(A), len(rest - A)))
    if rest == A:
        print('  => equals the perfect detector: no extra version needed (D6)')
    else:
        missed = A - rest
        print('  => NOT the perfect detector ({} errors missed, {} other FPs):'.format(len(missed), len(rest - A)))
        print('     add "Raha minus format-only" as one unranked diagnostic version on {} (D6)'.format(ds))
        print('     missed errors by column: {}'.format(pd.Series([cols[j] for _, j in missed]).value_counts().to_dict()))
