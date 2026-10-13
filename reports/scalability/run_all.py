#!/usr/bin/env python3
"""Host-side runner for the scalability campaign (thesis section 5.2.6).

One fresh container per (dataset, axis, fraction, detector, tier), so the
container's cgroup peak is that run's peak memory. A configuration that fails
(OOM, error, or timeout if TIMEOUT_S is set) at one fraction is not run at
larger fractions. No time limit since 29 Sep 2026 (REIN sets none); the
26-27 Sep campaign ran with a 2 h cap. The db
container's memory is sampled for HoloClean runs. Results accumulate in
reports/scalability/results.csv (written by scripts/scalability_driver.py);
failed runs get a status row from here. Re-runnable: finished runs are skipped.

    python3 reports/scalability/run_all.py [detector ...] [--dataset DS] [--fraction F] [--dry-run]
"""
import argparse
import csv
import os
import re
import subprocess
import threading
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'reports', 'scalability', 'results.csv')
LOG = os.path.join(ROOT, 'reports', 'scalability', 'run_all.log')
DBMEM = os.path.join(ROOT, 'reports', 'scalability', 'db_mem.csv')
TIMEOUT_S = None  # seconds per run; None = no time limit (was 7200 on 26-27 Sep)
FIELDS = ['dataset', 'axis', 'fraction', 'rows', 'cols', 'detector', 'tier',
          'status', 'precision', 'recall', 'f1', 'cell_TP', 'cell_FP', 'cell_FN',
          'cell_FG1', 'detections', 'runtime_s', 'wall_s', 'peak_mem_bytes',
          'baseline_mem_bytes', 'scratch', 'timestamp']

TENTHS = [round(0.1 * i, 1) for i in range(1, 11)]
FIFTHS = [0.2, 0.4, 0.6, 0.8, 1.0]
GE = [('greatExpectations', t) for t in ('dirty_profiled', 'clean_profiled', 'hand_written')]

PLAN = []
for det, tier in GE:
    PLAN += [('har', 'rows', f, det, tier) for f in TENTHS]
    PLAN += [('mercedes', 'cols', f, det, tier) for f in TENTHS]
    PLAN += [('adult', 'rows', f, det, tier) for f in FIFTHS]
PLAN += [('adult', 'rows', f, 'holoclean', '') for f in FIFTHS]
PLAN += [('har', 'rows', f, 'holoclean', '') for f in TENTHS]
PLAN += [('mercedes', 'cols', f, 'holoclean', '') for f in TENTHS]
PLAN += [('adult', 'rows', f, 'raha', '') for f in FIFTHS]
PLAN += [('har', 'rows', f, 'raha', '') for f in TENTHS]
PLAN += [('mercedes', 'cols', f, 'raha', '') for f in TENTHS]


def log(msg):
    line = '{} {}'.format(time.strftime('%Y-%m-%d %H:%M:%S'), msg)
    print(line, flush=True)
    with open(LOG, 'a') as f:
        f.write(line + '\n')


def load_results():
    if not os.path.exists(OUT):
        return []
    with open(OUT, newline='') as f:
        return list(csv.DictReader(f))


def key(r):
    return (r['dataset'], r['axis'], r['detector'], r['tier'])


def scratch_name(ds, axis, frac, det='', tier=''):
    return '{}_{}{}_{}'.format(ds, 'r' if axis == 'rows' else 'c', int(round(frac * 100)),
                               det + ('_' + tier if tier else ''))


def append_status(ds, axis, frac, det, tier, status, wall):
    new = not os.path.exists(OUT)
    with open(OUT, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({'dataset': ds, 'axis': axis, 'fraction': frac, 'detector': det, 'tier': tier,
                    'status': status, 'wall_s': wall, 'scratch': scratch_name(ds, axis, frac, det, tier),
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')})


def sample_db(stop, holder):
    while not stop.is_set():
        try:
            out = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{.MemUsage}}',
                                  'rein-benchmark-db-1'], capture_output=True, text=True, timeout=20).stdout
            m = re.match(r'\s*([\d.]+)([KMG]i?B)', out)
            if m:
                mult = {'B': 1, 'KB': 1e3, 'KiB': 1024, 'MB': 1e6, 'MiB': 1024 ** 2,
                        'GB': 1e9, 'GiB': 1024 ** 3}[m.group(2)]
                holder[0] = max(holder[0], float(m.group(1)) * mult)
        except Exception:  # noqa: BLE001
            pass
        stop.wait(5)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('detectors', nargs='*', help='optional detector filter, e.g. greatExpectations holoclean')
    p.add_argument('--dataset', help='run only this dataset')
    p.add_argument('--fraction', type=float, help='run only this fraction, e.g. 0.4')
    p.add_argument('--dry-run', action='store_true', help='print what would run, change nothing')
    a = p.parse_args()
    for ds, axis, frac, det, tier in PLAN:
        if (a.detectors and det not in a.detectors) or (a.dataset and ds != a.dataset) \
                or (a.fraction is not None and frac != a.fraction):
            continue
        rows = load_results()
        k = (ds, axis, det, tier)
        done = [r for r in rows if key(r) == k and float(r['fraction']) == frac]
        if any(r['status'] == 'ok' for r in done):
            continue
        failed_smaller = [r for r in rows if key(r) == k and r['status'] != 'ok'
                          and r['status'] != 'skipped' and float(r['fraction']) < frac]
        if failed_smaller and a.dry_run:
            print('would skip {} {} {} {} {}: failed at {}'.format(ds, axis, frac, det, tier,
                                                                  failed_smaller[0]['fraction']))
            continue
        if failed_smaller:
            log('skip {} {} {} {} {}: failed at {}'.format(ds, axis, frac, det, tier,
                                                            failed_smaller[0]['fraction']))
            append_status(ds, axis, frac, det, tier, 'skipped', 0)
            continue
        scratch = scratch_name(ds, axis, frac, det, tier)
        cmd = ['docker', 'compose', 'run', '--rm', '-T', '-e', 'EXPECTATION_TIER=' + (tier or 'hand_written'), 'rein']
        if TIMEOUT_S:
            cmd += ['timeout', str(TIMEOUT_S)]
        cmd += ['python3', 'scripts/scalability_driver.py',
                '--dataset', ds, '--axis', axis, '--fraction', str(frac), '--detector', det]
        if tier:
            cmd += ['--tier', tier]
        if a.dry_run:
            print('would run', ' '.join(cmd))
            continue
        log('run  {} {} {} {} {}'.format(ds, axis, frac, det, tier))
        stop, holder = threading.Event(), [0.0]
        th = threading.Thread(target=sample_db, args=(stop, holder), daemon=True)
        th.start()
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        wall = round(time.time() - t0, 1)
        stop.set()
        th.join(timeout=30)
        with open(DBMEM, 'a') as f:
            f.write('{},{},{},{},{},{}\n'.format(ds, axis, frac, det, tier, int(holder[0])))
        tail = '\n'.join(proc.stdout.strip().splitlines()[-3:])
        if proc.returncode != 0:
            status = {124: 'timeout', 137: 'oom_killed'}.get(proc.returncode,
                                                                'exit_{}'.format(proc.returncode))
            rows_now = load_results()
            if not any(key(r) == k and float(r['fraction']) == frac and r['scratch'] == scratch
                       for r in rows_now[len(rows):]):
                append_status(ds, axis, frac, det, tier, status, wall)
            log('FAIL {} {} {} {} {}: {} after {} s | {}'.format(ds, axis, frac, det, tier, status, wall,
                                                                proc.stderr.strip().splitlines()[-1:]))
        else:
            log('ok   {} {} {} {} {}: {} s | {}'.format(ds, axis, frac, det, tier, wall, tail.splitlines()[-1:]))
        subprocess.run(['rm', '-rf', os.path.join(ROOT, 'rein-datasets', scratch)])
    if not a.dry_run:
        log('campaign finished')


if __name__ == '__main__':
    main()
