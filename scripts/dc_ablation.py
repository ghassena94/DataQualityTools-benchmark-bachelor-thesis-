#!/usr/bin/env python3
####################################################
# Per-denial-constraint ablation for the HoloClean violation detector.
#
# HoloClean reports one F1 for a whole constraint set. On beers that number is
# carried by a single constraint: with all three the set scores 0.5022, with the
# first removed it scores 0.0566. This script answers that question for any
# dataset without re-running HoloClean, by re-implementing the ViolationDetector
# exactly (see cleaners/holoclean/detect/violationdetector.py):
#
#   for a DC  t1&t2&EQ(t1.A,t2.A)&...&IQ(t1.C,t2.C)
#   row t1 violates iff some row t2 agrees on every EQ column and differs on C,
#   and *every* attribute the DC names -- the EQ columns as well as C -- is then
#   flagged for that row.
#
# Equivalently: group by the EQ columns, and if a group holds more than one
# distinct value of C, every row in the group violates. Validated against the
# HoloClean numbers in rein-datasets/beers/results/detection_results.csv.
#
# Read-only: it writes nothing into the dataset directories.
#
#   docker compose run --rm rein python3 scripts/dc_ablation.py \
#       --dataset_name beers bike nasa
####################################################

import argparse
import os
import re

import pandas as pd

from rein.auxiliaries.datasets_dictionary import datasets_dictionary

# EQ(t1.col,t2.col) or IQ(t1.col,t2.col); column names may contain spaces
PREDICATE = re.compile(r'(EQ|IQ)\(t1\.(.+?),t2\.(.+?)\)')


def parse_dcs(path):
    """Reads _all_constraints.txt into [{'eq': [...], 'iq': col, 'raw': line}]."""
    dcs = []
    if not os.path.exists(path):
        return dcs
    with open(path) as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            eq, iq = [], []
            for operation, left, right in PREDICATE.findall(line):
                if left != right:
                    raise ValueError("predicate compares two different columns: " + line)
                (eq if operation == 'EQ' else iq).append(left)
            if len(iq) != 1:
                raise ValueError("expected exactly one IQ predicate in: " + line)
            dcs.append({'eq': eq, 'iq': iq[0], 'raw': line})
    return dcs


def load_frames(dataset):
    """Loads the dirty frame and the ground truth cells, as the benchmark does."""
    paths = datasets_dictionary[dataset]
    dirty = pd.read_csv(paths["dirty_path"], dtype=str, header="infer",
                        encoding="utf-8", keep_default_na=False, low_memory=False)
    errors = pd.read_csv(os.path.join(paths["dataset_path"], "actual_errors.csv"),
                         names=['i', 'j', 'dummy'])
    truth = set(zip(errors['i'].astype(int), errors['j'].astype(int)))
    return dirty, truth


def violating_cells(dirty, dc):
    """The cells one DC flags, with the ViolationDetector's own semantics."""
    group_sizes = dirty.groupby(dc['eq'], sort=False, dropna=False)[dc['iq']].transform('nunique')
    rows = dirty.index[group_sizes > 1]
    columns = [dirty.columns.get_loc(c) for c in dc['eq'] + [dc['iq']]]
    return {(row, column) for row in rows for column in columns}


def score(predicted, truth):
    """precision, recall, f1, tp, fp, fn -- the same arithmetic as __evaluate."""
    tp, fp, fn = len(predicted & truth), len(predicted - truth), len(truth - predicted)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1, tp, fp, fn


def report(dataset):
    dirty, truth = load_frames(dataset)
    dc_path = os.path.join(datasets_dictionary[dataset]["dataset_path"],
                           "constraints", "_all_constraints.txt")
    dcs = parse_dcs(dc_path)

    n_rows, n_columns = dirty.shape
    n_cells = n_rows * n_columns
    error_rate = len(truth) / n_cells
    # the F1 of the trivial detector that flags every cell. The benchmark already
    # reports this as cell_baseline; it is the bar a real detector has to clear.
    cell_baseline = 2 * error_rate / (1 + error_rate)

    print("\n{}".format("=" * 108))
    print("{}: N={} d={} cells={} errors={} eps={:.4f} cell_baseline={:.4f} #DCs={}".format(
        dataset, n_rows, n_columns, n_cells, len(truth), error_rate, cell_baseline, len(dcs)))
    print("=" * 108)

    if not dcs:
        print("  No denial constraints. HoloClean scores 0.0000 here because it has "
              "nothing to violate,")
        print("  not because it looked and found nothing.")
        return

    per_dc = [violating_cells(dirty, dc) for dc in dcs]
    everything = set().union(*per_dc)
    precision, recall, f1, tp, fp, fn = score(everything, truth)
    print("  all {} DCs:  P={:.4f} R={:.4f} F1={:.4f}  TP={} FP={} FN={}  "
          "flags {:.1%} of the table".format(
              len(dcs), precision, recall, f1, tp, fp, fn, len(everything) / n_cells))
    print("  F1 - cell_baseline = {:+.4f}{}".format(
        f1 - cell_baseline,
        "   <-- at or below the flag-everything detector" if f1 <= cell_baseline + 1e-9 else ""))
    print()

    header = "  {:>3} {:<50}{:>8}{:>9}{:>9}{:>9}{:>8}"
    print(header.format("k", "constraint (EQ -> IQ)", "rows", "F1 alone",
                        "F1 w/o", "dF1", "uniqTP"))
    print("  " + "-" * 104)

    rows = []
    for index, (dc, cells) in enumerate(zip(dcs, per_dc), 1):
        others = set().union(*[c for j, c in enumerate(per_dc) if j != index - 1]) \
            if len(per_dc) > 1 else set()
        alone = score(cells, truth)
        without = score(others, truth)
        unique = cells - others
        rows.append((f1 - without[2], index, dc, cells, alone, without, unique))

    for delta, index, dc, cells, alone, without, unique in sorted(rows, reverse=True):
        label = "{} -> {}".format(",".join(dc['eq']), dc['iq'])
        print(header.format(index, label[:49], len(cells) // (len(dc['eq']) + 1),
                            "{:.4f}".format(alone[2]), "{:.4f}".format(without[2]),
                            "{:+.4f}".format(delta), len(unique & truth)))
    print("  " + "-" * 104)
    print("  dF1 = F1(all DCs) - F1(all DCs except this one): how much of the score "
          "this one constraint carries.")
    print("  uniqTP = true errors this constraint is the only one to flag.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_name', nargs='+', required=True)
    args = parser.parse_args()

    for name in args.dataset_name:
        if name not in datasets_dictionary:
            raise ValueError("Dataset {} is not known.".format(name))
        report(name)
    print()
