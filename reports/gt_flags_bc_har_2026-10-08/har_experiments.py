"""har: are the 665 label 'errors' on clean 'null' rows injected errors or an I/O artifact?
Read-only on the repo."""
import importlib.util, io, math, sys, warnings
import pandas as pd
from scipy.stats import binomtest

warnings.filterwarnings('ignore'); sys.dont_write_bytecode = True
REPO = '/Users/ghassen.aicha@caronsale.de/Desktop/BA/rein-benchmark'
DS = REPO + '/rein-datasets/har/'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


prof = load_module('prof', REPO + '/rein/auxiliaries/expectations_profiler.py')
hw = load_module('hw', REPO + '/rein/auxiliaries/expectations_dictionary_local.py').DATASET_EXPECTATIONS


def differ(a, b):  # = Datasets.__cells_differ for values read with keep_default_na=False
    am, bm = a == '', b == ''
    if am or bm:
        return am != bm
    try:
        return not math.isclose(float(a), float(b), rel_tol=1e-6)
    except (ValueError, OverflowError):
        return a != b


clean = pd.read_csv(DS + 'clean.csv', dtype=str, keep_default_na=False)
dirty = pd.read_csv(DS + 'dirty.csv', dtype=str, keep_default_na=False)
ae = pd.read_csv(DS + 'actual_errors.csv', header=None, names=['r', 'c', 'v'])
A = set(zip(ae.r, ae.c)); N, d = clean.shape; gtj = clean.columns.get_loc('gt')

CG, DG = clean['gt'], dirty['gt']
# -- 1. the label column, split by the clean label
print('clean gt values:', CG.value_counts().to_dict())
for lab in ('stand', 'sit', 'null'):
    m = CG == lab
    ch = (DG[m] != CG[m])
    print('  clean %-5s rows %6d  changed in dirty %5d (%.1f %%)  dirty values of changed: %s' % (
        lab, m.sum(), ch.sum(), 100 * ch.mean(), DG[m][ch].value_counts().to_dict()))
print("'nan' strings anywhere in dirty.csv:", int((dirty == 'nan').values.sum()),
      " of which in gt on clean-null rows:", int(((DG == 'nan') & (CG == 'null')).sum()))
print("'null' strings anywhere in dirty.csv:", int((dirty == 'null').values.sum()))

# blank rate among stand/sit labels vs blanks on null rows
ns = CG != 'null'
p_blank = (DG[ns] == '').mean()
k = int(((DG == '') & (CG == 'null')).sum())
print('blank rate on stand/sit labels %.4f -> expected blanks among 665 null rows %.1f, observed %d, binomial p = %.3f' % (
    p_blank, 665 * p_blank, k, binomtest(k, 665, p_blank).pvalue))

# -- 2. the mechanism, replayed on three toy rows with REIN's own read/convert steps
toy = 'x,gt\n1.0,stand\n2.0,null\n3.0,sit\n'
gtdf = pd.read_csv(io.StringIO(toy), sep=',', encoding='utf-8')         # Datasets.__init__: pandas defaults
print('\nREIN reads clean.csv with defaults -> gt =', gtdf['gt'].tolist())
s = gtdf.astype(str)                                                     # inject_errors: dirtyDF.astype(str)
print('after .astype(str) before the error generator -> gt =', s['gt'].tolist())
out = io.StringIO(); s.to_csv(out, index=False); print('written dirty.csv:', out.getvalue().replace('\n', ' | '))
print("benchmark comparison: differ('nan','null') =", differ('nan', 'null'), "  differ('', 'null') =", differ('', 'null'))

# -- 3. Table 2 row, published vs without the 665 artifact cells
nullrows = set(clean.index[CG == 'null'])
art = {(r, gtj) for r in nullrows if (r, gtj) in A}
print('\nartifact cells in actual_errors.csv:', len(art), ' share of gt errors: %.1f %%' % (100 * len(art) / sum(1 for x in A if x[1] == gtj)))


def row(err):
    eps = len(err) / (N * d); rows = {r for r, _ in err}; rho = len(rows) / N
    rhohat = 1 - (1 - eps) ** d
    return dict(errors=len(err), dirty_rows=len(rows), eps=round(eps, 4), rho=round(rho, 4),
                F1base_cell=round(2 * eps / (1 + eps), 4), F1base_row=round(2 * rho / (1 + rho), 4),
                rhohat=round(rhohat, 4), rho_minus_rhohat=round(rho - rhohat, 4), eps_d_over_rho=round(eps * d / rho, 2))


print(pd.DataFrame([dict(version='published (Table 2)', **row(A)), dict(version='without artifact', **row(A - art))]).to_string(index=False))

# -- 4. what the five configurations do with the artifact (GE replayed; HoloClean has no constraints on har)


def ge(df, exps):
    det = set()
    for e in exps:
        col = e['column']; j = df.columns.get_loc(col); s = df[col].astype(str); kk = e['expectation']; kw = e['kwargs']
        if kk == 'expect_column_values_to_match_regex':
            bad = ~s.str.contains(kw['regex'], regex=True)
        elif kk == 'expect_column_values_to_be_in_set':
            bad = ~s.isin(kw['value_set'])
        elif kk == 'expect_column_values_to_not_be_in_set':
            bad = s.isin(kw['value_set'])
        elif kk == 'expect_column_values_to_be_unique':
            bad = s.duplicated(keep=False)
        elif kk == 'expect_column_values_to_not_match_regex':
            bad = s.str.contains(kw['regex'], regex=True)
        det |= {(i, j) for i in df.index[bad.values]}
    return det


def f1(det, truth):
    tp = len(det & truth); p = tp / len(det) if det else 0; r = tp / len(truth)
    return round(2 * p * r / (p + r), 4) if p + r else 0.0, tp, len(det) - tp


suites = {'dirty_profiled': prof.profile_expectations(dirty), 'clean_profiled': prof.profile_expectations(clean),
          'hand_written': hw['har']['hand_written']}
print('\nGE on full har (published GT vs GT without artifact):')
for nme, exps in suites.items():
    det = ge(dirty, exps)
    a, b = f1(det, A), f1(det, A - art)
    print('  %-15s detections %6d  artifact cells flagged %3d   F1 %.4f (TP %d) -> %.4f (TP %d)' % (
        nme, len(det), len(det & art), a[0], a[1], b[0], b[1]))
stored = pd.read_csv(DS + 'greatExpectations/detections.csv', header=None, names=['r', 'c', 'v'])
print('  stored greatExpectations/detections.csv:', len(stored), 'rows (14 Sep run, tier unknown)')

# -- 5. would a token-aware rule ("null", "nan", "N/A" ... = missing) be the fix? check all nine datasets
TOK = {'', 'nan', 'NaN', 'null', 'NULL', 'N/A', 'n/a', 'NA', 'None', '-', '?'}
print('\ncells counted as errors today although BOTH sides are a missing token:')
for ds in ['adult', 'beers', 'bike', 'breast_cancer', 'har', 'mercedes', 'nasa', 'smartfactory', 'soilmoisture']:
    c = pd.read_csv('%s/rein-datasets/%s/clean.csv' % (REPO, ds), dtype=str, keep_default_na=False)
    dd = pd.read_csv('%s/rein-datasets/%s/dirty.csv' % (REPO, ds), dtype=str, keep_default_na=False)
    if list(c.columns) != list(dd.columns) and sorted(c.columns) == sorted(dd.columns):
        c = c[list(dd.columns)]
    both = (c.isin(TOK) & dd.isin(TOK) & (c != dd))
    n = int(both.values.sum())
    if n:
        pairs = pd.Series([(c.iat[i, j], dd.iat[i, j]) for i, j in zip(*both.values.nonzero())]).value_counts().head(3).to_dict()
        print('  %-13s %5d  %s' % (ds, n, pairs))
    else:
        print('  %-13s %5d' % (ds, n))
