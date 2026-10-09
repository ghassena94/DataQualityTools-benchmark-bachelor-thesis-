"""D8: can check 1 demand cell identity for adult HoloClean, or only count identity?
The plan assumed HoloClean lower-cases and strips strings. That happens only when HoloClean reads a FILE
(cleaners/holoclean/dataset/table.py:58); the benchmark passes a DataFrame (rein/detectors.py:1148, Source.DF),
which is used unchanged. Checks: (1) would normalisation change anything on adult at all, (2) how REIN reads
dirty.csv (missing values -> SQL NULL), (3) the stale disk file vs the replay vs Table 3.
Run: docker exec -w /rein/reports/block_d_final_plan_2026-10-09/checks/decisions rein-benchmark-rein-1 python3 d8_adult_holoclean.py
"""
import sys
sys.dont_write_bytecode = True
import os, time
import pandas as pd
from mini_driver import ns, D

ds = 'adult'
dirty = pd.read_csv('{}/{}/dirty.csv'.format(D, ds), dtype=str, keep_default_na=False)
A = ns['read_cells']('{}/{}/actual_errors.csv'.format(D, ds))
# (1) values that strip().lower() would change
changed = {c: int((dirty[c] != dirty[c].str.strip().str.lower()).sum()) for c in dirty.columns}
print('(1) cells that strip+lower would change:', {c: v for c, v in changed.items() if v} or 'none')
print('    examples:', {c: dirty[c].iloc[0] for c in ('workclass', 'education', 'gender', 'native_country')})
# (2) missing values as pandas reads them by default (REIN reads dirty.csv with pandas defaults -> NaN -> SQL NULL)
dflt = pd.read_csv('{}/{}/dirty.csv'.format(D, ds), dtype=str)
print('(2) cells pandas reads as missing by default: %d' % int(dflt.isna().sum().sum()))
# replay on raw values, and on strip+lower values
rep = ns['holo'](dirty, ds)
norm = ns['holo'](dirty.apply(lambda s: s.str.strip().str.lower()), ds)
print('    replay raw: %d cells, TP/FP/det %s | replay strip+lower identical: %s' % (len(rep), ns['tp_fp'](rep, A), rep == norm))
print('    Table 3: %s' % (ns['TABLE3'][ds]['holoclean'],))
# (3) the stale disk file
p = '{}/{}/holoclean/detections.csv'.format(D, ds)
disk = ns['read_cells'](p)
print('(3) disk file %s, %d cells, TP/FP/det %s' % (time.strftime('%d %b %H:%M', time.localtime(os.path.getmtime(p))), len(disk), ns['tp_fp'](disk, A)))
print('    disk == replay: %s | only on disk %d | only in replay %d' % (disk == rep, len(disk - rep), len(rep - disk)))
cols = list(dirty.columns)
od = pd.Series([cols[j] for _, j in disk - rep]).value_counts().to_dict()
orr = pd.Series([cols[j] for _, j in rep - disk]).value_counts().to_dict()
print('    by column, only on disk:', od)
print('    by column, only in replay:', orr)
