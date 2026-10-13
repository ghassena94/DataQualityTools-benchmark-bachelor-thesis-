"""Parse REIN detection-result PDFs and log one row per (run, dataset, tool).

Usage:
    python log_detection_results.py report1.pdf [report2.pdf ...] --log results/runs_log.csv

Each PDF is treated as one run (run_id = its 'generated' timestamp).
TP/FP/FN are derived:  TP ~ recall * injected_errors
                       FP = #detections - TP,  FN = injected_errors - TP
TP is the integer consistent with all three rounded scores (P, R, F1).
When the 4-decimal PDF values leave it ambiguous, the exact counts are taken
from <dataset>/results/detection_results.csv (same detector, #detections and
F1); 'TP_range' shows the remaining ambiguity if no single stored run matches.
Re-running on the same PDF does not duplicate rows.

Needs: pip install pdfplumber pandas
"""
import argparse
import logging
import re
from pathlib import Path

import pandas as pd
import pdfplumber

logging.getLogger("pdfminer").setLevel(logging.ERROR)  # silence font warnings

NUM = r"-?[\d,]*\.?\d+"
METRICS = {  # label in PDF -> column name
    "rows (N)": "n_rows",
    "dimension (d)": "d",
    "cells": "cells",
    "injected errors": "injected_errors",
    "dirty row fraction": "dirty_row_fraction",
    "cell error rate (eps)": "eps",
    "cell_baseline = 2eps/(1+eps)": "cell_baseline",
    "denial constraints": "n_dcs",
}
DETECTOR = re.compile(
    rf"^\s*(GreatExpectations \([\w ]+\)|HoloClean|Raha)\s+"
    rf"({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s*$"
)


def num(s):
    s = s.replace(",", "")
    return float(s) if "." in s else int(s)


def solve_tp(p, r, f1, n_det, errs):
    """Find integer TP consistent with the 4-decimal precision, recall and F1.

    Returns (best, lo, hi). lo != hi means the rounded PDF numbers cannot
    pin TP down exactly -- use the raw run logs for those.
    """
    if n_det == 0:
        return 0, 0, 0
    guess = r * errs if errs <= n_det else p * n_det
    cands = range(max(0, int(guess) - 5), min(n_det, errs, int(guess) + 6) + 1)
    ok = [t for t in cands
          if round(t / n_det, 4) == p and round(t / errs, 4) == r
          and round(2 * t / (n_det + errs), 4) == f1]
    if not ok:  # fall back to the closest estimate
        t = round(guess)
        return t, t, t
    best = min(ok, key=lambda t: abs(t - guess))
    return best, min(ok), max(ok)


# PDF label -> detector key in <dataset>/results/detection_results.csv
DETECTOR_KEYS = {
    "HoloClean": "holoclean", "Raha": "raha",
    "GreatExpectations (dirty profiled)": "greatExpectations:dirty_profiled",
    "GreatExpectations (clean profiled)": "greatExpectations:clean_profiled",
    "GreatExpectations (hand written)": "greatExpectations:hand_written",
}
RESULTS_DIR = Path(__file__).resolve().parents[1] / "datasets"


def exact_counts(dataset, tool, n_det, f1):
    """Exact (TP, FP, FN) of the stored run the PDF row came from, or None.

    Matches the detector, the detection count and the 4-decimal F1. Used when
    the rounded PDF scores leave TP ambiguous.
    """
    path = RESULTS_DIR / dataset / "results" / "detection_results.csv"
    if tool not in DETECTOR_KEYS or not path.exists():
        return None
    runs = pd.read_csv(path)
    runs = runs[(runs["detector"] == DETECTOR_KEYS[tool])
                & (runs["#detections"] == n_det) & (runs["f1"].round(4) == f1)]
    counts = {tuple(int(v) for v in row) for row in runs[["cell_TP", "cell_FP", "cell_FN"]].values}
    return counts.pop() if len(counts) == 1 else None


def parse_pdf(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    lines = text.splitlines()

    # header: "nasa, breast_cancer, ... · generated 2026-09-15 17:02"
    header = next(l for l in lines if "generated" in l)
    datasets = [d.strip() for d in header.split("·")[0].split(",")]
    run_id = re.search(r"generated\s+(.+)$", header).group(1).strip()

    rows, current, meta = [], None, {}
    for line in lines:
        s = line.strip()
        if s in datasets:                       # new dataset section
            current, meta = s, {}
            continue
        if current is None:
            continue
        for label, col in METRICS.items():      # dataset metrics
            m = re.match(rf"^{re.escape(label)}\s+({NUM})$", s)
            if m:
                meta[col] = num(m.group(1))
        m = re.match(r"^columns with errors \(d_err\)\s+(\d+) of (\d+)$", s)
        if m:
            meta["d_err"] = int(m.group(1))
        m = DETECTOR.match(line)                # detector result line
        if m:
            tool = m.group(1)
            p, r, f1, f1_gain, n_det, rt = map(num, m.groups()[1:])
            errs = meta["injected_errors"]
            tp, tp_lo, tp_hi = solve_tp(p, r, f1, n_det, errs)
            if tp_lo != tp_hi:                  # rounded scores are ambiguous
                exact = exact_counts(current, tool, n_det, f1)
                if exact is not None:
                    tp = tp_lo = tp_hi = exact[0]
            rows.append({
                "run_id": run_id, "source": Path(path).name, "dataset": current,
                **meta, "tool": tool,
                "TP": tp, "FP": n_det - tp, "FN": errs - tp,
                "detections": n_det, "precision": p, "recall": r, "F1": f1,
                "F1_minus_baseline": f1_gain, "runtime_s": rt,
                "TP_range": f"{tp_lo}-{tp_hi}" if tp_lo != tp_hi else "exact",
            })
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--log", default="results/runs_log.csv")
    args = ap.parse_args()

    new = pd.concat([parse_pdf(p) for p in args.pdfs], ignore_index=True)
    log = Path(args.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    if log.exists():
        old = pd.read_csv(log)
        new = pd.concat([old, new]).drop_duplicates(
            subset=["run_id", "source", "dataset", "tool"], keep="last")
    new.to_csv(log, index=False)

    # print per dataset -> per tool
    for ds, g in new.groupby("dataset", sort=False):
        print(f"\n== {ds}  (eps={g.eps.iloc[0]:.4f}, errors={g.injected_errors.iloc[0]}) ==")
        print(g[["run_id", "tool", "TP", "FP", "FN", "TP_range", "precision", "recall", "F1"]]
              .to_string(index=False))
    print(f"\nLogged {len(new)} rows -> {log}")


if __name__ == "__main__":
    main()