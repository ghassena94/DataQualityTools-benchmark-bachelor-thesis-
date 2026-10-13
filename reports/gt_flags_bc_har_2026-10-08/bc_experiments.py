"""breast_cancer: where do the false positives of the three GE suites come from,
and how much of the score depends on errors injected into identifier columns?

Read-only on the repo. GE replay = the real profiler + hand-written suite, evaluated
with the legacy PandasDataset semantics (validated: reproduces the stored counts).
"""
import importlib.util, math, sys
import pandas as pd

sys.dont_write_bytecode = True
REPO = '/Users/ghassen.aicha@caronsale.de/Desktop/BA/rein-benchmark'
DS = REPO + '/rein-datasets/breast_cancer/'
UCI = '/Users/ghassen.aicha@caronsale.de/Desktop/BA/REIN DATASETS/breast_cancer/original/breast-cancer-wisconsin.data'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


prof = load_module('prof', REPO + '/rein/auxiliaries/expectations_profiler.py')
hw = load_module('hw', REPO + '/rein/auxiliaries/expectations_dictionary_local.py').DATASET_EXPECTATIONS


def ge(df, exps):
    det, why = set(), {}
    for e in exps:
        col = e['column']
        if col not in df.columns:
            continue
        j = df.columns.get_loc(col); s = df[col].astype(str); k = e['expectation']; kw = e['kwargs']
        if k == 'expect_column_values_to_match_regex':
            bad = ~s.str.contains(kw['regex'], regex=True)
        elif k == 'expect_column_values_to_not_match_regex':
            bad = s.str.contains(kw['regex'], regex=True)
        elif k == 'expect_column_values_to_be_in_set':
            bad = ~s.isin(kw['value_set'])
        elif k == 'expect_column_values_to_not_be_in_set':
            bad = s.isin(kw['value_set'])
        elif k == 'expect_column_values_to_be_unique':
            bad = s.duplicated(keep=False)
        else:
            raise ValueError(k)
        for i in df.index[bad.values]:
            det.add((i, j)); why.setdefault((i, j), k.replace('expect_column_values_to_', ''))
    return det, why


def score(det, truth, pi):
    tp = len(det & truth); p = tp / len(det) if det else 0; r = tp / len(truth)
    f = 2 * p * r / (p + r) if p + r else 0
    fg = (f - pi) / ((1 - pi) * f) if f else float('nan')
    return dict(det=len(det), TP=tp, FP=len(det) - tp, P=round(p, 3), R=round(r, 3), F1=round(f, 3), FG1=round(fg, 3))


clean = pd.read_csv(DS + 'clean.csv', dtype=str, keep_default_na=False)
dirty = pd.read_csv(DS + 'dirty.csv', dtype=str, keep_default_na=False)
ae = pd.read_csv(DS + 'actual_errors.csv', header=None, names=['r', 'c', 'v'])
A = set(zip(ae.r, ae.c))
cols = list(clean.columns)
N, d = clean.shape
print('shape', clean.shape, 'errors', len(A), 'eps', round(len(A) / (N * d), 4))
print('errors per column:', {cols[c]: n for c, n in ae.c.value_counts().sort_index().items()})

suites = {
    'dirty_profiled': prof.profile_expectations(dirty),
    'clean_profiled': prof.profile_expectations(clean),
    'hand_written': hw['breast_cancer']['hand_written'],
}
dets = {}
for name, exps in suites.items():
    det, why = ge(dirty, exps)
    dets[name] = det
    s = score(det, A, len(A) / (N * d))
    print('\n==', name, s)
    fp = sorted(det - A)
    print('   FP by column:', pd.Series([cols[c] for _, c in fp]).value_counts().to_dict())
    print('   FP by rule:', pd.Series([why[x] for x in fp]).value_counts().to_dict())
    print('   FP dirty values:', pd.Series([dirty.iat[r, c] for r, c in fp]).value_counts().head(5).to_dict())

# -- 1. the '?' cells
q_clean = clean['Bare Nuclei'] == '?'
print('\n## ? cells: clean has', int(q_clean.sum()))
uci = pd.read_csv(UCI, header=None, dtype=str)
uci_q = uci[uci[6] == '?']
print('UCI file rows with ? in Bare Nuclei:', len(uci_q))
bn = cols.index('Bare Nuclei')
for r in clean.index[q_clean]:
    in_gt = (r, bn) in A
    flagged = {k: (r, bn) in v for k, v in dets.items()}
    print('  row %3d  id %-8s clean %-2r dirty %-4r  in GT: %-5s  flagged dp/cp/hw: %s' % (
        r, clean.at[r, 'Sample code number'], clean.at[r, 'Bare Nuclei'], dirty.at[r, 'Bare Nuclei'], in_gt,
        '/'.join('Y' if flagged[k] else '-' for k in suites)))
print('UCI ids with ?:', sorted(uci_q[0].tolist()) == sorted(clean.loc[q_clean, 'Sample code number'].tolist()))

# -- 2. the hand-written FPs in the row index: each is the untouched twin of an injected duplicate
print('\n## hand-written FPs in Unnamed: 0')
hw_fp = sorted(x for x in dets['hand_written'] - A if x[1] == 0)
for r, _ in hw_fp[:5]:
    v = dirty.iat[r, 0]
    twins = [t for t in dirty.index[dirty['Unnamed: 0'] == v] if t != r]
    for t in twins:
        print('  row %3d index %-4s (clean, untouched)  <-> row %3d: clean index %-4s, dirty %-4s, injected error: %s' % (
            r, v, t, clean.iat[t, 0], dirty.iat[t, 0], (t, 0) in A))
n_twin = sum(1 for r, _ in hw_fp if any((t, 0) in A for t in dirty.index[dirty['Unnamed: 0'] == dirty.iat[r, 0]] if t != r))
print('  FPs explained by an injected twin:', n_twin, 'of', len(hw_fp))

# -- 3. what kind of errors sit in the two identifier columns
for c in (0, 1):
    errs = [(r, c) for r, cc in A if cc == c]
    kinds = pd.Series(['blank' if dirty.iat[r, c] == '' else
                       ('not digits' if not dirty.iat[r, c].isdigit() else
                        ('value of another row' if dirty.iat[r, c] in set(clean.iloc[:, c]) else 'new number'))
                       for r, _ in errs]).value_counts().to_dict()
    det_by = {k: len(set(errs) & v) for k, v in dets.items()}
    print('\n## errors in', cols[c], len(errs), kinds, 'found by', det_by)
    for r, _ in errs[:3]:
        print('   e.g. row %d: clean %r -> dirty %r' % (r, clean.iat[r, c], dirty.iat[r, c]))

# -- 4. sensitivity: as published / identifiers excluded / ? counted as real errors
hc = pd.read_csv(DS + 'holoclean/detections.csv', header=None, names=['r', 'c', 'v'])
dets['HoloClean'] = set(zip(hc.r, hc.c))
ids = {0, 1}
Q = {(r, bn) for r in clean.index[q_clean] if dirty.at[r, 'Bare Nuclei'] == '?'}
rows = []
for name, det in dets.items():
    a = score(det, A, len(A) / (N * d))
    A2 = {x for x in A if x[1] not in ids}; det2 = {x for x in det if x[1] not in ids}
    b = score(det2, A2, len(A2) / (N * (d - 2)))
    A3 = A | Q
    c3 = score(det, A3, len(A3) / (N * d))
    rows.append(dict(config=name, **{'pub_' + k: a[k] for k in ('det', 'TP', 'FP', 'P', 'F1', 'FG1')},
                     **{'noid_' + k: b[k] for k in ('TP', 'FP', 'P', 'R', 'F1', 'FG1')},
                     **{'q_' + k: c3[k] for k in ('TP', 'FP', 'P', 'F1')}))
print('\n## sensitivity (pub = Table 3; noid = without row index + patient ID; q = 13 source ? counted as errors)')
print(pd.DataFrame(rows).to_string(index=False))
print('eps published', round(len(A) / (N * d), 4), ' eps without id columns', round(len(A2) / (N * (d - 2)), 4))
