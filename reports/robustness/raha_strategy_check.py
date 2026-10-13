"""Raha single-strategy check for the robustness report: runs all Raha 1.25 strategies on a kept
dirty file (container-local /tmp) and prints, per column, the best single strategy scored on the
injected non-blank outliers vs the untouched cells, and whether its flagged set is a length threshold.
Written by the 30 Sep verification agent, kept for provenance.
Run: docker compose run --rm -T rein python3 - <run names> < reports/robustness/raha_strategy_check.py"""
import os, shutil, sys, json
import numpy as np
from raha.detection import Detection
from raha.tools.dBoost.dboost.utils.read import stream_tuples
import io
# 1) type inference: header row decides types
s = io.StringIO("frequency,angle\n800.0,0.0\n1000.0,1.5\n")
print("dBoost field types:", [tuple(type(v).__name__ for v in row) for row in stream_tuples(s, ",", False, True)()][:3])
for run in sys.argv[1:]:
    src = "/rein/reports/robustness/runs/" + run
    dst = "/tmp/rc_" + run
    os.makedirs(dst, exist_ok=True)
    shutil.copy(src + "/dirty.csv", dst + "/dirty.csv")
    shutil.copy("/rein/datasets/nasa/clean.csv", dst + "/clean.csv")
    dd = {"name": "rc_" + run, "path": dst + "/dirty.csv", "clean_path": dst + "/clean.csv"}
    app = Detection(); app.SAVE_RESULTS = False
    d = app.initialize_dataset(dd)
    app.run_strategies(d)
    ae = set(tuple(map(int, l.split(",")[:2])) for l in open(src + "/actual_errors.csv"))
    n = d.dataframe.shape[0]
    line = []
    for j, col in enumerate(d.dataframe.columns[:5]):
        vals = d.dataframe[col].tolist()
        inj = set(i for i in range(n) if (i, j) in ae and vals[i] != "")
        unt = set(i for i in range(n) if (i, j) not in ae)
        best = (0, None, None)
        for sp in d.strategy_profiles:
            name = json.loads(sp["name"])
            out = set(i for (i, jj) in sp["output"] if jj == j)
            tp = len(out & inj); fp = len(out & unt)
            p = tp / (tp + fp) if tp + fp else 0; r = tp / len(inj)
            f = 2 * p * r / (p + r) if p + r else 0
            if f > best[0]: best = (f, name, out)
        # does the best strategy's flagged set equal a length threshold?
        f, name, out = best
        lens_out = [len(vals[i]) for i in out if vals[i] != ""]
        lens_not = [len(vals[i]) for i in range(n) if i not in out and vals[i] != ""]
        line.append(f"{col}: bestF1={f:.2f} {name} flagged len>={min(lens_out) if lens_out else None} unflagged len<={max(lens_not) if lens_not else None}")
    print("==", run); print("  " + "\n  ".join(line))
    shutil.rmtree(dst)
