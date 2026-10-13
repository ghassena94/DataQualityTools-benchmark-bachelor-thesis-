#!/usr/bin/env python3
####################################################
# Renders an HTML report of the detection results for one or more datasets,
# together with the per-denial-constraint ablation that says how much of
# HoloClean's score any single constraint is carrying.
#
# Read-only: reads results/detection_results.csv, dirty.csv and actual_errors.csv
# and writes a single HTML file. Print it to PDF with headless Chrome.
#
# It takes the LATEST row per detector of detection_results.csv. After a Raha
# batch of ten iterations that is iteration 10, not run 1; the thesis tables
# use run 1 from results/runs_log.csv.
#
#   docker compose run --rm rein python3 scripts/build_detection_report.py \
#       --dataset_name nasa bike --out_dir reports
####################################################

import argparse
import collections
import datetime
import html
import os

import pandas as pd

from rein.auxiliaries.dataset_metrics import compute_dataset_metrics
from rein.auxiliaries.datasets_dictionary import datasets_dictionary
from scripts.dc_ablation import load_frames, parse_dcs, score, violating_cells

# detectors in the order the report lists them, with the display name
DETECTOR_ORDER = [
    ('greatExpectations:dirty_profiled', 'GreatExpectations (dirty profiled)'),
    ('greatExpectations:clean_profiled', 'GreatExpectations (clean profiled)'),
    ('greatExpectations:hand_written', 'GreatExpectations (hand written)'),
    ('holoclean', 'HoloClean'),
    ('raha', 'Raha'),
]

CSS = """
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
 font-size:11px;line-height:1.5;color:#1a1a1a;max-width:1000px;margin:0 auto;padding:28px 22px}
h1{font-size:19px;margin:0 0 4px}h2{font-size:15px;margin:26px 0 8px;
 border-bottom:1px solid #d5d5d5;padding-bottom:4px}
h3{font-size:12.5px;margin:16px 0 6px}
p{margin:7px 0}
table{border-collapse:collapse;margin:8px 0 12px;font-size:10px}
th,td{border:1px solid #cfcfcf;padding:3px 7px;text-align:right;white-space:nowrap}
th{background:#f2f2f2;font-weight:600;text-align:right}
td.l,th.l{text-align:left}
code,.m{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9.5px}
.note{border-left:3px solid #b9b9b9;background:#fafafa;padding:7px 11px;margin:10px 0}
.win{background:#e7f5e9}.lose{background:#fdecec}.flat{background:#fdf6e3}
.small{font-size:9.5px;color:#666}
.sub{color:#555;margin:0 0 14px}
"""


def esc(value):
    return html.escape(str(value))


def fmt(value, digits=4):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "&mdash;"
    if isinstance(value, float):
        return "{:.{d}f}".format(value, d=digits)
    return esc(value)


def table(headers, rows, left_columns=(0,)):
    # headers and cells are written by this script, not taken from the data, so
    # they may carry entities like &rarr; and must not be escaped again
    out = ["<table><tr>"]
    for index, head in enumerate(headers):
        out.append('<th class="l">{}</th>'.format(head) if index in left_columns
                   else "<th>{}</th>".format(head))
    out.append("</tr>")
    for row in rows:
        out.append("<tr>")
        for index, cell in enumerate(row):
            klass = []
            if index in left_columns:
                klass.append("l")
            if isinstance(cell, tuple):
                cell, extra = cell
                klass.append(extra)
            attribute = ' class="{}"'.format(" ".join(klass)) if klass else ""
            out.append("<td{}>{}</td>".format(attribute, cell))
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)


def latest_results(dataset):
    """The most recent row per detector from results/detection_results.csv."""
    path = os.path.join(datasets_dictionary[dataset]["dataset_path"],
                        "results", "detection_results.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    frame = pd.read_csv(path)
    frame = frame[frame['detector'].notna()]
    frame['time'] = pd.to_datetime(frame['time'], errors='coerce')
    frame = frame.sort_values('time')
    return frame.groupby('detector', as_index=False).last()


def ablation(dataset):
    """Per-DC leave-one-out, plus the coverage and baseline context."""
    dirty, truth = load_frames(dataset)
    dcs = parse_dcs(os.path.join(datasets_dictionary[dataset]["dataset_path"],
                                 "constraints", "_all_constraints.txt"))
    n_rows, n_columns = dirty.shape
    n_cells = n_rows * n_columns
    error_rate = len(truth) / n_cells
    dirty_rows = {row for (row, _) in truth}
    error_columns = {column for (_, column) in truth}
    out = {'dataset': dataset, 'n_rows': n_rows, 'n_columns': n_columns,
           'n_cells': n_cells, 'n_errors': len(truth), 'error_rate': error_rate,
           'cell_baseline': 2 * error_rate / (1 + error_rate),
           'd_err': len(error_columns),
           'dirty_row_fraction': len(dirty_rows) / n_rows if n_rows else 0.0,
           'error_column_names': sorted(dirty.columns[c] for c in error_columns),
           'n_dcs': len(dcs), 'rows': [], 'full': None, 'coverage': 0.0,
           'blanket': None, 'touched': [], 'reuse': 0.0, 'reuse_max': 0}
    if not dcs:
        return out

    # How often a column recurs across the constraint set. This is what decides
    # whether a leave-one-out ablation can say anything: at ~1 a constraint owns
    # its columns outright and removing it removes them, so the gap it leaves is
    # interpretable. Well above 1, the same columns are named by several
    # constraints, and removing any one of them changes almost nothing.
    appearances = collections.Counter()
    for dc in dcs:
        for column in dc['eq'] + [dc['iq']]:
            appearances[column] += 1
    out['reuse'] = sum(appearances.values()) / len(appearances)
    out['reuse_max'] = max(appearances.values())

    cells = [violating_cells(dirty, dc) for dc in dcs]
    everything = set().union(*cells)
    out['full'] = score(everything, truth)
    out['coverage'] = len(everything) / n_cells

    touched = sorted({column for (_, column) in everything})
    out['touched'] = [dirty.columns[column] for column in touched]
    out['blanket'] = score({(row, column) for column in touched
                            for row in range(n_rows)}, truth)

    for index, (dc, own) in enumerate(zip(dcs, cells), 1):
        others = set().union(*[c for j, c in enumerate(cells) if j != index - 1]) \
            if len(cells) > 1 else set()
        out['rows'].append({
            'k': index,
            # smartfactory's constraints name up to eleven columns, which pushes
            # the table past the printable width. Keep the first few and say how
            # many more there are; the full text is in _all_constraints.txt.
            'label': "{} &rarr; {}".format(
                ", ".join(dc['eq'][:3]) + ("" if len(dc['eq']) <= 3
                                           else " + {} more".format(len(dc['eq']) - 3)),
                dc['iq']),
            'rows_flagged': len(own) // (len(dc['eq']) + 1),
            'row_share': (len(own) // (len(dc['eq']) + 1)) / n_rows,
            'cells': len(own),
            'alone': score(own, truth),
            'without': score(others, truth),
            'delta': out['full'][2] - score(others, truth)[2],
            'unique_tp': len((own - others) & truth),
        })
    return out


def section_for(dataset):
    parts = []
    data = ablation(dataset)
    results = latest_results(dataset)

    parts.append("<h2>{}</h2>".format(esc(dataset)))

    metrics = compute_dataset_metrics(
        {(0, 0): None}, data['n_rows'], data['n_columns'], data['error_rate'])
    parts.append(table(
        ["metric", "value"],
        [["rows (N)", "{:,}".format(data['n_rows'])],
         ["dimension (d)", data['n_columns']],
         ["cells", "{:,}".format(data['n_cells'])],
         ["injected errors", "{:,}".format(data['n_errors'])],
         ["columns with errors (d_err)", "{} of {}".format(data['d_err'], data['n_columns'])],
         ["dirty row fraction", "{:.4f}".format(data['dirty_row_fraction'])],
         ["cell error rate (eps)", fmt(data['error_rate'])],
         ["cell_baseline = 2eps/(1+eps)", fmt(data['cell_baseline'])],
         ["Rousseeuw prediction", fmt(metrics['rousseeuw_prediction'])],
         ["denial constraints", data['n_dcs']]]))
    if data['d_err'] <= 3:
        parts.append('<div class="note">Every injected error in this copy sits in '
                     '{}. A detector that flags any other column is spending its '
                     'precision on cells that cannot be wrong.</div>'.format(
                         ", ".join("<code>{}</code>".format(esc(name))
                                   for name in data['error_column_names'])))

    # ---- detector results
    parts.append("<h3>Detection results</h3>")
    if results.empty:
        parts.append("<p>No results recorded.</p>")
    else:
        indexed = results.set_index('detector')
        rows = []
        for key, label in DETECTOR_ORDER:
            if key not in indexed.index:
                continue
            record = indexed.loc[key]
            f1 = record.get('f1')
            beat = f1 - data['cell_baseline'] if pd.notna(f1) else None
            klass = "win" if (beat or 0) > 0.02 else ("lose" if (beat or 0) <= 0 else "flat")
            rows.append([
                label, fmt(record.get('precision')), fmt(record.get('recall')),
                fmt(f1), (fmt(beat, 4) if beat is not None else "&mdash;", klass),
                "{:,}".format(int(record['#detections'])) if pd.notna(record.get('#detections')) else "&mdash;",
                fmt(record.get('detection_runtime'), 2),
            ])
        parts.append(table(
            ["detector", "precision", "recall", "F1", "F1 &minus; baseline",
             "#detections", "runtime (s)"], rows))
        parts.append('<p class="small">F1 &minus; baseline compares each detector '
                     'against the trivial detector that flags every cell '
                     '(cell_baseline = {}). Green beats it by more than 0.02, '
                     'red is at or below it.</p>'.format(fmt(data['cell_baseline'])))

    # ---- DC ablation
    parts.append("<h3>HoloClean &mdash; per-constraint ablation</h3>")
    if not data['n_dcs']:
        parts.append('<div class="note">No denial constraints for this dataset. '
                     'HoloClean ran with an empty constraint set, so its 0.0000 is '
                     'the absence of a constraint set rather than a measurement of '
                     'the tool. Every FD the FDX profiler found was dropped because '
                     'its left-hand side contained a (near-)unique column, whose '
                     '<code>EQ()</code> can never match two distinct rows.</div>')
        return "".join(parts)

    rows = []
    for record in sorted(data['rows'], key=lambda r: -r['delta']):
        rows.append([
            record['k'], record['label'],
            "{:,}".format(record['cells']),
            "{:.1%}".format(record['row_share']),
            fmt(record['alone'][2]), fmt(record['without'][2]),
            ("{:+.4f}".format(record['delta']),
             "win" if record['delta'] > 0.05 else ""),
            "{:,}".format(record['unique_tp']),
        ])
    parts.append(table(
        ["k", "constraint (EQ &rarr; IQ)", "cells", "% rows", "F1 alone",
         "F1 without", "&Delta;F1", "unique TP"], rows, left_columns=(1,)))

    precision, recall, f1 = data['full'][0], data['full'][1], data['full'][2]
    parts.append(
        "<p>All {} constraints together: P={}, R={}, <strong>F1={}</strong>, "
        "flagging <strong>{:.1%}</strong> of the table. The trivial flag-everything "
        "detector scores {} ({:+.4f}).</p>".format(
            data['n_dcs'], fmt(precision), fmt(recall), fmt(f1), data['coverage'],
            fmt(data['cell_baseline']), f1 - data['cell_baseline']))

    if data['blanket']:
        parts.append(
            "<p>HoloClean touches {} of the {} columns. Flagging <em>every</em> cell "
            "of just those columns &mdash; ignoring the constraints entirely and "
            "keeping only the column selection &mdash; scores F1={}, against "
            "HoloClean's {} ({:+.4f} for the row-level filtering the constraints "
            "actually perform).</p>".format(
                len(data['touched']), data['n_columns'], fmt(data['blanket'][2]),
                fmt(f1), f1 - data['blanket'][2]))
    return "".join(parts)


def build(datasets, out_dir):
    body = ["<h1>REIN benchmark &mdash; detection results and denial-constraint "
            "attribution</h1>",
            '<p class="sub">{} &middot; generated {}</p>'.format(
                ", ".join(datasets),
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))]

    # cross-dataset summary of the DC question
    summary = [ablation(name) for name in datasets]
    body.append("<h2>Does the beers constraint story transfer?</h2>")
    rows = []
    for data in summary:
        if not data['n_dcs']:
            rows.append([data['dataset'], 0, "&mdash;", "&mdash;", "&mdash;",
                         "&mdash;", fmt(data['cell_baseline']), ("&mdash;", "lose")])
            continue
        top = max(record['delta'] for record in data['rows'])
        f1 = data['full'][2]
        beat = f1 - data['cell_baseline']
        rows.append([
            data['dataset'], data['n_dcs'],
            "{:.2f} (max {})".format(data['reuse'], data['reuse_max']),
            "{:.1%}".format(data['coverage']),
            fmt(f1), ("{:+.4f}".format(top), "win" if top > 0.05 else ""),
            fmt(data['cell_baseline']),
            ("{:+.4f}".format(beat), "win" if beat > 0.02 else
             ("lose" if beat <= 0.001 else "flat")),
        ])
    body.append(table(
        ["dataset", "#DCs", "mean DCs per column", "table flagged", "HoloClean F1",
         "largest single &Delta;F1", "cell_baseline", "F1 &minus; baseline"], rows))
    body.append(
        '<p class="small">mean DCs per column is what decides whether a '
        'leave-one-out ablation can say anything. Near 1, a constraint owns its '
        'columns outright, so removing it removes them and the gap it leaves is '
        'interpretable &mdash; that is the beers case. Well above 1, the same '
        'columns are named by several constraints, removing any one changes '
        'almost nothing, and the ablation is blind by construction.</p>')

    for name in datasets:
        body.append(section_for(name))

    document = ("<!doctype html><meta charset='utf-8'><title>REIN detection "
                "results</title><style>{}</style>{}".format(CSS, "".join(body)))
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "detection_results_{}.html".format("_".join(datasets)))
    with open(path, "w") as handle:
        handle.write(document)
    print("wrote {}".format(path))
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_name', nargs='+', required=True)
    parser.add_argument('--out_dir', default='reports')
    parser.add_argument('--detectors', nargs='+', default=None,
                        help='restrict the report to these detector keys, e.g. '
                             'holoclean raha greatExpectations')
    args = parser.parse_args()
    if args.detectors:
        keep = tuple(args.detectors)
        DETECTOR_ORDER[:] = [(key, label) for key, label in DETECTOR_ORDER
                             if key.split(':')[0] in keep or key.split('_')[0] in keep]
    for name in args.dataset_name:
        if name not in datasets_dictionary:
            raise ValueError("Dataset {} is not known.".format(name))
    build(args.dataset_name, args.out_dir)
