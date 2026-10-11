"""Block D, steps 2 and 7: freeze one flag set after plan check 1.

Copies datasets/<ds>/<detector>/detections.csv to reports/block_d/flags/<ds>/<config>.csv, but only if
  1. every cell is unique and inside the table,
  2. TP / FP / detections equal Table 3 exactly,
  3. GE and HoloClean: the cells equal the replay (plan section 7; D8: adult too).
     Raha has no replay, so its counts must match (2) and nothing more can be checked.
GE writes all three tiers to the same file, so the config named here must be the tier that ran last;
check 3 catches a wrong name. A frozen file is never overwritten; each freeze appends a row to
reports/block_d/flags/MANIFEST.csv. Make the copy read-only on the host afterwards (the script prints the
chmod); Docker Desktop does not pass chmod through to a macOS bind mount.

Run in the rein container from /rein:
    python3 scripts/blockd_freeze_flags.py <dataset> <config> [<config> ...]
    config: ge_dirty_profiled | ge_clean_profiled | ge_hand_written | holoclean | raha
"""
import sys
sys.dont_write_bytecode = True
import csv
import datetime
import hashlib
import os
import shutil
import stat

import pandas as pd

R = '/rein'
SRC = R + '/reports/block_d_final_plan_2026-10-09/checks/measure_fixes.py'
ns = {}
exec(compile(open(SRC).read().split('report = {}')[0], SRC, 'exec'), ns)   # replay helpers + Table 3 counts
D, TABLE3 = ns['D'], ns['TABLE3']
OUT = R + '/reports/block_d/flags'
DETECTOR_DIR = dict(ge_dirty_profiled='greatExpectations', ge_clean_profiled='greatExpectations',
                    ge_hand_written='greatExpectations', holoclean='holoclean', raha='raha')
MANIFEST_COLS = ['dataset', 'config', 'frozen_file', 'detections', 'tp', 'fp', 'sha256', 'source_file',
                 'source_mtime', 'table3', 'replay', 'frozen_at']


def replay(ds, config, dirty, clean):
    if config == 'ge_dirty_profiled':
        return ns['ge'](dirty, ns['prof'].profile_expectations(dirty))
    if config == 'ge_clean_profiled':
        return ns['ge'](dirty, ns['prof'].profile_expectations(clean))
    if config == 'ge_hand_written':
        return ns['ge'](dirty, ns['hw'].get(ds, {}).get('hand_written', []))
    if config == 'holoclean':
        return ns['holo'](dirty, ds)
    return None


def freeze(ds, config):
    src = '{}/{}/{}/detections.csv'.format(D, ds, DETECTOR_DIR[config])
    dst = '{}/{}/{}.csv'.format(OUT, ds, config)
    if os.path.exists(dst):
        sys.exit('REFUSED {} {}: {} is frozen already'.format(ds, config, dst))
    dirty = pd.read_csv('{}/{}/dirty.csv'.format(D, ds), dtype=str, keep_default_na=False)
    clean = pd.read_csv('{}/{}/clean.csv'.format(D, ds), dtype=str, keep_default_na=False)
    A = ns['read_cells']('{}/{}/actual_errors.csv'.format(D, ds))
    n, d = dirty.shape
    try:
        raw = pd.read_csv(src, header=None)
        pairs = list(zip(raw[0].astype(int), raw[1].astype(int)))
    except pd.errors.EmptyDataError:
        pairs = []
    cells = set(pairs)
    problems = []
    if len(cells) != len(pairs):
        problems.append('{} duplicate cells'.format(len(pairs) - len(cells)))
    outside = [c for c in cells if not (0 <= c[0] < n and 0 <= c[1] < d)]
    if outside:
        problems.append('{} cells outside the {} x {} table, e.g. {}'.format(len(outside), n, d, outside[0]))
    got, want = ns['tp_fp'](cells, A), TABLE3[ds][config]
    t3 = got == tuple(want)
    if not t3:
        problems.append('TP/FP/detections {} but Table 3 says {}'.format(got, tuple(want)))
    rep = replay(ds, config, dirty, clean)
    if rep is None:
        rp = 'n/a (no replay for Raha)'
    elif rep == cells:
        rp = 'identical'
    else:
        rp = 'DIFFERS'
        problems.append('replay differs: {} cells only in the file, {} only in the replay'.format(
            len(cells - rep), len(rep - cells)))
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(src)).strftime('%Y-%m-%d %H:%M:%S')
    print('{:<14} {:<18} file {} ({})  TP/FP/det {}  Table 3 {}  replay {}'.format(
        ds, config, src.replace(D, 'datasets'), mtime, got, 'match' if t3 else 'MISMATCH', rp))
    if problems:
        sys.exit('NOT FROZEN {} {}:\n  - {}'.format(ds, config, '\n  - '.join(problems)))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    os.chmod(dst, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    sha = hashlib.sha256(open(dst, 'rb').read()).hexdigest()
    man = OUT + '/MANIFEST.csv'
    new = not os.path.exists(man)
    with open(man, 'a', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(MANIFEST_COLS)
        w.writerow([ds, config, os.path.relpath(dst, R), got[2], got[0], got[1], sha, os.path.relpath(src, D),
                    mtime, 'match', rp, datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')])
    print('{:<14} {:<18} FROZEN -> {} (sha256 {}...)'.format(ds, config, os.path.relpath(dst, R), sha[:12]))
    # Docker Desktop does not pass chmod through to a macOS bind mount: make it read-only on the host.
    print('{:<14} {:<18} on the host run: chmod 444 {}'.format(ds, config, os.path.relpath(dst, R)))


if __name__ == '__main__':
    if len(sys.argv) < 3 or any(c not in DETECTOR_DIR for c in sys.argv[2:]):
        sys.exit(__doc__)
    for config in sys.argv[2:]:
        freeze(sys.argv[1], config)
