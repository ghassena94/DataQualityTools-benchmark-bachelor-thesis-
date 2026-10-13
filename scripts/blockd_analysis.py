"""Block D steps 6 and 8: analysis of driver runs (plan v2.1 §8; requirements R72-R110, R112).

Reads one or more full runs of scripts/blockd_driver.py (results.csv + manifest.json + inputs/), groups them by
fill (mean = primary, median = sensitivity §8.8), and prints:
  mean S2 per item (R77); pair verdicts by the exact sign-flip test on midranks (R78-R85), in both degenerate
  modes; references (a)-(d) recomputed from the frozen flags in <RUN>/inputs (R86-R91); concordance and the
  primary permutation test with Holm over the policies (R92-R97); Kendall tau-b (R98); share of gap closed (R99);
  random controls (R100-R101); the median sensitivity (R103-R104); the nasa D6 diagnostic (R105); and the
  plan §9 prediction scorecard (R106; §9 is only read).
--compare RUN_A RUN_B applies the V4 pass rule to two results.csv files (R107-R109) and exits 1 on STOP.

Run in the rein container from /rein (same settings as the driver):
    docker compose run --rm -T --no-deps --entrypoint python3 rein scripts/blockd_analysis.py RUN [RUN ...] [--out DIR]
    docker compose run --rm -T --no-deps --entrypoint python3 rein scripts/blockd_analysis.py --compare RUN_A RUN_B
    python3 scripts/blockd_analysis.py --selftest
--out (optional) must be a new or empty folder under reports/block_d/runs/; without it the script only prints.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import csv
import fractions
import importlib.util
import itertools
import json
import math
import os
import traceback

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blockd_driver as bd                                     # noqa: E402

KEY = ['dataset', 'version', 'policy', 'model', 'seed', 'scenario']
CMP_KEY = ['dataset', 'version', 'configuration', 'policy', 'model', 'seed', 'scenario']
DATA_COLS = ['item', 'task', 'fill', 'rows_kept', 'test_rows', 'cells_changed', 'excl_col_flags', 'format_only_fp',
             'rows_touched_without_format_only', 'parsable_tp', 'parsable_fp', 'errors_left_in_features',
             'label_errors_left', 'flagged_label_cells', 'degenerate', 'test_degenerate']
SCORE_COLS = ['score', 'f1', 'rmse', 'r2', 'precision', 'recall']
MODES = ['ranked_last', 'left_out']
REFS = ['a', 'b', 'c', 'd']
ALPHA = fractions.Fraction(1, 20)                               # every decision is p < 1/20 on exact fractions (§8.2)
PERM_SUPPORT = {5: 120, 4: 24, 3: 6, 2: 2}


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the pair rule (R78-R85)
def doubled_midranks(values):
    """Integer ranks x 2 with midranks for equal values (R83)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    r2 = [0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r2[order[k]] = i + j + 2                             # midrank (i+1 + j+1)/2, doubled
        i = j + 1
    return r2


def signflip(d):
    """Exact sign-flip test on midranks of |d| (ties after rounding to 12 significant digits, inf above all).
    Returns (T doubled, p as a Fraction) for the nonzero differences d."""
    mag = [math.inf if math.isinf(x) else float('%.12g' % abs(x)) for x in d]
    r2 = doubled_midranks(mag)
    T = sum(r if x > 0 else -r for x, r in zip(d, r2))
    dist = {0: 1}
    for r in r2:
        nxt = {}
        for s, c in dist.items():
            nxt[s + r] = nxt.get(s + r, 0) + c
            nxt[s - r] = nxt.get(s - r, 0) + c
        dist = nxt
    hits = sum(c for s, c in dist.items() if abs(s) >= abs(T))
    return T, fractions.Fraction(hits, 2 ** len(d))


def pair_verdict(a, b, mode):
    """a, b: dict(score, hash, deg) per seed (same seeds). Verdict '>' (a better), '<' or 'tie'; None if the pair
    is left out. Plan §8.2 + §8.7 (R79-R83)."""
    out = dict(verdict='tie', n=0, T='', p='', mean_d='', hash_rule=0, reason='')
    all_a, all_b = all(a['deg']), all(b['deg'])
    idx = list(range(len(a['deg'])))
    if mode == 'ranked_last':
        if all_a and all_b:
            return dict(out, reason='both degenerate')
        if all_a or all_b:
            return dict(out, verdict='<' if all_a else '>', reason='degenerate ranked last')
    else:
        if all_a or all_b:
            return None
        idx = [i for i in idx if not a['deg'][i] and not b['deg'][i]]
    if not idx:                                                  # left out: no seed where both are scored
        return dict(out, reason='no common scored seed')
    if all(a['hash'][i] == b['hash'][i] for i in idx):
        return dict(out, hash_rule=1, reason='same train_hash')
    d = []
    for i in idx:
        if a['deg'][i] and b['deg'][i]:
            d.append(0.0)
        elif a['deg'][i]:
            d.append(-math.inf)
        elif b['deg'][i]:
            d.append(math.inf)
        else:
            d.append(a['score'][i] - b['score'][i])
    finite = [x for x in d if math.isfinite(x)]
    mean_d = sum(finite) / len(finite) if finite else ''
    nz = [x for x in d if abs(x) >= 1e-9]
    if len(nz) <= 5:
        return dict(out, n=len(nz), mean_d=mean_d, reason='n <= 5')
    T, p = signflip(nz)
    v = ('>' if T > 0 else '<') if p < ALPHA else 'tie'
    return dict(out, verdict=v, n=len(nz), T=T, p=p, mean_d=mean_d, reason='sign-flip')


def ds_order(names):
    """The plan's dataset order; other (synthetic) datasets after it, by name."""
    return sorted(names, key=lambda ds: (bd.DATASETS.index(ds) if ds in bd.DATASETS else len(bd.DATASETS), ds))


def bundles_of(pairs):
    return {p['dataset'] for p in pairs}


def flip(v):
    return {'>': '<', '<': '>'}.get(v, v)


# ---------------------------------------------------------------- permutation test, Holm, tau-b (R94, R98)
def perm_distribution(items, verdicts, refvals):
    """Exact null of the concordant count of one dataset: reference values permuted among the items, one
    permutation shared by the models. verdicts: {(a, b): [verdict per model]}. Returns {count: Fraction}."""
    vals = [refvals[nm] for nm in items]
    dist, total = {}, 0
    for perm in itertools.permutations(vals):
        rv = dict(zip(items, perm))
        c = 0
        for (a, b), vs in verdicts.items():
            r = '>' if rv[a] > rv[b] else '<' if rv[a] < rv[b] else '='
            c += sum(1 for v in vs if v == r)
        dist[c] = dist.get(c, 0) + 1
        total += 1
    return {c: fractions.Fraction(k, total) for c, k in dist.items()}


def convolve(dists):
    out = {0: fractions.Fraction(1)}
    for d in dists:
        nxt = {}
        for c1, p1 in out.items():
            for c2, p2 in d.items():
                nxt[c1 + c2] = nxt.get(c1 + c2, 0) + p1 * p2
        out = nxt
    return out


def holm(ps):
    """Holm step-down adjusted p values, exact (Fractions in, Fractions out), and decisions: reject where the
    adjusted p < ALPHA, the strict rule of the pair test (plan §8.2)."""
    names = sorted(ps, key=lambda k: ps[k])
    m, running, adj = len(names), fractions.Fraction(0), {}
    for i, k in enumerate(names):
        running = max(running, min(fractions.Fraction(1), (m - i) * fractions.Fraction(ps[k])))
        adj[k] = running
    return adj, {k: adj[k] < ALPHA for k in adj}


def tau_b(nc, nd, n0, nref, ndown):
    den = (n0 - nref) * (n0 - ndown)
    return (nc - nd) / math.sqrt(den) if den > 0 else ''


def tau_from(verdicts, refdirs):
    """R98 from the pair verdicts and reference directions of one dataset x model: a pair tied on both sides
    counts in n_ref and in n_down, as in the standard tau-b."""
    cls = [classify(v, r) for v, r in zip(verdicts, refdirs)]
    return tau_b(cls.count('C'), cls.count('D'), len(cls), cls.count('reftie'), sum(1 for v in verdicts if v == 'tie'))


def gap_closed(item, floor, s4):
    """R99, ratio of means (A11) over the seeds where the item is scored; floor and S4 over the same seeds."""
    idx = [i for i, x in enumerate(item['score']) if x is not None]
    if not idx:
        return ''
    f = np.mean([floor['score'][i] for i in idx])
    den = np.mean([s4['score'][i] for i in idx]) - f
    return float((np.mean([item['score'][i] for i in idx]) - f) / den) if den != 0 else ''


def classify(v, r):
    if r == '=':
        return 'reftie'
    if v == 'tie':
        return 'T'
    return 'C' if v == r else 'D'


# ---------------------------------------------------------------- loading runs (R72-R76)
def read_manifest(run):
    p = os.path.join(run, 'manifest.json')
    if not os.path.exists(p):
        raise Refused('{}: no manifest.json'.format(run))
    return json.load(open(p))


def check_verdict_files(run, man):
    """The frozen and addendum verdict files read here must be the ones the run hashed (R67)."""
    want = man.get('expected_verdict_files') or {}
    for p in (bd.FROZEN_VERDICTS, bd.ADDENDUM_VERDICTS):
        got = bd.sha256_file(p) if os.path.exists(p) else 'missing'
        if want.get(p) != got:
            raise Refused('{}: sha256 of {} is {} now, the run manifest has {}'.format(run, p, got[:12], str(want.get(p))[:12]))


def provenance(env):
    """What two runs must share to be analysed together: git HEAD, image and host fingerprint.
    The hostname is only recorded: under docker compose run it is the container ID."""
    return (env.get('git_head'), env.get('variables', {}).get('REIN_IMAGE_ID'), env.get('host_fingerprint'))


def load_runs(runs):
    groups, prov = {}, None
    for run in runs:
        man = read_manifest(run)
        if man.get('mode') != 'full' or man.get('status') != 'ok':
            raise Refused('{}: mode {} status {} (need a full run with status ok)'.format(run, man.get('mode'), man.get('status')))
        check_verdict_files(run, man)
        env = man.get('environment', {})
        this = provenance(env)
        if prov is not None and this != prov:
            raise Refused('runs from different git HEAD, image or host: {} vs {}'.format(prov, this))
        prov = this
        df = pd.read_csv(os.path.join(run, 'results.csv'), dtype=str, keep_default_na=False)
        groups.setdefault(man['fill'], []).append((run, man, df))
    if 'mean' not in groups:
        raise Refused('no mean-fill run among {}'.format(runs))
    out = {}
    for fill, lst in groups.items():
        df = pd.concat([x[2] for x in lst], ignore_index=True)
        dup = df.duplicated(KEY)
        if dup.any():
            raise Refused('fill {}: {} duplicate result keys, e.g. {}'.format(fill, int(dup.sum()), df[dup].iloc[0][KEY].tolist()))
        out[fill] = dict(runs=lst, df=df, index=index_results(df))
    return out


def fnum(s):
    return float(s) if s != '' else None


def index_results(df):
    """{(ds, version, model, scenario): {seed: row}}."""
    idx = {}
    for r in df.to_dict('records'):
        idx.setdefault((r['dataset'], r['version'], r['model'], r['scenario']), {})[int(r['seed'])] = r
    return idx


def series(idx, ds, version, model, scenario, seeds):
    rows = idx.get((ds, version, model, scenario))
    if rows is None or any(s not in rows for s in seeds):
        return None
    rs = [rows[s] for s in seeds]
    raw = 'f1' if rs[0]['task'] == 'classification' else 'rmse'
    return dict(score=[fnum(r['score']) for r in rs], hash=[r['train_hash'] for r in rs],
                deg=[r['degenerate'] == '1' for r in rs], raw=[fnum(r[raw]) for r in rs],
                rows_kept=[int(r['rows_kept']) for r in rs])


def dataset_bundle(run, man, ds, flags_dir=None, data_root=None):
    """Items and references (a)-(d) from the run's input copies, sha256-checked against the manifest (R74)."""
    base = os.path.join(run, 'inputs', ds)
    names = dict(dirty='dirty.csv', clean='clean.csv', errors='actual_errors.csv', **{c: c + '.csv' for c in bd.CONFIGS})
    files = {}
    for k, nm in names.items():
        p = os.path.join(base, nm)
        if not os.path.exists(p):
            if not (flags_dir and data_root):
                raise Refused('{}: {} missing and no --flags_dir/--data_root given'.format(run, p))
            p = os.path.join(flags_dir if k in bd.CONFIGS else data_root, ds, nm)
        if bd.sha256_file(p) != man['inputs'].get('inputs/{}/{}'.format(ds, nm)):
            raise Refused('{}: sha256 of {} differs from the manifest'.format(run, p))
        files[k] = p
    bd.ns['D'] = data_root or man['args']['data_root']
    data, full, restricted = bd.cached(ds, bd.CFG[ds], files)
    items = bd.make_items(restricted)
    if [[nm, m] for nm, m in items] != man['items'][ds]:
        raise Refused('{}: items {} differ from the manifest {}'.format(ds, items, man['items'][ds]))
    ref = bd.references(data, full, restricted, items)
    verdicts = bd.expected_verdicts(ds, items, ref)
    return dict(items=items, ref=ref, verdicts=verdicts, n_train=len(bd.split(data, 0)[0]))


# ---------------------------------------------------------------- the analysis
class Out:
    def __init__(self):
        self.lines, self.tables = [], {}

    def say(self, s=''):
        print(s, flush=True)
        self.lines.append(s)

    def add(self, table, row):
        self.tables.setdefault(table, []).append(row)


def ref_dir(ref, a, b, k, pol):
    if k == 'd':
        m = bd.cmp_mech(ref[a]['d'][pol], ref[b]['d'][pol])
        return '=' if not m else '>' if m > 0 else '<'
    return '>' if ref[a][k] > ref[b][k] else '<' if ref[a][k] < ref[b][k] else '='


def item_series(G, ds, items, pol, model, seeds, extra=()):
    """Per-seed S2 of every item (first configuration; members must agree, R77) and of extra versions."""
    idx = G['index']
    out = {}
    for nm, members in items:
        ss = [series(idx, ds, '{}/{}'.format(c, pol), model, 'S2', seeds) for c in members]
        if any(s is None for s in ss):
            return None
        if any(s['score'] != ss[0]['score'] for s in ss[1:]):
            raise Refused('{} {} {} item {}: members have different scores'.format(ds, pol, model, nm))
        out[nm] = ss[0]
    for name, version in extra:
        s = series(idx, ds, version, model, 'S2', seeds)
        if s is not None:
            out[name] = s
    return out


def analyse_fill(fill, G, bundles, O, seeds_of):
    """Pair verdicts, mean S2, gap closed and controls of one fill group. Returns the pair records."""
    pairs = []
    dsets = [ds for ds in ds_order(bundles) if any(k[0] == ds for k in G['index'])]
    for ds in dsets:
        B, seeds = bundles[ds], seeds_of[ds]
        items = B['items']
        names = [nm for nm, _ in items]
        pols = [p for p in bd.POLICIES if ('{}/{}'.format(items[0][1][0], p)) in {k[1] for k in G['index'] if k[0] == ds}]
        for model in bd.MODELS:
            floor = series(G['index'], ds, 'floor', model, 'S2', seeds)
            s4 = series(G['index'], ds, 'clean', model, 'S4', seeds)
            for nm, s in (('floor', floor), ('clean S4', s4)):
                mean_row(O, fill, ds, 'none', model, nm, s)
            gap_ok = pair_verdict(s4, floor, 'ranked_last')['verdict'] == '>'
            for pol in pols:
                extra = [('perfect', 'perfect/' + pol), ('always_positive', 'always_positive/' + pol),
                         (bd.D6_NAME, '{}/{}'.format(bd.D6_NAME, pol))]
                if pol == 'delete':
                    extra += [('control/' + c, 'control/' + c) for c in bd.CONFIGS]
                S = item_series(G, ds, items, pol, model, seeds, extra)
                if S is None:
                    continue
                for nm, s in S.items():
                    mean_row(O, fill, ds, pol, model, nm, s)
                for nm in names + ['perfect']:
                    if gap_ok and nm in S:
                        O.add('gap_closed', dict(fill=fill, dataset=ds, policy=pol, model=model, item=nm,
                                                 gap_closed=gap_closed(S[nm], floor, s4)))
                for (na, _), (nb, _) in itertools.combinations(items, 2):
                    rec = dict(fill=fill, dataset=ds, policy=pol, model=model, pair='{} vs {}'.format(na, nb), a=na, b=nb)
                    for mode in MODES:
                        v = pair_verdict(S[na], S[nb], mode)
                        rec[mode] = v
                    for k in REFS:
                        rec['ref_' + k] = ref_dir(B['ref'], na, nb, k, pol)
                    pairs.append(rec)
                if pol == 'delete':
                    for nm, members in items:
                        c = members[0]
                        dv, cv = S[nm], S.get('control/' + c)
                        ks = [B['n_train'] - k for k in dv['rows_kept']]
                        ok = cv is not None and not any(dv['deg']) and all(0 < k < B['n_train'] for k in ks)
                        res = pair_verdict(dv, cv, 'ranked_last') if ok else None
                        word = {'>': 'detector better', '<': 'detector worse', 'tie': 'tie'}[res['verdict']] if res else 'n/a'
                        O.add('controls', dict(fill=fill, dataset=ds, model=model, item=nm, configuration=c,
                                               k='{}-{}'.format(min(ks), max(ks)), verdict=word,
                                               p=float(res['p']) if res and res['p'] != '' else '',
                                               n=res['n'] if res else ''))
                if ds in bd.D6 and bd.D6_NAME in S:
                    v = pair_verdict(S[bd.D6_NAME], S['Raha'], 'ranked_last')
                    O.add('d6', dict(fill=fill, dataset=ds, policy=pol, model=model,
                                     d6=mean_of(S[bd.D6_NAME]), raha=mean_of(S['Raha']), perfect=mean_of(S['perfect']),
                                     verdict_vs_raha=v['verdict'], p=float(v['p']) if v['p'] != '' else ''))
    return pairs


def mean_of(s):
    sc = [x for x in s['score'] if x is not None]
    return float(np.mean(sc)) if sc else ''


def mean_row(O, fill, ds, pol, model, nm, s):
    if s is None:
        return
    sc = [x for x in s['score'] if x is not None]
    raw = [x for x in s['raw'] if x is not None]
    O.add('mean_s2', dict(fill=fill, dataset=ds, policy=pol, model=model, version=nm,
                          mean=float(np.mean(sc)) if sc else '', sd=float(np.std(sc, ddof=1)) if len(sc) > 1 else '',
                          raw_mean=float(np.mean(raw)) if raw else '', seeds_scored=len(sc), degenerate=sum(s['deg'])))


def concordance(pairs, bundles, O, fill, label):
    """C/D/T, shares, permutation p (a, b, c), Holm on the primary rows, tau-b (R92-R98, R102)."""
    pols = sorted({p['policy'] for p in pairs}, key=bd.POLICIES.index)
    primary_p = {}
    for mode in MODES:
        for k in REFS:
            for pol in pols:
                P = [p for p in pairs if p['policy'] == pol and p[mode] is not None]
                cls = [classify(p[mode]['verdict'], p['ref_' + k]) for p in P]
                C, D, T, RT = (cls.count(x) for x in ('C', 'D', 'T', 'reftie'))
                row = dict(fill=fill, policy=pol, reference=k, mode=mode, C=C, D=D, T=T, reftie=RT,
                           share_all=C / (C + D + T) if C + D + T else '', share_decided=C / (C + D) if C + D else '',
                           perm_p='', holm_p='', decision='')
                if k != 'd':
                    dists = []
                    for ds in bundles:
                        Pd = [p for p in P if p['dataset'] == ds]
                        if not Pd:
                            continue
                        its = [nm for nm, _ in bundles[ds]['items'] if any(nm in (p['a'], p['b']) for p in Pd)]
                        ver = {}
                        for p in Pd:
                            ver.setdefault((p['a'], p['b']), []).append(p[mode]['verdict'])
                        dists.append(perm_distribution(its, ver, {nm: bundles[ds]['ref'][nm][k] for nm in its}))
                    dist = convolve(dists)
                    p_exact = sum((pr for c, pr in dist.items() if c >= C), fractions.Fraction(0))
                    row['perm_p'] = float(p_exact)
                    if k == 'a' and mode == 'ranked_last':
                        primary_p[pol] = p_exact
                taus = []
                for ds in bundles:
                    for model in bd.MODELS:
                        sub = [p for p in P if p['dataset'] == ds and p['model'] == model]
                        if sub:
                            taus.append(tau_from([p[mode]['verdict'] for p in sub], [p['ref_' + k] for p in sub]))
                            O.add('tau', dict(fill=fill, dataset=ds, policy=pol, model=model, reference=k, mode=mode, tau_b=taus[-1]))
                row['tau_b_mean'] = float(np.mean([t for t in taus if t != ''])) if any(t != '' for t in taus) else ''
                O.add('concordance', row)
    adj, dec = holm(primary_p) if primary_p else ({}, {})
    for row in O.tables.get('concordance', []):
        if row['fill'] == fill and row['reference'] == 'a' and row['mode'] == 'ranked_last' and row['policy'] in adj:
            row['holm_p'], row['decision'] = float(adj[row['policy']]), 'reject H0' if dec[row['policy']] else 'keep H0'
    O.say('')
    O.say('== concordance, fill {} ({}): C/D/T, share of all pairs, share of decided pairs, permutation p'.format(fill, label))
    for row in O.tables['concordance']:
        if row['fill'] != fill:
            continue
        tag = 'PRIMARY' if (row['reference'] == 'a' and row['mode'] == 'ranked_last') else 'descriptive'
        O.say('  {:<7} ref ({}) {:<12} C {:>3} D {:>3} T {:>3} reftie {:>3} | all {} decided {} | perm p {} holm p {} {} [{}]'.format(
            row['policy'], row['reference'], row['mode'], row['C'], row['D'], row['T'], row['reftie'], fmt(row['share_all']),
            fmt(row['share_decided']), fmt(row['perm_p']), fmt(row['holm_p']), row['decision'], tag))


def fmt(v, nd=3):
    if v == '' or v is None:
        return '-'
    if isinstance(v, fractions.Fraction):
        v = float(v)
    return ('{:.%df}' % nd).format(v) if isinstance(v, float) else str(v)


def print_pairs(pairs, O, frozen):
    O.say('')
    O.say('== pair verdicts (a > b means a better on S2); ranked-last / left-out; refs (a)(b)(c)(d); expected (c61ee72)')
    for p in pairs:
        rl, lo = p['ranked_last'], p['left_out']
        exp = frozen.get((p['dataset'], p['policy'], p['pair']), '')
        p['expected'] = exp
        O.add('pair_verdicts', dict(fill=p['fill'], dataset=p['dataset'], policy=p['policy'], model=p['model'], pair=p['pair'],
                                    verdict_ranked_last=rl['verdict'], verdict_left_out=lo['verdict'] if lo else 'left out',
                                    n=rl['n'], T2=rl['T'], p=float(rl['p']) if rl['p'] != '' else '', mean_d=rl['mean_d'],
                                    hash_rule=rl['hash_rule'], reason=rl['reason'],
                                    **{'ref_' + k: p['ref_' + k] for k in REFS},
                                    **{'class_' + k: classify(rl['verdict'], p['ref_' + k]) for k in REFS}, expected=exp))
        O.say('  {:<6} {:<13} {:<7} {:<6} {:<42} {:<4} {:<9} n {:>2} p {:<7} | (a){} (b){} (c){} (d){} | {}'.format(
            p['fill'], p['dataset'], p['policy'], p['model'], p['pair'], rl['verdict'], lo['verdict'] if lo else 'out',
            rl['n'], fmt(rl['p'], 4), p['ref_a'], p['ref_b'], p['ref_c'], p['ref_d'], exp))


def scorecard(pairs, bundles, O, frozen_rows):
    """Plan §9 predictions, ranked last, against (a), pooled over the datasets present (R106, A23)."""
    P = [p for p in pairs if p['fill'] == 'mean']
    cls = lambda p, k='a': classify(p['ranked_last']['verdict'], p['ref_' + k])

    def share(pol, k='a'):
        c = [cls(p, k) for p in P if p['policy'] == pol]
        C, D = c.count('C'), c.count('D')
        return C / (C + D) if C + D else None
    res = []
    sh = {pol: share(pol) for pol in bd.POLICIES}
    if all(v is not None for v in sh.values()):
        res.append((1, 'GT {} < delete {} and < impute {}'.format(fmt(sh['gt']), fmt(sh['delete']), fmt(sh['impute'])),
                    sh['gt'] < sh['delete'] and sh['gt'] < sh['impute']))
    else:
        res.append((1, 'needs all three policies', None))
    if sh['delete'] is not None and sh['impute'] is not None:
        res.append((2, 'delete {} impute {} (>= 0.70 each)'.format(fmt(sh['delete']), fmt(sh['impute'])),
                    sh['delete'] >= 0.70 and sh['impute'] >= 0.70))
    ok3, txt3 = True, []
    for pol in bd.POLICIES:
        c = [cls(p, 'd') for p in P if p['policy'] == pol and p['ref_d'] != '=' and p['ranked_last']['verdict'] != 'tie']
        s = c.count('C') / len(c) if c else None
        txt3.append('{} {}'.format(pol, fmt(s)))
        ok3 = ok3 and (s is None or s >= 0.70)
    res.append((3, 'against (d): ' + ', '.join(txt3), ok3))
    und = {(r['dataset'], r['pair']) for r in frozen_rows if r['policy'] == 'impute' and r['expected'] == 'undetermined'}
    c4 = [p for p in P if p['policy'] == 'impute' and (p['dataset'], p['pair']) in und]
    ties = sum(1 for p in c4 if p['ranked_last']['verdict'] == 'tie')
    res.append((4, '{} of {} undetermined impute cases tie'.format(ties, len(c4)), ties > len(c4) / 2 if c4 else None))
    tie_share = lambda dss: (lambda L: sum(1 for p in L if p['ranked_last']['verdict'] == 'tie') / len(L) if L else None)(
        [p for p in P if p['dataset'] in dss])
    clf_s, reg_s = tie_share({'breast_cancer', 'adult'}), tie_share({'nasa', 'bike'})
    bct = [p for p in P if p['dataset'] == 'breast_cancer' and p['model'] in ('rf', 'xgb')]
    bct_s = sum(1 for p in bct if p['ranked_last']['verdict'] == 'tie') / len(bct) if bct else None
    res.append((5, 'tie share clf {} reg {}; bc RF+XGB ties {}'.format(fmt(clf_s), fmt(reg_s), fmt(bct_s)),
                None if None in (clf_s, reg_s, bct_s) else (clf_s > reg_s and bct_s > 0.5)))
    if 'nasa' in bundles:
        ok6, txt6 = True, []
        for pol in ('gt', 'impute'):
            for it in ('GE-hand', 'Raha'):
                good = 0
                for model in bd.MODELS:
                    below = [p for p in P if p['dataset'] == 'nasa' and p['policy'] == pol and p['model'] == model
                             and it in (p['a'], p['b']) and not {p['a'], p['b']} == {'GE-hand', 'Raha'}
                             and ((p['a'] == it and p['ranked_last']['verdict'] == '<') or (p['b'] == it and p['ranked_last']['verdict'] == '>'))]
                    good += not below
                txt6.append('{} {} top in {}/3'.format(pol, it, good))
                ok6 = ok6 and good >= 2
        hr = [p for p in P if p['dataset'] == 'nasa' and p['policy'] == 'impute' and p['pair'] == 'GE-hand vs Raha'
              and p['ranked_last']['verdict'] == '>']
        txt6.append('impute GE-hand > Raha in {}/3'.format(len(hr)))
        rf = [r for r in O.tables.get('rf_perfect_floor', [])]
        ok6 = ok6 and len(hr) >= 2 and all(r['verdict'] == 'tie' for r in rf) and bool(rf)
        txt6.append('RF perfect/impute vs floor: {}'.format(rf[0]['verdict'] if rf else 'n/a'))
        res.append((6, '; '.join(txt6), ok6))
    else:
        res.append((6, 'nasa not present', None))
    if any(ds in bundles for ds in ('nasa', 'bike')):
        ok7, txt7 = True, []
        for ds in ('nasa', 'bike'):
            if ds not in bundles:
                continue
            for nm, members in bundles[ds]['items']:
                dmech = bundles[ds]['ref'][nm]['d']['delete']
                if isinstance(dmech, str) or dmech < 0.98:
                    continue
                rows = [r for r in O.tables.get('controls', []) if r['fill'] == 'mean' and r['dataset'] == ds and r['item'] == nm]
                good = sum(1 for r in rows if r['verdict'] == 'detector better')
                txt7.append('{} {} {}/3'.format(ds, nm, good))
                ok7 = ok7 and good >= 2
        res.append((7, 'beats its control: ' + ', '.join(txt7), ok7))
    else:
        res.append((7, 'nasa and bike not present', None))
    if 'bike' in bundles:
        ok8, txt8 = True, []
        for pol in ('gt', 'impute'):
            L = [p for p in P if p['dataset'] == 'bike' and p['policy'] == pol and p['pair'] == 'GE-hand vs Raha']
            good = sum(1 for p in L if cls(p, 'a') == 'D' and cls(p, 'c') == 'C')
            txt8.append('{} {}/3'.format(pol, good))
            ok8 = ok8 and good >= 2
        res.append((8, 'bike GE-hand vs Raha discordant (a) and concordant (c): ' + ', '.join(txt8), ok8))
    else:
        res.append((8, 'bike not present', None))
    O.say('')
    O.say('== plan §9 prediction scorecard (ranked last, reference (a), mean fill, datasets present)')
    for k, txt, ok in res:
        word = 'n/a' if ok is None else 'HOLDS' if ok else 'REFUTED'
        O.say('  {} {:<8} {}'.format(k, word, txt))
        O.add('predictions', dict(prediction=k, result=word, measured=txt))
    exp_disc = [r for r in frozen_rows if r['policy'] == 'gt' and r['expected'] == 'discordant']
    O.say('  prediction 1, the expected discordant GT pairs, observed per model (linear/rf/xgb):')
    for r in exp_disc:
        obs = [p['ranked_last']['verdict'] for p in P if p['dataset'] == r['dataset'] and p['policy'] == 'gt' and p['pair'] == r['pair']]
        if obs:
            O.say('    {:<14} {:<42} ref (a) {:<40} observed {}'.format(r['dataset'], r['pair'], r['reference_a'], '/'.join(obs)))


def analyse(runs, out_dir=None, flags_dir=None, data_root=None):
    O = Out()
    groups = load_runs(runs)
    seeds_of, bundles = {}, {}
    for fill, G in groups.items():
        for run, man, df in G['runs']:
            for ds in man['datasets']:
                s = sorted(int(x) for x in df.loc[df['dataset'] == ds, 'seed'].unique())
                if seeds_of.setdefault(ds, s) != s:
                    raise Refused('{}: seeds differ between runs'.format(ds))
                if ds not in bundles:
                    bundles[ds] = dataset_bundle(run, man, ds, flags_dir, data_root)
    mean_ds = ds_order({ds for _, man, _ in groups['mean']['runs'] for ds in man['datasets']})
    mean_pol = {p for _, man, _ in groups['mean']['runs'] for p in man['policies']}
    label = 'primary' if set(mean_ds) == set(bd.DATASETS) and mean_pol == set(bd.POLICIES) else 'interim'
    O.say('Block D analysis ({}): runs {}'.format(label, ', '.join(runs)))
    O.say('mean fill: datasets {}; median fill: {}'.format(' '.join(mean_ds), 'present' if 'median' in groups else 'absent'))
    frozen_rows = pd.read_csv(bd.FROZEN_VERDICTS, dtype=str, keep_default_na=False).to_dict('records')
    frozen = {(r['dataset'], r['policy'], r['pair']): r['expected'] for r in frozen_rows}
    add_rows = pd.read_csv(bd.ADDENDUM_VERDICTS, dtype=str, keep_default_na=False).to_dict('records')
    add = {(r['dataset'], r['policy'], r['pair']): r['expected'] for r in add_rows}
    O.say('')
    O.say('== references (a) published Table 3, (b) row F1, (c) model-visible F1; (d) mechanism per policy')
    n_match = n_all = 0
    for ds in ds_order(bundles):
        B = bundles[ds]
        for nm, _ in B['items']:
            r = B['ref'][nm]
            O.say('  {:<13} {:<34} (a) {:.3f} (b) {:.4f} (c) {:.4f} (d) {}'.format(
                ds, nm, r['a'], r['b'], r['c'], ' / '.join(str(bd.fmt_mech(r['d'][p])) for p in bd.POLICIES)))
        res = bd.compare_verdicts(ds, B['verdicts'], bd.ADDENDUM_VERDICTS, strict=True)
        if res:
            n_match, n_all = n_match + res[0], n_all + res[1]
            if res[0] != res[1]:
                raise Refused('{}: recomputed expected verdicts differ from the addendum: {}'.format(ds, res[2][:3]))
        if ds == 'bike':
            for k in ('a', 'c'):
                O.say('  bike GE-hand vs Raha under ({}): GE-hand {} Raha'.format(k, ref_dir(B['ref'], 'GE-hand', 'Raha', k, 'gt')))
            O.say('  (a discordance under (a) only is an excluded-column artefact, plan §0 / §8.3)')
    O.say('  recomputed expected verdicts = addendum: {}/{}'.format(n_match, n_all))
    diff = [k for k in frozen if k[0] in bundles and add.get(k) != frozen[k]]
    O.say('  frozen (c61ee72) vs addendum expected verdicts differing: {}{}'.format(len(diff), ' ' + str(diff) if diff else ''))
    all_pairs = {}
    for fill in ('mean', 'median'):
        if fill not in groups:
            continue
        pairs = analyse_fill(fill, groups[fill], bundles, O, seeds_of)
        all_pairs[fill] = pairs
        print_mean(O, fill)
        print_pairs(pairs, O, frozen)
        concordance(pairs, {ds: b for ds, b in bundles.items() if any(p['dataset'] == ds for p in pairs)}, O, fill, label)
        joined = sum(1 for p in pairs if p['model'] == 'linear' and p['expected'])
        O.say('  pairs joined with the frozen expected file: {} (87 for four datasets)'.format(joined))
        O.say('')
        O.say('== discordant pairs against (a), ranked last, fill {}'.format(fill))
        for p in pairs:
            if classify(p['ranked_last']['verdict'], p['ref_a']) == 'D':
                O.say('  {:<13} {:<7} {:<6} {} -> observed {}, (a) {}'.format(p['dataset'], p['policy'], p['model'], p['pair'],
                                                                            p['ranked_last']['verdict'], p['ref_a']))
    rf_perfect_floor(groups, seeds_of, O)
    print_controls(O)
    print_gap(O)
    print_d6(O)
    if 'median' in all_pairs:
        sensitivity(all_pairs['mean'], all_pairs['median'], groups, seeds_of, O)
    scorecard(all_pairs['mean'], {ds: b for ds, b in bundles.items() if ds in mean_ds}, O, frozen_rows)
    if out_dir:
        write_outputs(out_dir, O)
    return 0


def rf_perfect_floor(groups, seeds_of, O):
    """Prediction 6, last part: nasa RF perfect + impute vs floor by the pair rule."""
    G = groups['mean']
    if 'nasa' not in seeds_of:
        return
    a = series(G['index'], 'nasa', 'perfect/impute', 'rf', 'S2', seeds_of['nasa'])
    b = series(G['index'], 'nasa', 'floor', 'rf', 'S2', seeds_of['nasa'])
    if a and b:
        O.add('rf_perfect_floor', dict(verdict=pair_verdict(a, b, 'ranked_last')['verdict']))


def print_mean(O, fill):
    O.say('')
    O.say('== mean S2 (oriented: F1 or -RMSE) +- sd over scored seeds; raw metric; degenerate seeds; fill {}'.format(fill))
    for r in O.tables.get('mean_s2', []):
        if r['fill'] == fill:
            O.say('  {:<13} {:<7} {:<6} {:<34} {:>9} +- {:<8} raw {:>9} scored {:>2} deg {:>2}'.format(
                r['dataset'], r['policy'], r['model'], r['version'], fmt(r['mean'], 4), fmt(r['sd'], 4), fmt(r['raw_mean'], 4),
                r['seeds_scored'], r['degenerate']))


def print_controls(O):
    O.say('')
    O.say('== random-deletion controls: delete(c) vs control(c) by the pair rule (descriptive)')
    for r in O.tables.get('controls', []):
        O.say('  {:<6} {:<13} {:<6} {:<34} k {:<12} {}'.format(r['fill'], r['dataset'], r['model'], r['item'], r['k'], r['verdict']))
    O.say('  caveat: a tie can mean the deleted errors are harmless to the model; read it with the ground-truth repair result')
    O.say('  caveat: the control does not preserve the class balance of the deleted rows (bc, adult)')


def print_gap(O):
    O.say('')
    O.say('== share of gap closed (mean S2 - mean floor) / (mean S4 - mean floor), where S4 beats the floor by the pair rule')
    for r in O.tables.get('gap_closed', []):
        O.say('  {:<6} {:<13} {:<7} {:<6} {:<34} {}'.format(r['fill'], r['dataset'], r['policy'], r['model'], r['item'], fmt(r['gap_closed'])))


def print_d6(O):
    rows = O.tables.get('d6', [])
    if rows:
        O.say('')
        O.say('== D6 diagnostic (nasa {}, never ranked or counted): mean S2 beside Raha and perfect'.format(bd.D6_NAME))
        for r in rows:
            O.say('  {:<6} {:<7} {:<6} D6 {} Raha {} perfect {} | D6 vs Raha {} (p {})'.format(
                r['fill'], r['policy'], r['model'], fmt(r['d6'], 4), fmt(r['raha'], 4), fmt(r['perfect'], 4), r['verdict_vs_raha'], fmt(r['p'], 4)))


def sensitivity(mean_pairs, median_pairs, groups, seeds_of, O):
    """§8.8: verdict changes mean -> median, C/D/T against (a) under both fills; bike fill invariance (R103, R104)."""
    O.say('')
    O.say('== median sensitivity (descriptive)')
    med = {(p['dataset'], p['policy'], p['model'], p['pair']): p for p in median_pairs}
    keys = sorted({(p['dataset'], p['policy'], p['model']) for p in mean_pairs}, key=lambda k: (ds_order(bundles_of(mean_pairs)).index(k[0]), bd.POLICIES.index(k[1]), k[2]))
    for ds, pol, model in keys:
        A = [p for p in mean_pairs if (p['dataset'], p['policy'], p['model']) == (ds, pol, model)]
        if not all((ds, pol, model, p['pair']) in med for p in A):
            continue
        row = dict(dataset=ds, policy=pol, model=model)
        for mode in MODES:
            ch = [p['pair'] for p in A if (p[mode] or {}).get('verdict') != (med[(ds, pol, model, p['pair'])][mode] or {}).get('verdict')]
            row['changed_' + mode] = len(ch)
            row['changed_pairs_' + mode] = '; '.join(ch)
        for fill, L in (('mean', A), ('median', [med[(ds, pol, model, p['pair'])] for p in A])):
            c = [classify(p['ranked_last']['verdict'], p['ref_a']) for p in L]
            row['CDT_' + fill] = '{}/{}/{}'.format(c.count('C'), c.count('D'), c.count('T'))
        O.add('sensitivity', row)
        O.say('  {:<13} {:<7} {:<6} changed {} (left out {}) | C/D/T mean {} median {} | {}'.format(
            ds, pol, model, row['changed_ranked_last'], row['changed_left_out'], row['CDT_mean'], row['CDT_median'],
            row['changed_pairs_ranked_last']))
    if 'bike' in seeds_of and 'median' in groups:
        bad = []
        ia, ib = groups['mean']['index'], groups['median']['index']
        for key, rows in ia.items():
            if key[0] != 'bike' or not (key[1] == 'floor' or key[1].endswith('/gt') or key[1].endswith('/delete') or key[1].startswith('control/')):
                continue
            for s, r in rows.items():
                q = ib.get(key, {}).get(s)
                if q is None or q['train_hash'] != r['train_hash'] or q['score'] != r['score']:
                    bad.append((key, s))
        O.say('  bike fill invariance (floor, GT, delete, controls): {}'.format('holds' if not bad else 'VIOLATED in {} rows, e.g. {}'.format(len(bad), bad[:3])))


def write_outputs(out_dir, O):
    out = bd.resolve_out(out_dir)
    os.makedirs(out, exist_ok=True)
    bd.write_atomic(os.path.join(out, 'analysis.txt'), '\n'.join(O.lines) + '\n')
    names = dict(mean_s2='mean_s2.csv', pair_verdicts='pair_verdicts.csv', concordance='concordance.csv', controls='controls.csv',
                 sensitivity='sensitivity.csv', gap_closed='gap_closed.csv', predictions='predictions.csv', tau='tau_b.csv', d6='d6.csv')
    for t, fn in names.items():
        rows = O.tables.get(t, [])
        cols = list(rows[0]) if rows else ['empty']
        with open(os.path.join(out, fn + '.tmp'), 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
            w.writeheader()
            for r in rows:
                w.writerow({k: bd.fmt_value(v) if not isinstance(v, fractions.Fraction) else repr(float(v)) for k, v in r.items()})
        os.replace(os.path.join(out, fn + '.tmp'), os.path.join(out, fn))


# ---------------------------------------------------------------- --compare (R107-R109)
def compare(run_a, run_b, say=print):
    ma, mb = read_manifest(run_a), read_manifest(run_b)
    for k in ('datasets', 'fill', 'seeds', 'policies'):
        if ma.get(k) != mb.get(k):
            say('STOP: {} differs ({} vs {})'.format(k, ma.get(k), mb.get(k)))
            say('V4d STOP')
            return 1, 'STOP'
    A = pd.read_csv(os.path.join(run_a, 'results.csv'), dtype=str, keep_default_na=False)
    B = pd.read_csv(os.path.join(run_b, 'results.csv'), dtype=str, keep_default_na=False)
    ka, kb = A.set_index(CMP_KEY), B.set_index(CMP_KEY)
    missing = set(ka.index) ^ set(kb.index)
    if missing or ka.index.duplicated().any() or kb.index.duplicated().any():
        say('STOP: {} keys only in one run (or duplicated keys), e.g. {}'.format(len(missing), sorted(missing)[:3]))
        say('V4d STOP')
        return 1, 'STOP'
    kb = kb.loc[ka.index]
    counts, cells = {}, []
    for col in [c for c in A.columns if c not in CMP_KEY + ['fit_s', 'timestamp']]:
        neq = ka[col].values != kb[col].values
        for i in np.flatnonzero(neq):
            key = ka.index[i]
            cat = 'train_hash' if col == 'train_hash' else 'data' if col in DATA_COLS else 'scores ' + key[4]
            counts[(cat, key[0])] = counts.get((cat, key[0]), 0) + 1
            cells.append((key, col, ka[col].values[i], kb[col].values[i], cat))
    if not cells:
        verdict = 'PASS'
    elif all(c[4] == 'scores linear' or (c[4] == 'scores xgb' and c[0][0] in ('breast_cancer', 'adult')) for c in cells):
        verdict = 'PASS WITH NOTE'
    else:
        verdict = 'STOP'
    say('differing cells per category x dataset: {}'.format(dict(sorted(counts.items())) or 'none'))
    for key, col, va, vb, cat in cells:
        say('  {} {} {!r} vs {!r} [{}]'.format('|'.join(map(str, key)), col, va, vb, cat))
    if cells:
        changed = verdict_changes(run_a, ma, A, run_b, B)
        say('pair verdicts that differ between the runs: {}'.format(len(changed)))
        for c in changed:
            say('  ' + c)
    say('V4d {}'.format(verdict))
    return (0 if verdict != 'STOP' else 1), verdict


def verdict_changes(run_a, ma, A, run_b, B):
    out = []
    ia, ib = index_results(A), index_results(B)
    for ds in ma['datasets']:
        seeds = sorted(int(x) for x in A.loc[A['dataset'] == ds, 'seed'].unique())
        items = ma['items'][ds]
        for pol in ma['policies']:
            for model in bd.MODELS:
                for (na, ma_), (nb, mb_) in itertools.combinations(items, 2):
                    va = [series(ix, ds, '{}/{}'.format(m[0], pol), model, 'S2', seeds) for ix in (ia, ib) for m in (ma_, mb_)]
                    if None in va:
                        continue
                    for mode in MODES:
                        x, y = pair_verdict(va[0], va[1], mode), pair_verdict(va[2], va[3], mode)
                        if (x or {}).get('verdict') != (y or {}).get('verdict'):
                            out.append('{} {} {} {} vs {} {}: {} -> {}'.format(ds, pol, model, na, nb, mode,
                                                                              (x or {}).get('verdict'), (y or {}).get('verdict')))
    return out


# ---------------------------------------------------------------- main
def selftest():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests', 'test_blockd.py')
    spec = importlib.util.spec_from_file_location('test_blockd', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_all('analysis')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ['--selftest']:
        return selftest()
    ap = argparse.ArgumentParser(description='Block D analysis (plan v2.1 §8).')
    ap.add_argument('runs', nargs='*')
    ap.add_argument('--compare', nargs=2, metavar=('RUN_A', 'RUN_B'))
    ap.add_argument('--out')
    ap.add_argument('--flags_dir')
    ap.add_argument('--data_root')
    args = ap.parse_args(argv)
    try:
        if args.compare:
            return compare(*args.compare)[0]
        if not args.runs:
            ap.error('give at least one RUN or --compare RUN_A RUN_B')
        if args.out:
            bd.resolve_out(args.out)
        code = analyse(args.runs, args.out, args.flags_dir, args.data_root)
        print('DONE analysis')
        return code
    except (Refused, bd.Abort, SystemExit) as e:
        msg = e.msg if isinstance(e, bd.Abort) else str(e)
        print('FAIL analysis {}'.format(msg))
        return 1
    except Exception as e:                                       # noqa: BLE001  R6: traceback on stderr, FAIL last on stdout
        traceback.print_exc()
        sys.stderr.flush()
        print('FAIL analysis unexpected {!r}'.format(e), flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
