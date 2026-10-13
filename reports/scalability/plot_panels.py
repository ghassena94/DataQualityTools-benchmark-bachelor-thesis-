"""One standalone figure per panel of the scalability figure (thesis section 5.2.6).

Reads reports/scalability/results.csv and writes, for every metric (FG1, cold
runtime, peak memory) and every experiment (har rows, adult rows, mercedes
columns), its own PDF and PNG to reports/scalability/panels/:

    <metric>_<dataset>_<axis>.pdf / .png     e.g. runtime_har_rows.pdf

Only status-ok points are drawn. FG1 keeps three cases apart: a real value is
drawn on the axis; an undefined FG1 (no true positive) and a negative FG1 (F1 below
the cell error rate) are drawn in two bands below the axis, one row per
configuration, so no series hides another. A failed fraction (OOM) has no
runtime, so the FG1 and runtime panels mark it with a vertical dotted line at
the killed fraction; the memory panel marks it with an x on the memory limit.
No time limit per run (REIN sets none; the 2 h cap of 26-27 Sep was dropped on
29 Sep). plot.py imports draw_fg1 and fg1_slots from here for the combined figure.

Run inside the container (matplotlib is not on the host):
    docker compose run --rm -T rein python3 reports/scalability/plot_panels.py
    docker compose run --rm -T rein python3 reports/scalability/plot_panels.py --metric runtime --dataset har
"""
import argparse, csv, collections, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms

HERE = 'reports/scalability'
OUT = os.path.join(HERE, 'panels')
CONF = [  # key -> (label, colour, marker)   same order and palette as plot.py
    (('greatExpectations', 'dirty_profiled'), 'GE dirty-profiled', '#2a78d6', 'o'),
    (('greatExpectations', 'clean_profiled'), 'GE clean-profiled', '#eb6834', 's'),
    (('greatExpectations', 'hand_written'),   'GE hand-written',   '#1baf7a', '^'),
    (('holoclean', ''),                       'HoloClean',         '#eda100', 'D'),
    (('raha', ''),                            'Raha',              '#e87ba4', 'v'),
]
PANELS = {  # dataset -> (axis, title, x label)
    'har':      ('rows', 'har, rows (70 000 × 5)',            'fraction of the rows (%)'),
    'adult':    ('rows', 'adult, rows (45 222 × 15)',         'fraction of the rows (%)'),
    'mercedes': ('cols', 'mercedes, columns (4 209 × 378)',   'fraction of the columns (%)'),
}
METRICS = ('fg1', 'runtime', 'memory')
LIMIT_GB = 31.29 * 1.073741824  # Docker VM memory, GiB -> GB
FLOOR_GB = 0.65                 # interpreter + libraries, same for every configuration
GREY, TEXT, BAND = '#9a9994', '#52514e', '#f1f0ec'
BANDS = (('neg', -0.15, '< 0'), ('undef', -0.38, 'undefined'))  # FG1 bands below the axis: key, centre, label
BAND_STEP = 0.045               # vertical distance between two configurations' rows inside a band


def load():
    by = collections.defaultdict(dict)
    with open(os.path.join(HERE, 'results.csv')) as f:
        for r in csv.DictReader(f):
            by[(r['dataset'], r['axis'], r['detector'], r['tier'])][float(r['fraction'])] = r
    return by


def fg1_kind(r):
    """('val', v) for a real FG1 >= 0, ('neg', v) below 0, ('undef', None) when there is no true positive."""
    try:
        v = float(r['cell_FG1'])
    except ValueError:
        return 'undef', None
    if v != v:
        return 'undef', None
    return ('neg', v) if v < 0 else ('val', v)


def fg1_slots(by):
    """y of each configuration's row inside each band, the same on every panel. Only configurations
    that land in a band somewhere get a row there; the first configuration is the top row."""
    slots = {}
    for band, centre, _ in BANDS:
        keys = [key for key, *_ in CONF
                if any(r['status'] == 'ok' and fg1_kind(r)[0] == band
                       for k, d in by.items() if k[2:] == key for r in d.values())]
        for i, key in enumerate(keys):
            slots[(band, key)] = centre - (i - (len(keys) - 1) / 2) * BAND_STEP
    return slots


def draw_fg1(ax, by, ds, axis, slots):
    """FG1 panel: real values on the axis, undefined and negative FG1 in their bands, the 0.5
    baseline, and a dotted line at an OOM-killed fraction."""
    nan = float('nan')
    for key, label, colour, marker in CONF:
        d = by[(ds, axis) + key]
        ok = [f for f in sorted(d) if d[f]['status'] == 'ok']
        kinds = [fg1_kind(d[f]) for f in ok]
        x = [f * 100 for f in ok]
        kw = dict(color=colour, marker=marker, mfc='white', mew=1.4)
        # the labelled line is always drawn (possibly all NaN) so the legend lists every configuration
        ax.plot(x, [v if k == 'val' else nan for k, v in kinds], ms=5, lw=1.6, label=label, **kw)
        for band, _, _ in BANDS:
            ys = [slots[(band, key)] if k == band else nan for k, _ in kinds]
            if any(y == y for y in ys):
                ax.plot(x, ys, ms=4, lw=1.0, label='_nolegend_', **kw)
        for f in sorted(d):
            if d[f]['status'] in ('oom_killed', 'timeout'):
                tag = 'OOM' if d[f]['status'] == 'oom_killed' else 'timeout'
                ax.axvline(f * 100, color=colour, ls=':', lw=1.4)
                ax.annotate(tag, (f * 100, 0.42), textcoords='offset points', xytext=(-4, 0),
                            ha='right', va='center', fontsize=8, color=TEXT)
    label_at = mtransforms.blended_transform_factory(ax.transAxes, ax.transData)
    for band, centre, name in BANDS:
        ys = [y for (b, _), y in slots.items() if b == band] or [centre]
        ax.axhspan(min(ys) - 0.6 * BAND_STEP - 0.01, max(ys) + 0.6 * BAND_STEP + 0.01,
                   color=BAND, lw=0, zorder=0)
        ax.text(-0.015, centre, name, transform=label_at, ha='right', va='center', fontsize=8.5, color=TEXT)
    ax.axhline(0.5, color=GREY, ls='--', lw=1)
    lowest = min(list(slots.values()) + [BANDS[-1][1]])
    ax.set_ylim(lowest - 0.6 * BAND_STEP - 0.03, 1.05)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])


VALUE = {
    'runtime': lambda r: max(float(r['runtime_s']), 1e-2),
    'memory':  lambda r: int(r['peak_mem_bytes']) / 1e9,
}


def panel(by, slots, metric, ds):
    axis, title, xlabel = PANELS[ds]
    fig, ax = plt.subplots(figsize=(5, 4.3 if metric == 'fg1' else 4.1))
    if metric == 'fg1':
        draw_fg1(ax, by, ds, axis, slots)
        ax.set_ylabel('cell $FG_1$ (baseline 0.5 dashed)', fontsize=9)
    else:
        for key, label, colour, marker in CONF:
            d = by[(ds, axis) + key]
            fr = sorted(d)
            ok = [f for f in fr if d[f]['status'] == 'ok']
            if ok:
                ax.plot([f * 100 for f in ok], [VALUE[metric](d[f]) for f in ok], color=colour, marker=marker,
                        ms=5, lw=1.6, label=label, mfc='white', mew=1.4)
            for f in fr:
                if d[f]['status'] not in ('oom_killed', 'timeout'):
                    continue
                tag, x = ('OOM' if d[f]['status'] == 'oom_killed' else 'timeout'), f * 100
                if metric == 'runtime':  # a killed run has no runtime: mark where the curve stops
                    ax.axvline(x, color=colour, ls=':', lw=1.4)
                    ax.annotate(tag, (x, 0), xycoords=('data', 'axes fraction'), textcoords='offset points',
                                xytext=(-4, 4), ha='right', fontsize=8, color=TEXT)
                else:
                    ax.plot([x], [LIMIT_GB], marker='x', color=colour, ms=9, mew=2, ls='none')
                    ax.annotate(tag, (x, LIMIT_GB), textcoords='offset points', xytext=(0, -16),
                                ha='center', fontsize=8, color=TEXT)
        if metric == 'runtime':
            ax.set_yscale('log'); ax.set_ylim(5e-3, 2e4)
            ax.set_ylabel('cold runtime (s, log)', fontsize=9)
        else:
            ax.axhline(LIMIT_GB, color=GREY, ls='--', lw=1)
            ax.axhline(FLOOR_GB, color=GREY, ls=':', lw=1)
            ax.text(2, LIMIT_GB - 2.4, '33.6 GB memory limit', fontsize=8, color=TEXT)
            ax.text(35, FLOOR_GB + 1.2, 'interpreter floor', fontsize=8, color=TEXT)
            ax.set_ylim(0, 36)
            ax.set_ylabel('peak container memory (GB)', fontsize=9)

    ax.set_title(title, fontsize=10, loc='left')
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_xlim(0, 104)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.grid(True, color='#e8e7e3', lw=0.8); ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8.5)
    ax.legend(fontsize=7.5, frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3)
    fig.tight_layout()
    base = os.path.join(OUT, f'{metric}_{ds}_{axis}')
    fig.savefig(base + '.pdf')
    fig.savefig(base + '.png', dpi=150)
    plt.close(fig)
    return base


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--metric', choices=METRICS, nargs='*', default=list(METRICS))
    p.add_argument('--dataset', choices=list(PANELS), nargs='*', default=list(PANELS))
    a = p.parse_args()
    os.makedirs(OUT, exist_ok=True)
    by = load()
    slots = fg1_slots(by)
    for m in a.metric:
        for ds in a.dataset:
            print('saved', panel(by, slots, m, ds) + '.{pdf,png}')


if __name__ == '__main__':
    main()
