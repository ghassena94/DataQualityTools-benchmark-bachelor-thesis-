"""Figures for the robustness subsection (REIN section 6.2.1, Fig. 3 style): cell F1 and FG1 of the
five configurations on nasa's generated dirty versions, one row per variant of the generator:
  asis      = REIN's generator as it is (injected outliers carry a 12-21-digit fingerprint)
  cleanstyle = main protocol (2 Oct v2): injected values written exactly in the clean number style
Knob 1 (--knob 1): x = measured error rate, outliers (degree --degree) + blanks.
Knob 2 (--knob 2): x = outlier degree, outliers only at a fixed asked rate of 30 %.
Reads reports/robustness/results.csv (rows with status ok).
Run from the repo root, e.g.
  python3 reports/robustness/plot.py --degree 4 --variants cleanstyle  (knob 1 main figure)
  python3 reports/robustness/plot.py --knob 2 --variants cleanstyle      (knob 2 main figure)
  python3 reports/robustness/plot.py --knob 2 --variants asis,cleanstyle"""
import argparse, csv, collections, glob, re, statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument('--knob', type=int, choices=[1, 2], default=1)
ap.add_argument('--degree', type=float, default=3, help='knob 1 only')
ap.add_argument('--variants', default='cleanstyle')
ap.add_argument('--raha', choices=['mean', 'median'], default='mean',
                help='mean: Raha = average of its 6 draws, no bars (REIN plots average F1); '
                     'median: median with a min-max bar')
args = ap.parse_args()
VARIANTS = args.variants.split(',')
BASE = 'error_rate' if args.knob == 1 else 'outlier_degree'
SUFFIX = {'asis': '', 'cleanstyle': '_cleanstyle'}
TITLE = {'asis': "REIN's generator unchanged",
         'cleanstyle': "injected values rewritten in the column's number format"}

rows = [r for r in csv.DictReader(open('reports/robustness/results.csv')) if r['status'] == 'ok'
        and r['mode'] in [BASE + SUFFIX[v] for v in VARIANTS]
        and (args.knob == 2 or float(r['outlier_degree']) == args.degree)]
CONF = [  # same order, colours and markers as reports/scalability/plot.py
    (('greatExpectations', 'dirty_profiled'), 'GE dirty-profiled', '#2a78d6', 'o'),
    (('greatExpectations', 'clean_profiled'), 'GE clean-profiled', '#eb6834', 's'),
    (('greatExpectations', 'hand_written'),   'GE hand-written',   '#1baf7a', '^'),
    (('holoclean', ''),                       'HoloClean',         '#eda100', 'D'),
    (('raha', ''),                            'Raha',              '#e87ba4', 'v'),
]
PANELS = [('f1', 'cell $F_1$'), ('cell_FG1', 'cell $FG_1$')]   # dashed line at 0.5 = always-positive baseline (said in the caption)

# Raha seed checks (seeds 1-5 on the same dirty file, raha_seed_check*.txt): where they exist,
# Raha is drawn as the average of the 6 draws (campaign run + 5 seeds), as REIN plots average F1
# (--raha median: median with a min-max bar)
SEEDS = {}
for f in glob.glob('reports/robustness/raha_seed_check*.txt'):
    for line in open(f):
        m = re.match(r'(nasa\S+)\s+(.*)', line)
        if m:
            SEEDS[m.group(1)] = [float(x) for x in re.findall(r'F1=([0-9.]+)', m.group(2))]


def fg1_of(f1, pi):
    return max((f1 - pi) / ((1 - pi) * f1), 0.0) if f1 > 0 else 0.0


def xval(r):
    return float(r['measured_error_rate']) * 100 if args.knob == 1 else float(r['level'])


by = collections.defaultdict(dict)
for r in rows:
    by[(r['mode'], r['detector'], r['tier'])][xval(r)] = r


def val(r, key):
    try:
        v = float(r[key])
    except ValueError:
        return 0.0
    if v != v:          # NaN: undefined (no detections)
        return 0.0
    return max(v, 0.0) if key == 'cell_FG1' else v   # negative / undefined FG1 -> 0


n = len(VARIANTS)
def raha_draws(r, key):
    f1s = [float(r['f1'])] + SEEDS.get(r['scratch'], [])
    if key == 'f1':
        return f1s
    pi = float(r['measured_error_rate'])
    return [fg1_of(x, pi) for x in f1s]


fig, axes = plt.subplots(n, 2, figsize=(9, 0.6 + 3.0 * n), sharex=True, squeeze=False)
for i, v in enumerate(VARIANTS):
    for j, (key, ylabel) in enumerate(PANELS):
        ax = axes[i][j]
        for conf, label, colour, marker in CONF:
            d = by[(BASE + SUFFIX[v],) + conf]
            xs = sorted(d)
            if xs and conf == ('raha', '') and all(d[x]['scratch'] in SEEDS for x in xs):
                draws = [raha_draws(d[x], key) for x in xs]
                if args.raha == 'mean':
                    ax.plot(xs, [statistics.mean(v) for v in draws], color=colour, marker=marker, ms=5,
                            lw=1.6, mfc='white', mew=1.4, label='Raha (average of 6 runs)')
                else:
                    med = [statistics.median(v) for v in draws]
                    lo = [m - min(v) for m, v in zip(med, draws)]
                    hi = [max(v) - m for m, v in zip(med, draws)]
                    ax.errorbar(xs, med, yerr=[lo, hi], color=colour, marker=marker, ms=5, lw=1.6,
                                mfc='white', mew=1.4, elinewidth=1.0, capsize=2.5,
                                label='Raha (median of 6 draws, bar = range)')
            elif xs:
                # dirty-profiled gets a bigger marker so it stays visible where it coincides with
                # clean-profiled (identical on every nasa robustness file)
                big = conf == ('greatExpectations', 'dirty_profiled')
                ax.plot(xs, [val(d[x], key) for x in xs], color=colour, marker=marker,
                        ms=9 if big else 5, lw=3.2 if big else 1.6, label=label, mfc='white', mew=1.4)
        if key == 'cell_FG1':
            ax.axhline(0.5, color='#9a9994', ls='--', lw=1)
        ax.set_ylim(-0.03, 1.05)
        ax.set_ylabel(ylabel, fontsize=9)
        if j == 0 and n > 1:   # row titles only when variants are stacked; a single-variant figure is described by its caption
            extra = ' (outlier degree {:g})'.format(args.degree) if args.knob == 1 else ' (requested rate 30 %)'
            ax.set_title(TITLE[v] + extra, fontsize=10, loc='left')
        ax.grid(True, color='#e8e7e3', lw=0.8); ax.set_axisbelow(True)
        for s_ in ('top', 'right'):
            ax.spines[s_].set_visible(False)
        ax.tick_params(labelsize=8.5)
for ax in axes[-1]:
    if args.knob == 1:
        ax.set_xlabel('measured error rate of the dirty version (%)', fontsize=9)
        ax.set_xticks([0, 5, 10, 15, 20, 25, 30])
    else:
        ax.set_xlabel('outlier degree k (noise spread k·σ of the column)', fontsize=9)
        ax.set_xticks(range(1, 11))
h, l = axes[0][0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=3, frameon=False, fontsize=9, bbox_to_anchor=(0.5, -0.005))
fig.tight_layout(rect=(0, 0.13 if n == 1 else 0.075, 1, 1))
if args.knob == 1:
    name = 'fig_robustness_error_rate' + ('' if args.degree == 3 else '_d{:g}'.format(args.degree))
    name += '_' + '_'.join(VARIANTS)
else:
    name = 'fig_robustness_outlier_degree_' + '_'.join(VARIANTS)
if args.raha == 'median':
    name += '_median'
fig.savefig('reports/robustness/{}.pdf'.format(name))
fig.savefig('reports/robustness/{}.png'.format(name), dpi=150)
print('wrote reports/robustness/{}.{{pdf,png}}'.format(name))
