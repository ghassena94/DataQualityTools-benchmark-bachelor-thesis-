"""Addendum to the frozen prediction (plan sections 9 and 12): redo the flag-only checks with Raha run 1.

Runs checks/measure_fixes.py and checks/implied_predictions.py unchanged except for two things:
  - Raha flags come from the frozen run-1 files reports/block_d/flags/<ds>/raha.csv where they exist
    (breast_cancer and nasa since 11 Oct); bike and adult keep the disk file until step 7;
  - every output goes to this folder; the frozen checks/expected_pair_verdicts.csv is never touched.
Then lists every expected pair verdict that differs from the frozen file.
No model is trained: everything here follows from the flags alone.

Run in the rein container from /rein:
    python3 reports/block_d_final_plan_2026-10-09/checks/addendum_raha_run1/run_addendum.py
"""
import sys
sys.dont_write_bytecode = True
import contextlib
import os

import pandas as pd

CHK = '/rein/reports/block_d_final_plan_2026-10-09/checks'
HERE = CHK + '/addendum_raha_run1'
FROZEN_RAHA = "'/rein/reports/block_d/flags/{}/raha.csv'.format(ds)"


def patched(name, replacements):
    src = open(CHK + '/' + name).read()
    for old, new in replacements:
        assert src.count(old) == 1, (name, old)
        src = src.replace(old, new)
    return src


def run(name, src, log):
    with open(HERE + '/' + log, 'w') as f, contextlib.redirect_stdout(f):
        exec(compile(src, CHK + '/' + name, 'exec'), {'__name__': '__main__'})
    print('ran {} -> {}'.format(name, os.path.relpath(HERE + '/' + log, '/rein')))


raha_mf = ("(read_cells({0}) if __import__('os').path.exists({0}) "
           "else read_cells('{{}}/{{}}/raha/detections.csv'.format(D, ds)))").format(FROZEN_RAHA)
run('measure_fixes.py', patched('measure_fixes.py', [
    ("OUT = R + '/reports/block_d_final_plan_2026-10-09/checks'", "OUT = '{}'".format(HERE)),
    ("F['raha'] = read_cells('{}/{}/raha/detections.csv'.format(D, ds))", "F['raha'] = " + raha_mf),
]), 'measure_fixes_output.txt')

raha_ip = ("(ns['read_cells']({0}) if __import__('os').path.exists({0}) "
           "else ns['read_cells']('{{}}/{{}}/raha/detections.csv'.format(D, ds)))").format(FROZEN_RAHA)
run('implied_predictions.py', patched('implied_predictions.py', [
    ("MF = json.load(open('/rein/reports/block_d_final_plan_2026-10-09/checks/measure_fixes.json'))",
     "MF = json.load(open('{}/measure_fixes.json'))".format(HERE)),
    ("'raha': ns['read_cells']('{}/{}/raha/detections.csv'.format(D, ds))}", "'raha': " + raha_ip + "}"),
    ("df.to_csv('/rein/reports/block_d_final_plan_2026-10-09/checks/expected_pair_verdicts.csv', index=False)",
     "df.to_csv('{}/expected_pair_verdicts_raha_run1.csv', index=False)".format(HERE)),
]), 'implied_predictions_output.txt')

# ---- what changed against the frozen prediction
old = pd.read_csv(CHK + '/expected_pair_verdicts.csv', dtype=str)
new = pd.read_csv(HERE + '/expected_pair_verdicts_raha_run1.csv', dtype=str)
key = ['dataset', 'policy', 'pair']
m = old.merge(new, on=key, how='outer', suffixes=('_frozen', '_run1'), indicator=True)
assert (m['_merge'] == 'both').all(), 'pair lists differ'
changed_verdict = m[m['expected_frozen'] != m['expected_run1']]
changed_score = m[(m['mechanism_a_frozen'] != m['mechanism_a_run1']) | (m['mechanism_b_frozen'] != m['mechanism_b_run1'])]
print('\nRaha source per dataset:', {ds: 'frozen run 1' if os.path.exists('/rein/reports/block_d/flags/{}/raha.csv'.format(ds))
                                       else 'disk file (until step 7)' for ds in ('breast_cancer', 'nasa', 'bike', 'adult')})
print('pairs: {} | mechanism scores changed: {} | expected verdicts changed: {}'.format(len(m), len(changed_score), len(changed_verdict)))
cols = key + ['mechanism_a_frozen', 'mechanism_b_frozen', 'mechanism_a_run1', 'mechanism_b_run1', 'expected_frozen', 'expected_run1']
if len(changed_score):
    pd.set_option('display.width', 250)
    print(changed_score[cols].to_string(index=False))
print('\npooled expectations with Raha run 1 (frozen §9: GT 19/10/0, delete 16/4/9, impute 12/1/16):')
print(''.join(l for l in open(HERE + '/implied_predictions_output.txt') if 'pooled' in l))
