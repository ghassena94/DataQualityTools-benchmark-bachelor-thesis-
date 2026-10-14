"""Python helpers for server_env/calib.sh. They run inside the rein container (Python 3.8).

    python3 /rein/server_env/calib_lib.py mac-order <script.py> [args ...]
        Run <script.py> with os.listdir() returning the Mac's order for the seven Raha
        strategy-profiling folders (env/order_manifest.json); every other path is unchanged.
        Used by calib.sh v3 (server plan 2026-10-13, P2 table, V3).
    python3 /rein/server_env/calib_lib.py probe <rows> [features]
        scipy.cluster.hierarchy.linkage(X, method="average", metric="cosine"), the call Raha's
        build_clusters makes (raha/detection.py:239 in the image's raha 1.25), on <rows> random
        rows, then one fcluster; prints "linkage ok" or "linkage exception ...", and memory.peak.
        Used by calib.sh probe (J8).
    python3 /rein/server_env/calib_lib.py v4classify <pairs.tsv>
        Classify every changed line between reference and rerun output (V4c) for the V4 pass rule
        ("Block D on the server"): linear, xgb on a classification dataset (bc, adult), summary
        lines, or stop (RF, XGBRegressor, rows kept, fill values, degenerate, anything else).
        Two choices go beyond the plan's wording: equal words with other spacing are a stop
        (stop:whitespace), and a "=> ... pair verdicts change" line without a model word is
        "summary" (allowed), because each verdict line it counts is classified on its own line.
        The d4 positional rule keys on the file name d4_numeric_rule*, so baseline copies keep it.
        Read-only. Used by calib.sh v4 (informational since 14 Oct: Block D runs on the Mac).

Nothing here is imported by the benchmark; sitecustomize.py is the only file Python loads by itself.
"""
import difflib
import hashlib
import json
import os
import re
import runpy
import sys
import time

ORDER_MANIFEST = '/rein/env/order_manifest.json'


# ------------------------------------------------------------------------------------------ mac-order
def mac_order(argv):
    if not argv:
        sys.exit('usage: calib_lib.py mac-order <script.py> [args ...]')
    doc = json.load(open(ORDER_MANIFEST))
    orders = {}
    for ds, entry in doc['caches'].items():
        names = list(entry['order'])
        digest = hashlib.sha256('\n'.join(names).encode('utf-8')).hexdigest()
        if digest != entry['sha256'] or len(names) != entry['files']:
            sys.exit('mac-order: env/order_manifest.json entry {} fails its own sha256/count check'.format(ds))
        orders[ds] = names
    real_listdir = os.listdir

    def listdir(path='.'):
        names = real_listdir(path)
        if isinstance(path, (str, os.PathLike)):
            p = os.path.normpath(os.fspath(path))
            parent = os.path.basename(os.path.dirname(p))
            if os.path.basename(p) == 'strategy-profiling' and parent.startswith('raha-baran-results-'):
                ds = parent[len('raha-baran-results-'):]
                if ds not in orders:
                    raise RuntimeError('mac-order: no Mac order recorded for ' + ds)
                if sorted(names) != sorted(orders[ds]):
                    raise RuntimeError('mac-order: the files in {} differ from the Mac listing'.format(p))
                sys.stderr.write('mac-order: {} strategy files of {} returned in the Mac order\n'.format(
                    len(names), ds))
                return list(orders[ds])
        return names

    os.listdir = listdir
    script = os.path.abspath(argv[0])
    sys.argv = [argv[0]] + argv[1:]
    sys.path[0] = os.path.dirname(script)      # as "python3 <script.py>" would set it
    runpy.run_path(script, run_name='__main__')


# ------------------------------------------------------------------------------------------ probe
def read_cgroup(name):
    try:
        with open('/sys/fs/cgroup/' + name) as f:
            return f.read().strip()
    except OSError:
        return 'n/a'


def probe(argv):
    rows = int(argv[0])
    feats = int(argv[1]) if len(argv) > 1 else 20
    import numpy as np
    import scipy
    import scipy.cluster.hierarchy as hierarchy
    rng = np.random.RandomState(0)
    X = rng.randint(0, 2, size=(rows, feats)).astype(float)
    X[:, 0] = 1.0                    # no all-zero row: its cosine distance would be NaN
    entries = rows * (rows - 1) // 2
    print('probe rows {} features {} scipy {} numpy {} | condensed entries {} ({} 2^31-1) | 8*N^2 = {:.1f} GB'.format(
        rows, feats, scipy.__version__, np.__version__, entries, '>' if entries > 2 ** 31 - 1 else '<=',
        8.0 * rows * rows / 1e9))
    sys.stdout.flush()
    t0 = time.time()
    try:
        model = hierarchy.linkage(X, method='average', metric='cosine')
        labels = hierarchy.fcluster(model, 21, criterion='maxclust')
        status = 'ok ({} clusters at k=21)'.format(len(set(labels.tolist())))
    except Exception as e:                       # noqa: BLE001  (MemoryError, ValueError, OverflowError, ...)
        status = 'exception {}: {}'.format(type(e).__name__, e)
    print('linkage {} | {:.1f} s'.format(status, time.time() - t0))
    peak = read_cgroup('memory.peak')
    print('memory.peak {} bytes ({} GB) | memory.max {}'.format(
        peak, '{:.2f}'.format(int(peak) / 1e9) if peak.isdigit() else 'n/a', read_cgroup('memory.max')))
    sys.exit(0 if status.startswith('ok') else 1)


# ------------------------------------------------------------------------------------------ v4classify
MODELS = ('linear', 'rf', 'xgb')
DATASETS = ('breast_cancer', 'nasa', 'bike', 'adult')
# XGBClassifier on the classification datasets, XGBRegressor on nasa and bike
# (CFG in reports/block_d_final_plan_2026-10-09/checks/measure_fixes.py: task clf / reg).
CLASSIFICATION = ('breast_cancer', 'adult')
ALLOWED = ('linear', 'xgb_clf', 'summary')
# d4_numeric_rule_output.txt table rows: "<policy> <item> a -> b c -> d e -> f" = linear, rf, xgb by position
D4_ROW = re.compile(r'^\s*(floor|gt|delete|impute)\s+\S+\s+-?[0-9.]+\s+->\s')
D4_COLUMNS = {2: 'linear', 3: 'linear', 4: 'linear', 5: 'rf', 6: 'rf', 7: 'rf', 8: 'xgb', 9: 'xgb', 10: 'xgb'}


def keyword(tok):
    t = tok.strip(',:;()[]|').lower()
    return t if t in MODELS else None


def contexts(lines, ds0):
    """Per line: (dataset, model named by the last section header). A header is a line that ends with ':'
    or names a model followed by ':' (d3: '3. gt, RF: pair verdicts ...')."""
    out, ds, ctx = [], ds0, None
    for line in lines:
        toks = line.split()
        for t in toks:
            w = t.strip(',:;()[]|=').lower()
            if w in DATASETS:
                ds = w
                break
        s = line.strip()
        if s.startswith('==') or s.startswith('=' * 10):
            ctx = None
        if s.endswith(':') or any(t.endswith(':') and keyword(t) for t in toks):
            named = {keyword(t) for t in toks} - {None}
            ctx = named.pop() if len(named) == 1 else None
        out.append((ds, ctx))
    return out


def model_class(model, ds):
    if model == 'linear':
        return 'linear'
    if model == 'xgb':
        return 'xgb_clf' if ds in CLASSIFICATION else 'stop:xgb_regressor'
    if model == 'rf':
        return 'stop:rf'
    return 'stop:' + model


def whole_line_class(line, ds, ctx):
    toks = line.split()
    named = [k for k in (keyword(t) for t in toks) if k]
    if line.strip().startswith('=>') and not named:
        return 'summary'
    if len(set(named)) == 1:
        return model_class(named[0], ds)
    if not named and ctx:
        return model_class(ctx, ds)
    return 'stop:unattributed'


def position_model(toks, p, ctx, d4row):
    if d4row:
        return D4_COLUMNS.get(p, 'unattributed')
    if keyword(toks[p]):
        return 'model-keyword'              # the structure of the line changed
    for q in range(p - 1, -1, -1):
        k = keyword(toks[q])
        if k:
            return k
    return ctx or 'unattributed'


def pair_classes(old, new, ds, ctx, d4):
    if old.strip().startswith('=>') and new.strip().startswith('=>') and \
            not any(keyword(t) for t in old.split() + new.split()):
        return {'summary'}
    a, b = old.split(), new.split()
    if a == b:
        return {'stop:whitespace'}          # same words, other spacing: not a model number, so not allowed
    if sorted({keyword(t) for t in a} - {None}) != sorted({keyword(t) for t in b} - {None}):
        return {whole_line_class(old, ds, ctx), whole_line_class(new, ds, ctx)}
    d4a, d4b = d4 and bool(D4_ROW.match(old)), d4 and bool(D4_ROW.match(new))
    classes = set()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        for p in range(i1, i2):
            classes.add(model_class(position_model(a, p, ctx, d4a), ds))
        for p in range(j1, j2):
            classes.add(model_class(position_model(b, p, ctx, d4b), ds))
    return classes


def v4classify(argv):
    totals = dict(files=0, changed=0)
    for c in ALLOWED + ('stop',):
        totals[c] = 0
    for row in open(argv[0]):
        if not row.strip():
            continue
        ref, new, ds0 = row.rstrip('\n').split('\t')
        old_lines = open(ref).read().splitlines()
        new_lines = open(new).read().splitlines()
        d4 = os.path.basename(new).startswith('d4_numeric_rule')
        co, cn = contexts(old_lines, ds0), contexts(new_lines, ds0)
        counts = dict((c, 0) for c in ALLOWED + ('stop',))
        stops = []
        sm = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                continue
            units = []
            if tag == 'replace' and i2 - i1 == j2 - j1:
                for k in range(i2 - i1):
                    i, j = i1 + k, j1 + k
                    units.append((j + 1, new_lines[j], pair_classes(old_lines[i], new_lines[j], cn[j][0], cn[j][1], d4)))
            else:
                for i in range(i1, i2):
                    units.append((i + 1, '[-] ' + old_lines[i], {whole_line_class(old_lines[i], *co[i])}))
                for j in range(j1, j2):
                    units.append((j + 1, '[+] ' + new_lines[j], {whole_line_class(new_lines[j], *cn[j])}))
            for lineno, text, classes in units:
                bad = sorted(c for c in classes if c not in ALLOWED)
                if bad:
                    counts['stop'] += 1
                    stops.append('  STOP {}:{} {}: {}'.format(os.path.basename(new), lineno, ','.join(bad), text.strip()))
                elif 'xgb_clf' in classes:
                    counts['xgb_clf'] += 1
                elif 'linear' in classes:
                    counts['linear'] += 1
                else:
                    counts['summary'] += 1
        changed = sum(counts.values())
        totals['files'] += 1
        totals['changed'] += changed
        for c in counts:
            totals[c] += counts[c]
        if changed:
            print('{}: {} changed lines (linear {}, xgb_clf {}, summary {}, stop {})'.format(
                os.path.basename(new), changed, counts['linear'], counts['xgb_clf'], counts['summary'], counts['stop']))
            for s in stops:
                print(s)
    print('V4C_CLASSES files={files} changed={changed} linear={linear} xgb_clf={xgb_clf} summary={summary} '
          'stop={stop}'.format(**totals))


if __name__ == '__main__':
    commands = {'mac-order': mac_order, 'probe': probe, 'v4classify': v4classify}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        sys.exit('usage: calib_lib.py {mac-order|probe|v4classify} ...')
    commands[sys.argv[1]](sys.argv[2:])
