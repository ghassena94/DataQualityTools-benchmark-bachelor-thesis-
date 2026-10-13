"""Split every robustness run's true positives into the two injected error kinds.
For each kept run under reports/robustness/runs/<scratch>/ it reads the generated dirty.csv,
actual_errors.csv and the detector's detections.csv and counts, per run: blanks injected /
caught, outliers injected / caught, false positives. Writes reports/robustness/mechanism.csv.
Run from the repo root: python3 reports/robustness/mechanism.py"""
import csv, os
import pandas as pd

RUNS = 'reports/robustness/runs'
OUT = 'reports/robustness/mechanism.csv'
res = {r['scratch']: r for r in csv.DictReader(open('reports/robustness/results.csv'))}

out = []
for scratch in sorted(os.listdir(RUNS)):
    d = os.path.join(RUNS, scratch)
    if not os.path.exists(os.path.join(d, 'detections.csv')):
        continue
    dirty = pd.read_csv(os.path.join(d, 'dirty.csv'), dtype=str, keep_default_na=False)
    actual = pd.read_csv(os.path.join(d, 'actual_errors.csv'), header=None, usecols=[0, 1])
    try:
        det = pd.read_csv(os.path.join(d, 'detections.csv'), header=None, usecols=[0, 1])
    except pd.errors.EmptyDataError:   # a run without a single detection
        det = pd.DataFrame(columns=[0, 1])
    actual = set(map(tuple, actual.values.tolist()))
    det = set(map(tuple, det.values.tolist()))
    blank = {c for c in actual if dirty.iat[c[0], c[1]] == ''}
    outl = actual - blank
    r = res.get(scratch, {})
    out.append(dict(scratch=scratch, level=r.get('level', ''),
                    measured_error_rate=r.get('measured_error_rate', ''),
                    outlier_degree=r.get('outlier_degree', ''),
                    detector=r.get('detector', ''), tier=r.get('tier', ''),
                    blanks=len(blank), blanks_caught=len(blank & det),
                    outliers=len(outl), outliers_caught=len(outl & det),
                    false_positives=len(det - actual), detections=len(det)))
pd.DataFrame(out).to_csv(OUT, index=False)
print(pd.DataFrame(out).to_string(index=False))
