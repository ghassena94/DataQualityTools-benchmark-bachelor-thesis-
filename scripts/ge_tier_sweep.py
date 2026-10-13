#!/usr/bin/env python3
####################################################
# Runs the three greatExpectations tiers side by side and prints their metrics.
#
# Read-only by design: it never writes detections.csv into the dataset directory
# and never appends to detection_results.csv, so the hand_written results already on
# disk stay exactly as the benchmark left them. benchmark.py is not touched.
#
#   docker compose run --rm rein python3 scripts/ge_tier_sweep.py --dataset_name beers
####################################################

import argparse
import time
from math import isclose

import pandas as pd
from great_expectations.dataset import PandasDataset

from rein.auxiliaries.datasets_dictionary import datasets_dictionary
from rein.auxiliaries.expectations_dictionary import DATASET_EXPECTATIONS
from rein.auxiliaries.expectations_profiler import profile_expectations


def load_data(path):
    """Reads a CSV with the same options as Datasets.load_data"""
    return pd.read_csv(path, dtype=str, header="infer", encoding="utf-8",
                       keep_default_na=False, low_memory=False)


def cells_differ(dirty_value, truth_value):
    """Copy of Datasets.__cells_differ, which is name-mangled and cannot be imported"""
    dirty_missing = pd.isna(dirty_value) or dirty_value == ""
    truth_missing = pd.isna(truth_value) or truth_value == ""
    if dirty_missing or truth_missing:
        return dirty_missing != truth_missing
    try:
        return not isclose(float(dirty_value), float(truth_value), rel_tol=1e-6)
    except (TypeError, ValueError, OverflowError):
        return dirty_value != truth_value


def get_actual_errors(dirtyDF, truthDF):
    """Same cell by cell comparison as Datasets.get_actual_errors, minus the disk write"""
    if list(dirtyDF.columns) != list(truthDF.columns):
        if sorted(dirtyDF.columns) == sorted(truthDF.columns):
            truthDF = truthDF[list(dirtyDF.columns)]

    errors = set()
    for col in dirtyDF.columns:
        col_j = dirtyDF.columns.get_loc(col)
        for i in range(len(dirtyDF)):
            if cells_differ(dirtyDF.iat[i, col_j], truthDF.iat[i, col_j]):
                errors.add((i, col_j))
    return errors


def detect(dirtyDF, expectations):
    """Applies a list of expectations, mirroring the loop in Detectors.greatExpectations"""
    ds = PandasDataset(dirtyDF)
    detections = set()
    for expectation in expectations:
        column = expectation['column']
        if column not in dirtyDF.columns:
            print("  skipping expectation on missing column {}".format(column))
            continue
        col_j = dirtyDF.columns.get_loc(column)
        result = getattr(ds, expectation['expectation'])(
            column, **expectation['kwargs'], result_format="COMPLETE")
        for i in result.result['unexpected_index_list']:
            detections.add((i, col_j))
    return detections


def build_expectations(tier, dataset, dirtyDF, truthDF, max_set_size):
    """Picks the expectations for a tier, the same way Detectors.greatExpectations does"""
    if tier == "dirty_profiled":
        return profile_expectations(dirtyDF, max_set_size)
    if tier == "clean_profiled":
        return profile_expectations(truthDF, max_set_size)
    return DATASET_EXPECTATIONS[dataset]["hand_written"]


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_name', default='beers')
    parser.add_argument('--tiers', nargs='+', default=['hand_written', 'dirty_profiled', 'clean_profiled'])
    # the profiler's cutoff for building a value-set rule. worth sweeping: it is what
    # decides whether the clean_profiled tier can cover a column like state (51 distinct clean values)
    parser.add_argument('--max_set_size', type=int, default=20)
    args = parser.parse_args()

    dataset = args.dataset_name
    if dataset not in datasets_dictionary:
        raise ValueError("Dataset {} is not known.".format(dataset))

    dirtyDF = load_data(datasets_dictionary[dataset]["dirty_path"])
    truthDF = load_data(datasets_dictionary[dataset]["groundTruth_path"])

    actual_errors = get_actual_errors(dirtyDF, truthDF)
    error_rate = len(actual_errors) / truthDF.size

    print("\ndataset: {}   cells: {}   actual errors: {}   error rate: {:.4f}   max_set_size: {}\n"
          .format(dataset, dirtyDF.size, len(actual_errors), error_rate, args.max_set_size))

    header = "{:<10}{:>7}{:>8}{:>7}{:>7}{:>7}{:>9}{:>9}{:>9}{:>10}{:>9}"
    print(header.format("tier", "#exp", "#detect", "TP", "FP", "FN",
                        "P", "R", "F1", "cell_FG1", "runtime"))
    print("-" * 92)

    for tier in args.tiers:
        expectations = build_expectations(tier, dataset, dirtyDF, truthDF, args.max_set_size)

        start_time = time.time()
        detections = detect(dirtyDF, expectations)
        runtime = time.time() - start_time

        # identical arithmetic to Detectors.__evaluate
        tp = len(detections & actual_errors)
        precision = 0.0 if not detections else tp / len(detections)
        recall = 0.0 if not actual_errors else tp / len(actual_errors)
        f1 = 0.0 if (precision + recall) == 0 else (2 * precision * recall) / (precision + recall)

        # identical arithmetic to benchmark.py
        cell_FG1 = (f1 - error_rate) / ((1 - error_rate) * f1) if f1 > 0 and error_rate < 1.0 else None

        print(header.format(
            tier, len(expectations), len(detections), tp, len(detections) - tp,
            len(actual_errors) - tp, "{:.4f}".format(precision), "{:.4f}".format(recall),
            "{:.4f}".format(f1),
            "-" if cell_FG1 is None else "{:.4f}".format(cell_FG1),
            "{:.3f}s".format(runtime)))

    # which columns the profiler left without a real rule. this is the whole story
    # behind the dirty_profiled tier, so print it rather than leaving it to be inferred
    print("\ncolumns carrying only the missing-value rule (no regex, no value set):")
    for tier, frame in (("dirty_profiled", dirtyDF), ("clean_profiled", truthDF)):
        if tier not in args.tiers:
            continue
        profiled = profile_expectations(frame, args.max_set_size)
        ruled = {e['column'] for e in profiled
                 if e['expectation'] != 'expect_column_values_to_not_be_in_set'}
        print("  {:<9} {}".format(tier, sorted(set(frame.columns) - ruled)))
    print()
