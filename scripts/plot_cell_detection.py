"""Draw Figure 2-style cell-level detection panels from runs_log.csv.

Usage:
    python plot_cell_detection.py --log results/runs_log.csv --out figures/cell_detection

Writes one PDF per dataset (panel_<dataset>.pdf), to be combined with
\\subfigure in LaTeX. Uses the most recent run per (dataset, tool).
Panels switch to a broken y-axis automatically when one bar dwarfs the rest.

Needs: pip install "matplotlib<3.8" pandas   (3.7 is the last for Python 3.8)
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

GREEN, RED, EDGE = "#a3c776", "#e08c80", "#555555"
# One naming scheme for the three GE suites across all panels
LABELS = {
    "GreatExpectations (dirty profiled)": "GE\ndirty-profiled",
    "GreatExpectations (clean profiled)": "GE\nclean-profiled",
    "GreatExpectations (hand written)": "GE\nhand-written",
    "HoloClean (DC2+DC3)": "HoloClean\nDC2+DC3",
    "HoloClean": "HoloClean",
    "Raha": "RAHA",
}
# per-dataset label overrides: beers also shows HoloClean without DC1, and its
# Raha bar is the first of the ten runs of 22 Sep
LABEL_OVERRIDES = {
    ("beers", "HoloClean"): "HoloClean\nall 3 DCs",
    ("beers", "Raha"): "RAHA\n(run 1)",
}
BREAK_RATIO = 20  # break the axis if tallest bar > 20x the actual error count


def draw(ax, df, errors, labels_on=True):
    x = range(len(df))
    ax.bar(x, df.TP, color=GREEN, edgecolor=EDGE, label="True Positives")
    ax.bar(x, df.FP, bottom=df.TP, color=RED, edgecolor=EDGE, label="False Positives")
    ax.axhline(errors, color="red", ls="--", lw=1, label="Actual Errors")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    return x

TP_COLOR, FP_COLOR = "#2e6b12", "#a33"   # dark green / dark red (readable on the bars)

def annotate(ax, x, df, ymax):
    fits = 0.06 * ymax                     # min segment height to hold a label
    for i, (tp, fp) in zip(x, zip(df.TP, df.FP)):
        if tp + fp == 0:
            ax.text(i, ymax * 0.02, "0 detections", rotation=90, ha="center",
                    va="bottom", fontsize=6, color="grey")
            continue
        above = []                          # labels that don't fit inside
        if tp >= fits:                      # TP inside the green box
            ax.text(i, tp / 2, f"TP {tp:,}", ha="center", va="center",
                    fontsize=5.5, color=TP_COLOR)
        elif tp > 0:
            above.append((f"TP {tp:,}", TP_COLOR))
        if tp + fp <= ymax:                 # skip FP here if bar is cut (top axis shows it)
            if fp >= fits:
                ax.text(i, tp + fp / 2, f"FP {fp:,}", ha="center", va="center",
                        fontsize=5.5, color=FP_COLOR)
            elif fp > 0:
                above.append((f"FP {fp:,}", FP_COLOR))
        y = min(tp + fp, ymax) + ymax * 0.01
        for text, color in above:           # stacked, so TP and FP never overlap
            ax.text(i, y, text, ha="center", va="bottom", fontsize=5.5, color=color)
            y += ymax * 0.045


def plot_dataset(ds, df, out_dir):
    errors = int(df.injected_errors.iloc[0])
    totals = df.TP + df.FP
    names = [LABEL_OVERRIDES.get((ds, t), LABELS.get(t, t)) for t in df.tool]
    tallest = totals.max()
    big = [t for t in totals if t > BREAK_RATIO * errors]
    rest = max([t for t in totals if t <= BREAK_RATIO * errors] + [errors])

    if big:                                      # broken y-axis
        fig, (top, bot) = plt.subplots(2, 1, sharex=True, figsize=(max(4, 0.82 * len(df)), 3.2),
                                       gridspec_kw={"height_ratios": [1, 3]})
        for ax in (top, bot):
            x = draw(ax, df, errors)
        low_max = max(rest, errors) * 1.35
        bot.set_ylim(0, low_max)
        top.set_ylim(min(big) * 0.9 if len(big) > 1 else tallest * 0.985,
                     tallest * 1.02)
        top.spines["bottom"].set_visible(False)
        bot.spines["top"].set_visible(False)
        top.tick_params(bottom=False)
        d = 0.012  # diagonal cut marks
        kw = dict(transform=top.transAxes, color="k", clip_on=False, lw=0.8)
        top.plot((-d, d), (-d * 3, d * 3), **kw)
        top.plot((1 - d, 1 + d), (-d * 3, d * 3), **kw)
        kw["transform"] = bot.transAxes
        bot.plot((-d, d), (1 - d, 1 + d), **kw)
        bot.plot((1 - d, 1 + d), (1 - d, 1 + d), **kw)
        annotate(bot, x, df, low_max)
        for i, (tp, fp) in zip(x, zip(df.TP, df.FP)):
            if tp + fp > low_max:
                top.text(i, tp + fp, f"FP {fp:,}", ha="center", va="bottom",
                         fontsize=6, color="#a33")
        top.legend(fontsize=6, loc="upper left")
        bot.set_ylabel("Detected Cells", fontsize=7)
        ax_main = bot
    else:
        fig, ax_main = plt.subplots(figsize=(max(4, 0.82 * len(df)), 3.2))
        x = draw(ax_main, df, errors)
        ymax = max(tallest, errors) * 1.15
        ax_main.set_ylim(0, ymax)
        annotate(ax_main, x, df, ymax)
        ax_main.legend(fontsize=6, loc="upper left")
        ax_main.set_ylabel("Detected Cells", fontsize=7)

    ax_main.set_xticks(list(x))
    ax_main.set_xticklabels(names, fontsize=6)
    for ax in fig.axes:
        ax.tick_params(axis="y", labelsize=6)
        ax.ticklabel_format(axis="y", style="plain")
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    fig.tight_layout()
    path = out_dir / f"panel_{ds}.pdf"
    fig.savefig(path)
    fig.savefig(path.with_suffix(".png"), dpi=150)  # quick preview
    plt.close(fig)
    print("wrote", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="results/runs_log.csv")
    ap.add_argument("--out", default="figures/cell_detection")
    args = ap.parse_args()

    df = pd.read_csv(args.log)
    # latest run per (dataset, tool)
    df = df.sort_values("run_id").groupby(["dataset", "tool"], sort=False).tail(1)
    order = list(LABELS)
    df["order"] = df.tool.map(lambda t: order.index(t) if t in order else 99)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for ds, g in df.groupby("dataset", sort=False):
        plot_dataset(ds, g.sort_values("order").reset_index(drop=True), out_dir)


if __name__ == "__main__":
    main()