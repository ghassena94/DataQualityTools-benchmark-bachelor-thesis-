"""Figure for thesis section 5.2.6: FG1, cold runtime and peak memory against the
row fraction (har, adult) and the column fraction (mercedes) for the five
configurations. Reads reports/scalability/results.csv. No time limit per run
(the 2 h cap of 26-27 Sep was dropped on 29 Sep); an OOM-killed fraction is a
dotted vertical line in the FG1 and runtime rows and an x at the memory limit.
The FG1 row comes from plot_panels.draw_fg1: undefined and negative FG1 sit in
two bands below the axis, one row per configuration."""
import csv, collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from plot_panels import draw_fg1, fg1_slots  # same FG1 drawing as the standalone panels

rows = list(csv.DictReader(open('reports/scalability/results.csv')))
CONF = [  # key -> (label, colour, marker)   fixed order, validated palette
    (('greatExpectations', 'dirty_profiled'), 'GE dirty-profiled', '#2a78d6', 'o'),
    (('greatExpectations', 'clean_profiled'),  'GE clean-profiled', '#eb6834', 's'),
    (('greatExpectations', 'hand_written'),  'GE hand-written',   '#1baf7a', '^'),
    (('holoclean', ''),                'HoloClean',         '#eda100', 'D'),
    (('raha', ''),                     'Raha',              '#e87ba4', 'v'),
]
PANELS = [('har', 'rows', 'har, rows (70\u202f000 \u00d7 5)'),
          ('adult', 'rows', 'adult, rows (45\u202f222 \u00d7 15)'),
          ('mercedes', 'cols', 'mercedes, columns (4\u202f209 \u00d7 378)')]
LIMIT_GB = 31.29 * 1.073741824  # Docker VM memory, GiB -> GB
FLOOR_GB = 0.65                 # interpreter + libraries, same for every configuration

by = collections.defaultdict(dict)
for r in rows:
    by[(r['dataset'], r['axis'], r['detector'], r['tier'])][float(r['fraction'])] = r

slots = fg1_slots(by)

fig, axes = plt.subplots(3, 3, figsize=(11, 9.2), sharex='col')
for c, (ds, axis, title) in enumerate(PANELS):
    ax_q, ax_t, ax_m = axes[0][c], axes[1][c], axes[2][c]
    draw_fg1(ax_q, by, ds, axis, slots)
    for key, label, colour, marker in CONF:
        d = by[(ds, axis) + key]
        fr = sorted(d)
        ok = [f for f in fr if d[f]['status'] == 'ok']
        x = [f * 100 for f in ok]
        kw = dict(color=colour, marker=marker, ms=5, lw=1.6, label=label, mfc='white', mew=1.4)
        if ok:
            ax_t.plot(x, [max(float(d[f]['runtime_s']), 1e-2) for f in ok], **kw)
            ax_m.plot(x, [int(d[f]['peak_mem_bytes']) / 1e9 for f in ok], **kw)
        fails = [f for f in fr if d[f]['status'] in ('oom_killed', 'timeout')]
        for f in fails:  # no runtime for a killed run: dotted line where the curve stops; x at the memory limit
            tag, x = ('OOM' if d[f]['status'] == 'oom_killed' else 'timeout'), f * 100
            ax_t.axvline(x, color=colour, ls=':', lw=1.4)
            ax_t.annotate(tag, (x, 0), xycoords=('data', 'axes fraction'), textcoords='offset points',
                          xytext=(-4, 4), ha='right', fontsize=8, color='#52514e')
            ax_m.plot([x], [LIMIT_GB], marker='x', color=colour, ms=9, mew=2, ls='none')
            ax_m.annotate(tag, (x, LIMIT_GB), textcoords='offset points', xytext=(0, -16),
                          ha='center', fontsize=8, color='#52514e')
    ax_q.set_title(title, fontsize=10, loc='left')
    ax_t.set_yscale('log'); ax_t.set_ylim(5e-3, 2e4)
    ax_m.axhline(LIMIT_GB, color='#9a9994', ls='--', lw=1)
    ax_m.axhline(FLOOR_GB, color='#9a9994', ls=':', lw=1)
    ax_m.set_ylim(0, 36)
    ax_m.set_xlabel('fraction of the table (%)')
    ax_m.set_xticks([0, 20, 40, 60, 80, 100])
    for ax in (ax_q, ax_t, ax_m):
        ax.grid(True, color='#e8e7e3', lw=0.8); ax.set_axisbelow(True)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        ax.tick_params(labelsize=8.5)
axes[0][0].set_ylabel('cell $FG_1$ (baseline 0.5 dashed)', fontsize=9)
axes[1][0].set_ylabel('cold runtime (s, log)', fontsize=9)
axes[2][0].set_ylabel('peak container memory (GB;\nlimit dashed, floor dotted)', fontsize=9)
axes[2][1].text(22, LIMIT_GB - 2.4, '33.6 GB memory limit', fontsize=8, color='#52514e')
axes[2][1].text(22, FLOOR_GB + 1.2, 'interpreter floor', fontsize=8, color='#52514e')
h, l = axes[0][0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=5, frameon=False, fontsize=9, bbox_to_anchor=(0.5, -0.005))
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig('reports/scalability/fig_scalability.pdf')
fig.savefig('reports/scalability/fig_scalability.png', dpi=150)
print('saved')
