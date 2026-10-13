#!/usr/bin/env python3
####################################################
# Measures how much memory a detector needs.
#
# Every measurement runs in its own process, so the baseline is the interpreter,
# the libraries and the data and nothing else. A second detector in the same
# process would start from whatever the first one left behind.
#
# Nothing already on disk is touched: the child sends detections.csv,
# actual_errors.csv and error_rate.json to a scratch directory.
#
#   docker compose run --rm rein python3 scripts/measure_memory.py --self-test
#   docker compose run --rm rein python3 scripts/measure_memory.py --datasets adult har --tiers dirty_profiled clean_profiled
####################################################

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tracemalloc
from datetime import datetime
from statistics import mean, stdev

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# holoclean ships in cleaners/ but setup.py does not install it and PYTHONPATH is
# empty, so detectors.py catches the ImportError and the detector never runs
sys.path.insert(0, os.path.join(ROOT, "cleaners"))

from rein.auxiliaries.memory_probe import (PeakTracker, current_rss, max_rss, rss_unit,
                                            tracemalloc_coverage, trim_allocator)

# the child prints its record on one line behind this prefix, so the parent can
# pick it out of whatever else the detector logged
RECORD_PREFIX = "MEMORY_RECORD "

MB = 1024 * 1024

SUMMARY_FIELDS = ["dataframe_bytes", "baseline_rss_bytes", "peak_rss_bytes",
                  "tool_memory_bytes", "amplification", "tracemalloc_peak_bytes",
                  "tracemalloc_minus_tool_bytes", "probe_coverage"]


def measure(call, dirtyDF):
    """Runs call() and reports the memory it needed.

    Everything the detector should not be charged for - the imports, loading the
    data, building the ground truth - has to happen before this is called, so it
    lands in the baseline instead of in the delta.
    """
    dataframe_bytes = int(dirtyDF.memory_usage(deep=True).sum())

    # give back what loading the data left the allocator holding, so the detector
    # has to ask the OS for the memory it needs instead of finding it lying around
    trimmed = trim_allocator()
    baseline = current_rss()

    # tracemalloc only traces what is allocated after start(), so starting it
    # here gives the peak of the window. python 3.8 has no reset_peak().
    tracemalloc.start()
    with PeakTracker() as tracker:
        output = call()
    tracemalloc_peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    peak = tracker.peak

    # a detector that peaks below the baseline reports 0, not a negative number
    tool_memory = max(0, peak - baseline)

    record = {
        "dataframe_bytes": dataframe_bytes,
        "baseline_rss_bytes": baseline,
        "peak_rss_bytes": peak,
        "tool_memory_bytes": tool_memory,
        "amplification": tool_memory / dataframe_bytes if dataframe_bytes else None,
        "tracemalloc_peak_bytes": tracemalloc_peak,
        # what tracemalloc saw that the RSS delta did not. trim_allocator takes
        # most of this out, and what is left should be small: on har it is 0.01 MB
        # against a 6.7 MB peak. a tool allocating outside python, on the JVM or
        # through torch, should push this the other way and turn it negative.
        "tracemalloc_minus_tool_bytes": tracemalloc_peak - tool_memory,
        # the whole process high water mark, for comparison only. it cannot be
        # reset, so it carries whatever peaked before the window as well.
        "max_rss_bytes": max_rss(),
        "peak_method": tracker.method,
        "allocator_trimmed": trimmed,
    }
    record.update(tracemalloc_coverage())
    record.update({
        "rss_unit": rss_unit(),
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "timestamp": datetime.now().isoformat(),
    })
    return record, output


def load_ground_truth(data, dataset_path, dirtyDF, groundtruthDF):
    """Reads the cached ground truth if it is there, computes it otherwise.

    Same two branches as run_detectors. Recomputing adult takes about half a
    minute, and it is the same answer every time, so the cache is worth using.
    Either way this happens before the window and lands in the baseline.
    """
    import pandas as pd

    errors_path = os.path.join(dataset_path, "actual_errors.csv")
    rate_path = os.path.join(dataset_path, "error_rate.json")

    if os.path.exists(errors_path) and os.path.exists(rate_path):
        reader = pd.read_csv(errors_path, names=["i", "j", "dummy"])
        actual_errors = reader.groupby(["i", "j"])["dummy"].apply(list).to_dict()
        with open(rate_path) as handle:
            error_rate = json.load(handle)
        return actual_errors, error_rate, True

    actual_errors, error_rate = data.get_actual_errors(dirtyDF, groundtruthDF)
    return actual_errors, error_rate, False


def measure_detector(dataset, detector, tier):
    """Runs one detector on one dataset and returns the record. Child process only."""
    import pandas as pd

    from rein.auxiliaries.datasets_dictionary import datasets_dictionary
    from rein.datasets import Datasets
    from rein.detectors import Detectors

    real_path = datasets_dictionary[dataset]["dataset_path"]
    scratch = tempfile.mkdtemp(prefix="memory_")

    # holoclean reads its denial constraints out of the dataset directory, so the
    # scratch needs a copy or it would quietly run with no constraints at all
    constraints = os.path.join(real_path, "constraints")
    if os.path.exists(constraints):
        shutil.copytree(constraints, os.path.join(scratch, "constraints"))

    # the detector reads this for its detections directory, Datasets keeps its
    # own copy for actual_errors.csv, so both have to be pointed at the scratch
    datasets_dictionary[dataset]["dataset_path"] = scratch
    dataset_dict = datasets_dictionary[dataset]

    data = Datasets(dataset_dict)
    data.dataset_path = scratch

    dirtyDF = data.load_data(dataset_dict["dirty_path"])
    groundtruthDF = data.load_data(dataset_dict["groundTruth_path"])
    actual_errors, error_rate, cached = load_ground_truth(
        data, real_path, dirtyDF, groundtruthDF)

    detectors = Detectors(dataset, actual_errors)
    function = getattr(detectors, detector)

    configs = {
        "detect_method": "ALL",
        "keys": dataset_dict.get("keys", []),
        "path_dirty": dataset_dict["dirty_path"],
        "correct_labels": pd.DataFrame(),
        "expectation_tier": tier,
        "groundtruthDF": groundtruthDF,
    }

    record, output = measure(lambda: function(dirtyDF, dataset, configs), dirtyDF)
    shutil.rmtree(scratch, ignore_errors=True)

    detections, results = output
    record.update({
        "dataset": dataset,
        "detector": detector,
        "tier": tier,
        "rows": int(dirtyDF.shape[0]),
        "columns": int(dirtyDF.shape[1]),
        "detections": len(detections),
        "error_rate": error_rate,
        "ground_truth_cached": cached,
    })
    return record


def measure_synthetic(rows=500000, copies=4):
    """Runs a trivial detector on a synthetic frame. Needs no GE and no dataset."""
    import numpy as np
    import pandas as pd

    dirtyDF = pd.DataFrame({
        "a": np.arange(rows, dtype=np.float64),
        "b": np.arange(rows, dtype=np.float64) * 2,
    })

    def detector():
        # holds a few copies of the frame at once, so the amplification should
        # land near the number of copies and can be checked against
        held = [dirtyDF.copy() for _ in range(copies)]
        detections = {(i, 0): "DUMMY VALUE" for i in range(0, rows, 1000)}
        del held
        return detections, {}

    record, output = measure(detector, dirtyDF)
    record.update({
        "dataset": "synthetic",
        "detector": "synthetic",
        "tier": "none",
        "rows": rows,
        "columns": int(dirtyDF.shape[1]),
        "detections": len(output[0]),
        "expected_amplification": copies,
    })
    return record


def run_child(child_args):
    """Spawns one measurement in a fresh process and returns its record."""
    command = [sys.executable, os.path.abspath(__file__), "--child"] + child_args
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    for line in process.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith(RECORD_PREFIX):
            return json.loads(line[len(RECORD_PREFIX):])

    sys.stderr.write(process.stderr.decode("utf-8", "replace")[-3000:] + "\n")
    raise RuntimeError("no record from child: {}".format(" ".join(child_args)))


def append_record(path, record):
    """Appends one record, flushed, so a crashed run keeps what it already had."""
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    with open(path, "a") as handle:
        handle.write(json.dumps(record) + "\n")
        handle.flush()


def summarise(records):
    groups = {}
    for record in records:
        key = (record["dataset"], record["detector"], record["tier"])
        groups.setdefault(key, []).append(record)

    summary = []
    for key, group in sorted(groups.items()):
        entry = {"dataset": key[0], "detector": key[1], "tier": key[2], "runs": len(group)}
        for field in SUMMARY_FIELDS:
            values = [record[field] for record in group if record.get(field) is not None]
            entry[field + "_mean"] = mean(values) if values else None
            # a single run has no spread, and reporting 0.0 would pretend it does
            entry[field + "_std"] = stdev(values) if len(values) > 1 else None
        summary.append(entry)
    return summary


def print_summary(summary):
    header = "{:<12}{:<9}{:>10}{:>11}{:>11}{:>11}{:>8}{:>9}{:>11}{:>8}{:>8}"
    print(header.format("dataset", "tier", "frame MB", "baseline", "peak", "tool MB",
                        "amp", "amp std", "tracemall", "gap MB", "cover"))
    print("-" * 109)

    for entry in summary:
        print(header.format(
            entry["dataset"],
            entry["tier"],
            "{:.2f}".format(entry["dataframe_bytes_mean"] / MB),
            "{:.1f}".format(entry["baseline_rss_bytes_mean"] / MB),
            "{:.1f}".format(entry["peak_rss_bytes_mean"] / MB),
            "{:.2f}".format(entry["tool_memory_bytes_mean"] / MB),
            "-" if entry["amplification_mean"] is None else "{:.2f}".format(entry["amplification_mean"]),
            "-" if entry["amplification_std"] is None else "{:.2f}".format(entry["amplification_std"]),
            "{:.2f}".format(entry["tracemalloc_peak_bytes_mean"] / MB),
            "{:.2f}".format(entry["tracemalloc_minus_tool_bytes_mean"] / MB),
            "{:.2f}".format(entry["probe_coverage_mean"])))


def check(records, summary):
    """The sanity checks. Prints what it finds and changes nothing."""
    problems = []

    # tracemalloc sees a subset of what the process allocates, so its peak should
    # not come out above the RSS delta. if it does, the window is wrong.
    for record in records:
        if record["tracemalloc_peak_bytes"] > record["tool_memory_bytes"] + MB:
            problems.append("{} {} run {}: tracemalloc peak {:.2f} MB is above the RSS delta {:.2f} MB by {:.2f} MB".format(
                record["dataset"], record["tier"], record.get("run", 0),
                record["tracemalloc_peak_bytes"] / MB, record["tool_memory_bytes"] / MB,
                record["tracemalloc_minus_tool_bytes"] / MB))

    # a tool memory that small is measurement noise, and the amplification
    # built on it does not mean anything
    for entry in summary:
        if entry["tool_memory_bytes_mean"] < 2 * MB:
            problems.append("{} {}: tool memory {:.2f} MB is too small to read".format(
                entry["dataset"], entry["tier"], entry["tool_memory_bytes_mean"] / MB))

    # repeated runs of the same deterministic detector should agree
    for entry in summary:
        spread = entry["tool_memory_bytes_std"]
        average = entry["tool_memory_bytes_mean"]
        if spread is not None and average > 0 and spread / average > 0.25:
            problems.append("{} {}: tool memory varies by {:.0f}% across {} runs".format(
                entry["dataset"], entry["tier"], 100 * spread / average, entry["runs"]))

    print("\nchecks:")
    if not problems:
        print("  all passed")
    for problem in problems:
        print("  FAILED  " + problem)
    return problems


def self_test(repeats=2):
    print("running the whole path on synthetic data\n")

    records = []
    for run in range(repeats):
        record = run_child(["--synthetic"])
        record["run"] = run
        records.append(record)

    summary = summarise(records)
    print_summary(summary)

    entry = summary[0]
    expected = records[0]["expected_amplification"]
    problems = check(records, summary)

    # the synthetic detector holds a known number of copies, so the amplification
    # is known in advance and worth checking directly
    measured = entry["amplification_mean"]
    if not 0.5 * expected <= measured <= 1.5 * expected:
        problems.append("amplification {:.2f} is far from the expected {}".format(measured, expected))
        print("  FAILED  amplification {:.2f} is far from the expected {}".format(measured, expected))
    else:
        print("  amplification {:.2f} against an expected {}".format(measured, expected))

    print("\n{} on {}, ru_maxrss in {}".format(
        records[0]["python"], records[0]["platform"], records[0]["rss_unit"]))

    return 1 if problems else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", default=["beers"])
    parser.add_argument("--detector", default="greatExpectations")
    parser.add_argument("--tiers", nargs="+", default=["hand_written", "dirty_profiled", "clean_profiled"])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out", default=os.path.join("detection_logs", "memory_records.jsonl"))
    parser.add_argument("--self-test", action="store_true")
    # used when this script calls itself for a single measurement
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--tier", default=None)
    args = parser.parse_args()

    if args.child:
        if args.synthetic:
            record = measure_synthetic()
        else:
            record = measure_detector(args.dataset, args.detector, args.tier)
        print(RECORD_PREFIX + json.dumps(record))
        return 0

    if args.self_test:
        return self_test()

    records = []
    for dataset in args.datasets:
        for tier in args.tiers:
            for run in range(args.repeats):
                record = run_child(["--dataset", dataset, "--detector", args.detector,
                                    "--tier", tier])
                record["run"] = run
                append_record(args.out, record)
                records.append(record)

    summary = summarise(records)
    print()
    print_summary(summary)
    check(records, summary)

    summary_path = os.path.splitext(args.out)[0] + "_summary.json"
    with open(summary_path, "w") as handle:
        json.dump(summary, handle, indent=2)
    print("\nrecords: {}\nsummary: {}".format(args.out, summary_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
