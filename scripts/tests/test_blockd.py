"""Synthetic tests of scripts/blockd_driver.py and scripts/blockd_analysis.py (requirements R111, R112).

Pure python / pandas / numpy on small synthetic data written to a tempfile folder (never into the repo); one test
(R90) reads the real flags and datasets read-only, without training. Runs with pytest when installed, otherwise
with plain python. Run in the rein container from /rein:
    docker compose run --rm -T --no-deps --entrypoint python3 rein scripts/tests/test_blockd.py
    python3 scripts/blockd_driver.py --selftest      (driver tests)    python3 scripts/blockd_analysis.py --selftest
"""
import sys
sys.dont_write_bytecode = True
import contextlib
import csv
import fractions
import hashlib
import io
import itertools
import json
import math
import os
import shutil
import tempfile
import traceback

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import blockd_driver as bd                                     # noqa: E402
import blockd_analysis as ba                                   # noqa: E402

F = fractions.Fraction
SYN = 'synth'
COLS = ['id', 'x1', 'x2', 'x3', 'cat', 'y']


# ---------------------------------------------------------------- synthetic dataset (R111)
def make_synthetic(root, n=200, bad_label=False):
    """200 rows: 3 numeric features, 1 categorical, 1 excluded column ('id'), binary label 'y' (positive '1').
    Errors that parse (x1 x100), that do not (x2 'abc'), label flips, categorical typos, excluded-column errors,
    a format-only FP (x3 '3' vs '3.0', not an error) and an unflagged '?' that is '?' in clean.csv too."""
    rng = np.random.default_rng(7)
    x1 = rng.integers(1, 10, n).astype(float)
    x2 = np.round(rng.normal(5, 2, n), 2)
    x3 = rng.integers(0, 5, n)
    y = ((x1 + x2 + rng.normal(0, 1.5, n)) > 10).astype(int)
    clean = pd.DataFrame({'id': [str(i) for i in range(n)], 'x1': [repr(float(v)) for v in x1],
                          'x2': [repr(float(v)) for v in x2], 'x3': [str(v) for v in x3],
                          'cat': rng.choice(['a', 'b', 'c'], n), 'y': [str(v) for v in y]})
    clean.loc[7, 'x3'] = '?'
    clean.loc[9, 'x3'] = clean.loc[9, 'x3'] + '.0'             # dirty keeps the integer text: format-only
    dirty = clean.copy()
    dirty.loc[9, 'x3'] = clean.loc[9, 'x3'][:-2]
    j = {c: i for i, c in enumerate(COLS)}
    err = []
    for i in range(0, 60, 4):
        dirty.loc[i, 'x1'] = repr(float(clean.loc[i, 'x1']) * 100)
        err.append((i, j['x1']))
    for i in range(1, 60, 6):
        dirty.loc[i, 'x2'] = 'abc'
        err.append((i, j['x2']))
    for i in (2, 50, 90, 130):
        dirty.loc[i, 'y'] = '0' if clean.loc[i, 'y'] == '1' else '1'
        err.append((i, j['y']))
    for i in (3, 61):
        dirty.loc[i, 'cat'] = 'zz'
        err.append((i, j['cat']))
    for i in (5, 55):
        dirty.loc[i, 'id'] = 'X'
        err.append((i, j['id']))
    if bad_label:
        dirty.loc[11, 'y'] = 'bad'
        err.append((11, j['y']))
    err = sorted(set(err))
    xs = [e for e in err if e[1] == j['x1']]
    flags = dict(
        ge_dirty_profiled=[], ge_clean_profiled=[],
        ge_hand_written=xs + [e for e in err if e[1] == j['cat']],
        holoclean=[(i, j['y']) for i in range(n)] + [e for e in err if e[1] == j['x2']] + [(i, j['x1']) for i in range(100, 130)],
        raha=[e for e in err if e[1] in (j['x2'], j['y'])] + [(9, j['x3']), (5, j['id']), (150, j['x1'])] + xs[:5])
    data_root, flags_dir = os.path.join(root, 'data'), os.path.join(root, 'flags')
    os.makedirs(os.path.join(data_root, SYN))
    os.makedirs(os.path.join(flags_dir, SYN))
    clean.to_csv(os.path.join(data_root, SYN, 'clean.csv'), index=False)
    dirty.to_csv(os.path.join(data_root, SYN, 'dirty.csv'), index=False)
    write_cells(os.path.join(data_root, SYN, 'actual_errors.csv'), err)
    A = set(err)
    table3, man = {}, []
    for c, cells in flags.items():
        p = os.path.join(flags_dir, SYN, c + '.csv')
        write_cells(p, sorted(set(cells)))
        table3[c] = bd.tp_fp(set(cells), A)
        man.append(dict(dataset=SYN, config=c, detections=table3[c][2], tp=table3[c][0], fp=table3[c][1],
                        sha256=bd.sha256_file(p)))
    with open(os.path.join(flags_dir, 'MANIFEST.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(man[0]))
        w.writeheader()
        w.writerows(man)
    bd.CFG[SYN] = dict(label='y', excl=['id'], task='clf', pos='1')
    bd.TABLE3[SYN] = table3
    bd.PUBLISHED_F1[SYN] = {c: round(bd.f1_counts(table3[c][2], len(A), table3[c][0]), 3) for c in flags}
    return data_root, flags_dir


def write_cells(path, cells):
    with open(path, 'w') as f:
        for i, jj in cells:
            f.write('{},{},DUMMY\n'.format(i, jj))


def synthetic_data(root, **kw):
    data_root, flags_dir = make_synthetic(root, **kw)
    files = dict(dirty=os.path.join(data_root, SYN, 'dirty.csv'), clean=os.path.join(data_root, SYN, 'clean.csv'),
                 errors=os.path.join(data_root, SYN, 'actual_errors.csv'),
                 **{c: os.path.join(flags_dir, SYN, c + '.csv') for c in bd.CONFIGS})
    bd._CACHE.clear()
    data, full, restricted = bd.cached(SYN, bd.CFG[SYN], files)
    return data, full, restricted


@contextlib.contextmanager
def tmpdir():
    d = tempfile.mkdtemp(prefix='blockd_test_')
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@contextlib.contextmanager
def patched_driver(root):
    """Runs root under the tempfile folder, no environment gate, no replay (the synthetic set has none)."""
    saved = (bd.RUNS_ROOT, bd.check_environment, bd.replay, os.environ.get('REIN_IMAGE_ID'))
    bd.RUNS_ROOT = os.path.join(root, 'runs')
    os.makedirs(bd.RUNS_ROOT, exist_ok=True)
    bd.check_environment = lambda mode, say: dict(git_head='test', hostname='test', variables={'REIN_IMAGE_ID': 'test'})
    bd.replay = lambda ds, c, dirty, clean: None
    os.environ['REIN_IMAGE_ID'] = 'test'
    try:
        yield
    finally:
        bd.RUNS_ROOT, bd.check_environment, bd.replay = saved[:3]
        if saved[3] is None:
            os.environ.pop('REIN_IMAGE_ID', None)
        else:
            os.environ['REIN_IMAGE_ID'] = saved[3]


def run_driver(args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = bd.main(args)
    return code, buf.getvalue()


# ---------------------------------------------------------------- driver tests
def test_numeric_rule():
    """D4: numeric iff >= 90 % of the clean values parse; '' and non-finite values do not parse."""
    with tmpdir() as root:
        n = 200
        clean = pd.DataFrame({'a': ['1'] * 180 + ['?'] * 20, 'b': ['1'] * 179 + ['?'] * 21, 'c': ['inf'] * 200,
                              'd': [''] * 10 + ['2.5'] * 190, 'y': ['0', '1'] * 100})
        os.makedirs(os.path.join(root, 'd'))
        for nm in ('clean', 'dirty'):
            clean.to_csv(os.path.join(root, 'd', nm + '.csv'), index=False)
        open(os.path.join(root, 'd', 'actual_errors.csv'), 'w').close()
        bd.CFG['numrule'] = dict(label='y', excl=[], task='clf', pos='1')
        data = bd.load_data('numrule', bd.CFG['numrule'], dict(clean=os.path.join(root, 'd', 'clean.csv'),
                                                             dirty=os.path.join(root, 'd', 'dirty.csv'),
                                                             errors=os.path.join(root, 'd', 'actual_errors.csv')))
        names = lambda js: [data['cols'][j] for j in js]
        assert names(data['num_j']) == ['a', 'd'], names(data['num_j'])
        assert names(data['cat_j']) == ['b', 'c'], names(data['cat_j'])
        assert not bd.isnum('') and not bd.isnum('nan') and not bd.isnum('inf') and bd.isnum('1e3')
        assert len(data['clean_num']) == n


def test_single_encoder():
    """R27: one fixed map (positive -> 1, the other clean class -> 0) for every array; other text does not parse."""
    with tmpdir() as root:
        data, _, restricted = synthetic_data(root)
        lab = data['lab_j']
        enc = lambda t: 1.0 if t == '1' else 0.0
        assert all(data['y_clean'][i] == enc(t) for i, t in enumerate(data['clean_txt'][:, lab]))
        assert all(data['y_dirty'][i] == enc(t) for i, t in enumerate(data['dirty_txt'][:, lab]))
        # a training set holding one class keeps that class's code (a per-array LabelEncoder would give 0)
        pos_rows = np.flatnonzero(data['y_clean'] == 1.0)
        kept, _, _, y = bd.apply_policy(data, restricted['perfect'], 'clean', pos_rows)
        assert set(y.tolist()) == {1.0}
    with tmpdir() as root:
        data, _, _ = synthetic_data(root, bad_label=True)
        assert np.isnan(data['y_dirty'][11]) and not np.isnan(data['y_clean']).any()


def test_degenerate_rule():
    assert bd.is_degenerate(True, np.array([0.0, 1.0] * 24 + [0.0]))           # 49 rows
    assert not bd.is_degenerate(True, np.array([0.0, 1.0] * 25))               # 50 rows, two classes
    assert bd.is_degenerate(True, np.ones(500))                                 # one class
    assert not bd.is_degenerate(False, np.ones(50))                            # regression: rows only
    assert bd.test_degenerate(True, np.array([])) and bd.test_degenerate(True, np.ones(5))
    assert bd.test_degenerate(False, np.array([1.0])) and not bd.test_degenerate(False, np.array([1.0, 2.0]))


def test_d2_kept_row_statistics():
    """D2: impute statistics come from the unflagged parsable cells of the KEPT training rows only."""
    with tmpdir() as root:
        data, _, restricted = synthetic_data(root)
        tr, te = bd.split(data, 0)
        x1 = data['cols'].index('x1')
        rm = np.zeros_like(restricted['perfect'])
        rm[tr[0], x1] = True                                    # one flagged feature cell
        rm[tr[1:11], data['lab_j']] = True                     # ten flagged labels: their rows are dropped
        kept = bd.kept_rows(data, rm, 'impute', tr)
        assert len(kept) == len(tr) - 10 and not set(tr[1:11]) & set(kept)
        st = bd.impute_stats(data, rm, kept, 'mean')
        pool = [data['dirty_num'][i, x1] for i in kept if i != tr[0] and bd.isnum(data['dirty_txt'][i, x1])]
        assert st[x1] == float(pd.Series(pool).mean())
        all_rows = [data['dirty_num'][i, x1] for i in tr if i != tr[0] and bd.isnum(data['dirty_txt'][i, x1])]
        assert st[x1] != float(pd.Series(all_rows).mean())      # all-rows statistic differs here
        assert bd.impute_stats(data, rm, kept, 'median')[x1] == float(pd.Series(pool).median())
        v = bd.build_version(data, 'test/impute', 'test', 'impute', rm, tr, te, 'mean')
        p = list(data['num_j']).index(x1)
        assert v['num'][0, p] == st[x1] and repr(st[x1]) and float(repr(st[x1])) == st[x1]   # R44
        cj = int(data['cat_j'][0])
        rm2 = rm.copy()
        rm2[kept, cj] = True                                     # a fully flagged column becomes constant
        st2 = bd.impute_stats(data, rm2, kept, 'mean')
        assert st2[cj] == '__none__'


def test_labels_never_imputed():
    """Under impute a flagged label costs the row; the kept labels are the dirty labels unchanged."""
    with tmpdir() as root:
        data, _, restricted = synthetic_data(root)
        tr, te = bd.split(data, 0)
        rm = restricted['raha']                                 # flags the label errors and other cells
        v = bd.build_version(data, 'raha/impute', 'raha', 'impute', rm, tr, te, 'mean')
        lab_flagged = set(tr[rm[tr, data['lab_j']]].tolist())
        assert lab_flagged and not lab_flagged & set(v['kept'].tolist())
        assert np.array_equal(v['y'], data['y_dirty'][v['kept']])
        t = v['test']
        assert not set(te[rm[te, data['lab_j']]].tolist()) & set(t[0].tolist())   # test rows too (R45)
        hv = bd.build_version(data, 'holoclean/impute', 'holoclean', 'impute', restricted['holoclean'], tr, te, 'mean')
        assert hv['rows_kept'] == 0 and hv['degenerate'] and hv['train_hash'] == ''


def test_merge_identical_flag_sets():
    """R34: identical model-column sets merge in CONFIGS order, even when excluded-column flags differ."""
    with tmpdir() as root:
        data, full, restricted = synthetic_data(root)
        r = dict(restricted)
        r['ge_clean_profiled'] = r['ge_dirty_profiled'].copy()
        assert [nm for nm, _ in bd.make_items(r)] == ['GE-dirty=GE-clean', 'GE-hand', 'HoloClean', 'Raha']
        r['raha'] = r['ge_hand_written'].copy()
        items = bd.make_items(r)
        assert [nm for nm, _ in items] == ['GE-dirty=GE-clean', 'GE-hand=Raha', 'HoloClean']
        assert items[1][1] == ['ge_hand_written', 'raha']
        # excluded-column flags are counted, never applied (restriction happens before the merge)
        assert full['raha'][:, data['excl_j']].any() and not restricted['raha'][:, data['excl_j']].any()


def test_train_hash_stability():
    """R54: rounding to 12 significant digits, -0.0 = 0.0, shape and labels matter, 64 hex digits, pinned value."""
    X = np.array([[1.0, 0.1 + 0.2, -0.0], [2.5, 1e-300, 123456789.123456789]])
    y = np.array([0.0, 1.0])
    h = bd.train_hash(X, y)
    assert len(h) == 64 and h == bd.train_hash(X.copy(), y.copy())
    assert h == bd.train_hash(X * (1 + 1e-15), y)                   # below the 12th digit
    X0 = X.copy()
    X0[0, 2] = 0.0
    assert h == bd.train_hash(X0, y)                                 # -0.0 == 0.0
    assert h != bd.train_hash(X.reshape(3, 2), y)                    # the shape is hashed
    assert h != bd.train_hash(X, y[::-1])
    assert h != bd.train_hash(X + 1e-9, y)
    r = np.random.default_rng(1).normal(0, 1e3, 1000)
    assert np.array_equal(bd.round12(r), np.array([float('%.12g' % v) for v in r]))
    assert h == 'd58b6f5691c08f925b40eeef13099b23878703416d1c0371157142fb3f9c3ad0', h   # pinned; = a pure-struct sha256


def test_policies_and_checks_synthetic():
    """R40-R46, R52, checks 2-4 and R38 on one seed of the synthetic dataset."""
    with tmpdir() as root:
        data, full, restricted = synthetic_data(root)
        vs, lines, r62 = bd.seed_versions(data, restricted, 0, 'mean', bd.POLICIES, False)
        assert any(l.startswith('check 4') for l in lines) and len(lines) == 3
        tr, te = bd.split(data, 0)
        floor = vs['floor']
        assert floor['rows_kept'] == len(tr) and floor['cells_changed'] == 0
        # GT: flagged cells get the clean value, all rows kept; perfect + GT = clean (check 2)
        assert vs['perfect/gt']['train_hash'] == vs['clean']['train_hash']
        # the unflagged '?' at (7, x3) is '?' in clean too: no feature error left there
        x3 = data['cols'].index('x3')
        assert data['clean_txt'][7, x3] == '?' and data['dirty_txt'][7, x3] == '?'
        # delete drops rows with model-column flags only (the excluded id flag of raha keeps row 5)
        d = vs['raha/delete']
        assert full['raha'][5, data['cols'].index('id')] and not restricted['raha'][5].any()
        assert set(d['kept'].tolist()) == set(tr[~restricted['raha'][tr].any(axis=1)].tolist())
        assert 5 not in set(tr.tolist()) or 5 in set(d['kept'].tolist())
        # the format-only FP (9, x3) counts, and is not an error left
        assert bd.flag_stats(data, full['raha'], restricted['raha'])['format_only_fp'] == 1
        # zero-flag configurations equal the floor; their controls have k = 0
        assert vs['ge_dirty_profiled/impute']['eq_floor'] == '=' and vs['control/ge_dirty_profiled']['k'] == 0
        # controls: k = rows the delete version removes, drawn with default_rng([seed, c_idx])
        c = vs['control/raha']
        k = len(tr) - vs['raha/delete']['rows_kept']
        assert c['k'] == k and c['rows_kept'] == len(tr) - k
        drop = np.random.default_rng([0, bd.CONFIGS.index('raha')]).choice(tr, size=k, replace=False)
        assert np.array_equal(c['kept'], np.setdiff1d(tr, drop))
        assert vs['control/holoclean']['degenerate']                 # degenerate because holoclean/delete is
        # errors left: the floor counts every visible feature error of its training rows
        vis = sum(1 for i in tr for j in data['feat_j']
                  if (i, j) in bd.cell_set(data['err_cells']) and not bd.same_value(
                      np.array([data['dirty_num'][i, j]]), np.array([data['clean_num'][i, j]]))[0]
                  if j in data['num_j']) + sum(1 for i in tr for j in data['cat_j'] if data['dirty_txt'][i, j] != data['clean_txt'][i, j])
        assert floor['errors_left_in_features'] == vis, (floor['errors_left_in_features'], vis)


def test_driver_full_run_synthetic():
    """R13 (--jobs 1 = --jobs 2), R16-R21 inputs and check 1, R63-R66 outputs, then --compare and the analysis."""
    with tmpdir() as root:
        data_root, flags_dir = make_synthetic(root)
        with patched_driver(root):
            base = ['--datasets', SYN, '--flags_dir', flags_dir, '--data_root', data_root, '--seeds', '0-6']
            outs = []
            for jobs in ('1', '2'):
                out = os.path.join(bd.RUNS_ROOT, 'full' + jobs)
                code, text = run_driver(base + ['--jobs', jobs, '--out', out])
                assert code == 0, text[-3000:]
                assert text.strip().splitlines()[-1].startswith('DONE full'), text[-500:]
                outs.append(out)
            A = pd.read_csv(os.path.join(outs[0], 'results.csv'), dtype=str, keep_default_na=False)
            B = pd.read_csv(os.path.join(outs[1], 'results.csv'), dtype=str, keep_default_na=False)
            assert list(A.columns) == bd.RESULT_COLS
            assert len(A) == 72 * 3 * 7                                  # R66
            assert A.drop(columns=['fit_s', 'timestamp']).equals(B.drop(columns=['fit_s', 'timestamp']))
            for f in ('manifest.json', 'checks.txt', 'run.log', 'dryrun.txt', 'inputs/MANIFEST.csv'):
                assert os.path.exists(os.path.join(outs[0], f)), f
            assert open(os.path.join(outs[0], 'dryrun.txt')).read() == open(os.path.join(outs[1], 'dryrun.txt')).read()
            s4 = A[(A.version == 'clean') & (A.scenario == 'S4')]
            pg = A[(A.version == 'perfect/gt') & (A.scenario == 'S2')]
            assert s4['score'].tolist() == pg['score'].tolist()              # check 2 through reuse
            deg = A[A.version == 'holoclean/delete']
            assert (deg['degenerate'] == '1').all() and (deg['score'] == '').all() and (deg['train_hash'] == '').all()
            ctrl = A[A.policy == 'control']
            assert set(ctrl['scenario']) == {'S2'}
            assert len(A[A.version == 'clean']) == 3 * 7 and set(A[A.version == 'clean']['scenario']) == {'S4'}
            # a reused member has an empty fit_s
            assert (A.loc[(A.version == 'ge_clean_profiled/gt'), 'fit_s'] == '').all()
            # --check runs the training part of check 2
            code, text = run_driver(base + ['--check', '--out', os.path.join(bd.RUNS_ROOT, 'check')])
            assert code == 0 and 'check 2(train)' in open(os.path.join(bd.RUNS_ROOT, 'check', 'checks.txt')).read(), text[-2000:]
            # --out outside the runs folder is refused before anything is written (R8)
            code, text = run_driver(base + ['--dry_run', '--out', os.path.join(root, 'elsewhere')])
            assert code == 2 and 'FAIL out' in text and not os.path.exists(os.path.join(root, 'elsewhere'))
            # --compare: itself PASS, a linear score PASS WITH NOTE, an RF score or a hash STOP (R109)
            assert ba.compare(outs[0], outs[1], say=lambda s: None)[1] == 'PASS'
            for col, model, want in (('score', 'linear', 'PASS WITH NOTE'), ('score', 'rf', 'STOP'),
                                     ('train_hash', 'rf', 'STOP'), ('rows_kept', 'linear', 'STOP')):
                d = os.path.join(root, 'cmp_' + col + model)
                shutil.copytree(outs[1], d)
                C = pd.read_csv(os.path.join(d, 'results.csv'), dtype=str, keep_default_na=False)
                i = C.index[(C.model == model) & (C[col] != '')][0]
                C.loc[i, col] = C.loc[i, col][:-1] + ('1' if C.loc[i, col][-1] != '1' else '2')
                C.to_csv(os.path.join(d, 'results.csv'), index=False)
                got = ba.compare(outs[0], d, say=lambda s: None)
                assert got[1] == want, (col, model, got)
            # the analysis runs end to end on the synthetic run (interim label; synthetic refs from the inputs)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = ba.main([outs[0], '--out', os.path.join(bd.RUNS_ROOT, 'analysis')])
            text = buf.getvalue()
            assert code == 0, text[-3000:]
            assert 'Block D analysis (interim)' in text and 'prediction scorecard' in text
            assert os.path.exists(os.path.join(bd.RUNS_ROOT, 'analysis', 'pair_verdicts.csv'))
            assert 'seeds 0-6,' in open(os.path.join(outs[0], 'run.log')).read()
            # review fix: a verdict file that differs from the one the run hashed is refused (R67)
            d = os.path.join(root, 'tampered')
            shutil.copytree(outs[0], d)
            man = json.load(open(os.path.join(d, 'manifest.json')))
            assert man['expected_verdict_files'][bd.FROZEN_VERDICTS] == bd.sha256_file(bd.FROZEN_VERDICTS)
            man['expected_verdict_files'][bd.FROZEN_VERDICTS] = '0' * 64
            json.dump(man, open(os.path.join(d, 'manifest.json'), 'w'))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = ba.main([d])
            last = buf.getvalue().strip().splitlines()[-1]
            assert code == 1 and last.startswith('FAIL analysis') and 'sha256 of ' + bd.FROZEN_VERDICTS in last, last


def test_unexpected_failures_recorded():
    """Review fix (R6, R57): a missing MANIFEST.csv is a CHECK 1 FAIL; any other exception still ends stdout with a
    FAIL line and writes a failed manifest.json (with the traceback), checks.txt and run.log."""
    with tmpdir() as root:
        data_root, flags_dir = make_synthetic(root)
        with patched_driver(root):
            base = ['--datasets', SYN, '--flags_dir', flags_dir, '--data_root', data_root, '--seeds', '0', '--dry_run']
            os.rename(os.path.join(flags_dir, 'MANIFEST.csv'), os.path.join(root, 'MANIFEST.csv'))
            code, text = run_driver(base + ['--out', os.path.join(bd.RUNS_ROOT, 'noman')])
            last = text.strip().splitlines()[-1]
            assert code == 1 and last.startswith('FAIL check1 CHECK 1 FAIL missing input'), text[-800:]
            assert json.load(open(os.path.join(bd.RUNS_ROOT, 'noman', 'manifest.json')))['status'] == 'failed'
            os.rename(os.path.join(root, 'MANIFEST.csv'), os.path.join(flags_dir, 'MANIFEST.csv'))
            saved, err = bd.prepare, io.StringIO()

            def boom(*a, **k):
                raise KeyError('boom')
            bd.prepare = boom
            try:
                with contextlib.redirect_stderr(err):
                    code, text = run_driver(base + ['--out', os.path.join(bd.RUNS_ROOT, 'boom')])
            finally:
                bd.prepare = saved
            out = os.path.join(bd.RUNS_ROOT, 'boom')
            assert code == 1 and text.strip().splitlines()[-1] == "FAIL unexpected KeyError('boom')", text[-800:]
            man = json.load(open(os.path.join(out, 'manifest.json')))
            assert man['status'] == 'failed' and man['failure'] == "unexpected KeyError('boom')"
            assert 'KeyError' in man['traceback'] and 'Traceback' in err.getvalue()
            assert open(os.path.join(out, 'run.log')).read().strip().splitlines()[-1] == "FAIL unexpected KeyError('boom')"
            assert "unexpected KeyError('boom')" in open(os.path.join(out, 'checks.txt')).read()
    bd._CACHE.clear()


def test_seeds_text():
    """Review fix: the banner and dryrun.txt [4] print seed lists as runs, so --seeds 0 2 is not shown as 0-2."""
    assert bd.seeds_text(list(range(10))) == '0-9' and bd.seeds_text([0, 2]) == '0,2'
    assert bd.seeds_text([8, 0, 1, 2, 5, 7]) == '0-2,5,7-8' and bd.seeds_text([3]) == '3' and bd.seeds_text([]) == '-'


def test_check1_aborts():
    """R19, R20: a corrupted MANIFEST sha256 and a duplicate cell each abort; R28: an unflagged bad label aborts."""
    with tmpdir() as root:
        data_root, flags_dir = make_synthetic(root)
        with patched_driver(root):
            base = ['--datasets', SYN, '--flags_dir', flags_dir, '--data_root', data_root, '--seeds', '0', '--dry_run']
            man = pd.read_csv(os.path.join(flags_dir, 'MANIFEST.csv'), dtype=str)
            man.loc[man.config == 'raha', 'sha256'] = '0' * 64
            man.to_csv(os.path.join(flags_dir, 'MANIFEST.csv'), index=False)
            code, text = run_driver(base + ['--out', os.path.join(bd.RUNS_ROOT, 'sha')])
            assert code == 1 and 'CHECK 1 FAIL synth raha sha256' in text, text[-800:]
            assert '"status": "failed"' in open(os.path.join(bd.RUNS_ROOT, 'sha', 'manifest.json')).read()
            p = os.path.join(flags_dir, SYN, 'ge_hand_written.csv')
            open(p, 'a').write(open(p).readline())
            bd._CACHE.clear()
            code, text = run_driver(base + ['--out', os.path.join(bd.RUNS_ROOT, 'dup')])
            assert code == 1 and 'duplicate' in text, text[-800:]
    with tmpdir() as root:
        data_root, flags_dir = make_synthetic(root, bad_label=True)
        with patched_driver(root):
            bd._CACHE.clear()
            code, text = run_driver(['--datasets', SYN, '--flags_dir', flags_dir, '--data_root', data_root,
                                     '--seeds', '0', '--dry_run', '--out', os.path.join(bd.RUNS_ROOT, 'lab')])
            assert code == 1 and 'LABEL FAIL' in text, text[-800:]
    bd._CACHE.clear()


# ---------------------------------------------------------------- analysis tests
def test_signflip_examples():
    """R84: the three examples, both pair orders; n = 5 and n = 6 extremes."""
    for d, p in (([4, 2, 4, 1, 3, 4, -3, 2, 1, -1], F(60, 1024)), ([2, 3, -1, 3, -2, 1, 1, 1, 2, 5], F(64, 1024)),
                 ([5, -1, -1, 3, 3, 1, -2, 4, 2, 3], F(50, 1024))):
        d = [float(x) for x in d]
        assert ba.signflip(d)[1] == p and ba.signflip([-x for x in d])[1] == p
        assert ba.signflip(d)[0] == -ba.signflip([-x for x in d])[0]
    assert ba.signflip([1.0, 2.0, 3.0, 4.0, 5.0])[1] == F(2, 32)
    assert ba.signflip([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])[1] == F(2, 64)


def test_signflip_ties_zeros_small_n():
    """Midranks for ties (after rounding to 12 digits), |d| < 1e-9 dropped, n <= 5 nonzero -> tie, hash rule."""
    assert ba.doubled_midranks([1.0, 1.0, 2.0]) == [3, 3, 6]
    assert ba.signflip([0.1 + 0.2, 0.3, 1.0])[0] == ba.signflip([0.3, 0.3, 1.0])[0]   # equal at 12 digits
    s = lambda sc, h=None: dict(score=sc, hash=h or [str(i) for i in range(len(sc))], deg=[False] * len(sc))
    a = s([1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    b = s([0, 0, 0, 0, 0, 1, 1, 1, 1, 1 + 1e-12], ['x'] * 10)          # 5 nonzero + 5 (near) zeros
    v = ba.pair_verdict(a, b, 'ranked_last')
    assert v['verdict'] == 'tie' and v['n'] == 5 and v['reason'] == 'n <= 5'
    c = s([2.0] * 10, ['h'] * 10)
    assert ba.pair_verdict(c, dict(c), 'ranked_last')['hash_rule'] == 1
    up = s([1.0 + i for i in range(10)], ['p'] * 10)
    lo = s([0.0] * 10, ['q'] * 10)
    v = ba.pair_verdict(up, lo, 'ranked_last')
    assert v['verdict'] == '>' and v['p'] == F(2, 1024)
    assert ba.pair_verdict(lo, up, 'ranked_last')['verdict'] == '<'


def test_signflip_symmetry_and_mini_rule():
    """R83, R112: order of the pair and of the seeds never changes the verdict; sign(T) = mini's median rule."""
    rng = np.random.default_rng(0)
    checked = 0
    for _ in range(200):
        d = rng.integers(-3, 6, size=10).astype(float)
        a = dict(score=list(d), hash=[str(i) for i in range(10)], deg=[False] * 10)
        b = dict(score=[0.0] * 10, hash=['z'] * 10, deg=[False] * 10)
        v1 = ba.pair_verdict(a, b, 'ranked_last')
        v2 = ba.pair_verdict(b, a, 'ranked_last')
        assert v1['verdict'] == ba.flip(v2['verdict']) and v1['p'] == v2['p']
        perm = rng.permutation(10)
        ap = dict(score=[a['score'][i] for i in perm], hash=[a['hash'][i] for i in perm], deg=a['deg'])
        assert ba.pair_verdict(ap, b, 'ranked_last')['verdict'] == v1['verdict']
        nz = d[np.abs(d) >= 1e-9]
        if v1['p'] != '' and v1['p'] < F(1, 20):
            med = '>' if np.median(nz) > 0 or (np.median(nz) == 0 and nz.sum() > 0) else '<'
            assert med == v1['verdict'], (d, v1)
            checked += 1
    assert checked > 10


def test_degenerate_modes():
    """R79: ranked last vs left out, incl. a partially degenerate item (-inf seeds rank above every finite |d|)."""
    good = dict(score=[0.9] * 10, hash=['g'] * 10, deg=[False] * 10)
    dead = dict(score=[None] * 10, hash=[''] * 10, deg=[True] * 10)
    assert ba.pair_verdict(good, dead, 'ranked_last')['verdict'] == '>'
    assert ba.pair_verdict(dead, good, 'ranked_last')['verdict'] == '<'
    assert ba.pair_verdict(dead, dict(dead), 'ranked_last')['verdict'] == 'tie'
    assert ba.pair_verdict(good, dead, 'left_out') is None
    part = dict(score=[None] * 6 + [0.95] * 4, hash=[''] * 6 + ['p'] * 4, deg=[True] * 6 + [False] * 4)
    v = ba.pair_verdict(good, part, 'ranked_last')
    assert v['verdict'] == 'tie' and v['n'] == 10 and v['p'] == F(92, 1024), v      # 6 x +inf, 4 x -0.05
    assert ba.signflip([math.inf] * 6 + [-0.05] * 4)[0] == 2 * (6 * 7.5) - 2 * (4 * 2.5)
    lo = ba.pair_verdict(good, part, 'left_out')
    assert lo['n'] == 4 and lo['verdict'] == 'tie'
    # review fix: left out with no seed where both are scored is a tie, not the hash rule
    a = dict(score=[None] * 5 + [0.9] * 5, hash=[''] * 5 + ['a'] * 5, deg=[True] * 5 + [False] * 5)
    b = dict(score=[0.8] * 5 + [None] * 5, hash=['b'] * 5 + [''] * 5, deg=[False] * 5 + [True] * 5)
    v = ba.pair_verdict(a, b, 'left_out')
    assert v['verdict'] == 'tie' and v['hash_rule'] == 0 and v['reason'] == 'no common scored seed', v


def test_permutation_support_and_holm_tau():
    """R112: support sizes 120/24/6/2, probabilities sum to 1, p = 1/120 when fully concordant; Holm; tau-b."""
    for k, size in ba.PERM_SUPPORT.items():
        items = ['i%d' % i for i in range(k)]
        ref = {nm: float(k - i) for i, nm in enumerate(items)}
        ver = {(a, b): ['>'] * 3 for a, b in itertools.combinations(items, 2)}
        dist = ba.perm_distribution(items, ver, ref)
        assert sum(dist.values()) == 1 and min(dist.values()) * size >= 1
        assert dist[max(dist)] == F(1, size)
        assert sum(1 for _ in itertools.permutations(items)) == size
    conv = ba.convolve([ba.perm_distribution(['a', 'b'], {('a', 'b'): ['>']}, {'a': 1, 'b': 0})] * 2)
    assert conv == {0: F(1, 4), 1: F(1, 2), 2: F(1, 4)}
    adj, dec = ba.holm({'gt': F(1, 100), 'delete': F(4, 100), 'impute': F(3, 100)})
    assert adj == {'gt': F(3, 100), 'impute': F(6, 100), 'delete': F(6, 100)}
    assert dec == {'gt': True, 'impute': False, 'delete': False}
    # review fix: exact fractions and the strict rule of §8.2 at the boundary (3 x 1/60 == 0.05 in floats too)
    adj, dec = ba.holm({'gt': F(1, 60), 'delete': F(1, 40), 'impute': F(1, 20)})
    assert set(adj.values()) == {F(1, 20)} and not any(dec.values()), (adj, dec)
    assert ba.holm({'gt': F(1, 61), 'delete': F(1, 2), 'impute': F(1, 2)})[1]['gt']
    assert abs(ba.tau_b(6, 2, 10, 0, 2) - 4 / math.sqrt(80)) < 1e-12 and ba.tau_b(0, 0, 3, 3, 0) == ''
    # review fix: a pair tied on both sides counts in n_ref and n_down (standard tau-b)
    assert ba.tau_from(['>', 'tie', '>'], ['>', '=', '>']) == 1.0
    assert abs(ba.tau_from(['>', 'tie', '>', 'tie'], ['>', '>', '>', '=']) - 2 / math.sqrt(3 * 2)) < 1e-12
    assert ba.classify('>', '>') == 'C' and ba.classify('<', '>') == 'D' and ba.classify('tie', '<') == 'T'
    assert ba.classify('>', '=') == 'reftie'


def test_r90_addendum_reproduced():
    """R90: mechanism (d) and the 87 expected verdicts recomputed from the frozen flags equal the addendum CSV
    (flags and datasets read-only, no training)."""
    flags = bd.R + '/reports/block_d/flags'
    if not os.path.exists(flags + '/MANIFEST.csv') or not os.path.exists(bd.ADDENDUM_VERDICTS):
        print('    skipped: real flags not available')
        return
    bd.ns['D'] = bd.R + '/datasets'
    total = 0
    for ds in bd.DATASETS:
        files = dict(dirty='{}/datasets/{}/dirty.csv'.format(bd.R, ds), clean='{}/datasets/{}/clean.csv'.format(bd.R, ds),
                     errors='{}/datasets/{}/actual_errors.csv'.format(bd.R, ds),
                     **{c: '{}/{}/{}.csv'.format(flags, ds, c) for c in bd.CONFIGS})
        bd._CACHE.clear()
        data, full, restricted = bd.cached(ds, bd.CFG[ds], files)
        items = bd.make_items(restricted)
        ref = bd.references(data, full, restricted, items)
        ok, n, diff = bd.compare_verdicts(ds, bd.expected_verdicts(ds, items, ref), bd.ADDENDUM_VERDICTS, strict=True)
        assert ok == n, (ds, diff[:3])
        total += ok
    bd._CACHE.clear()
    assert total == 87, total


def test_gap_closed_matched_seeds():
    """Review fix (R99): floor and S4 are averaged over the seeds where the item is scored."""
    item = dict(score=[None, 0.5, 0.7])
    floor, s4 = dict(score=[0.0, 0.4, 0.4]), dict(score=[1.0, 0.8, 0.8])
    assert abs(ba.gap_closed(item, floor, s4) - 0.5) < 1e-12
    full = dict(score=[0.2, 0.5, 0.7])
    assert ba.gap_closed(full, floor, s4) == float((np.mean(full['score']) - np.mean(floor['score']))
                                                   / (np.mean(s4['score']) - np.mean(floor['score'])))   # = before
    assert ba.gap_closed(dict(score=[None] * 3), floor, s4) == '' and ba.gap_closed(full, floor, dict(floor)) == ''


def test_analysis_unexpected_failure():
    """Review fix (R6): an unexpected exception in the analysis ends stdout with a FAIL line and exits 1."""
    saved, out, err = ba.analyse, io.StringIO(), io.StringIO()

    def boom(*a, **k):
        raise KeyError('boom')
    ba.analyse = boom
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ba.main(['some_run'])
    finally:
        ba.analyse = saved
    assert code == 1 and out.getvalue().strip().splitlines()[-1] == "FAIL analysis unexpected KeyError('boom')"
    assert 'Traceback' in err.getvalue()


def test_provenance_ignores_container_hostname():
    """Two compose runs on one machine get different container IDs as hostname; they must still match."""
    base = dict(git_head='h', variables={'REIN_IMAGE_ID': 'img'}, host_fingerprint='x86_64:abc')
    a = dict(base, hostname='4ac78109a60c')
    b = dict(base, hostname='9864802f8517')
    assert ba.provenance(a) == ba.provenance(b)
    c = dict(base, hostname='4ac78109a60c', host_fingerprint='x86_64:def')
    assert ba.provenance(a) != ba.provenance(c)
    d = dict(base, git_head='other')
    assert ba.provenance(a) != ba.provenance(d)


DRIVER_TESTS = [test_numeric_rule, test_single_encoder, test_degenerate_rule, test_d2_kept_row_statistics,
                test_labels_never_imputed, test_merge_identical_flag_sets, test_train_hash_stability,
                test_policies_and_checks_synthetic, test_check1_aborts, test_driver_full_run_synthetic,
                test_unexpected_failures_recorded, test_seeds_text]
ANALYSIS_TESTS = [test_signflip_examples, test_signflip_ties_zeros_small_n, test_signflip_symmetry_and_mini_rule,
                  test_degenerate_modes, test_permutation_support_and_holm_tau, test_r90_addendum_reproduced,
                  test_gap_closed_matched_seeds, test_analysis_unexpected_failure,
                  test_provenance_ignores_container_hostname]


def run_all(which=None):
    tests = {'driver': DRIVER_TESTS, 'analysis': ANALYSIS_TESTS}.get(which, DRIVER_TESTS + ANALYSIS_TESTS)
    failed = 0
    for t in tests:
        try:
            t()
            print('PASS', t.__name__, flush=True)
        except Exception:                                       # noqa: BLE001
            failed += 1
            print('FAIL', t.__name__, flush=True)
            traceback.print_exc(file=sys.stdout)
    print('{} passed, {} failed'.format(len(tests) - failed, failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(run_all(sys.argv[1] if len(sys.argv) > 1 else None))
