"""Raha seed check for the robustness report: reruns Raha 1.25 (Detection.run, default budget 20)
directly on each kept dirty file with NumPy/random seeds 1-5, in container-local /tmp; scores
against the run's actual_errors.csv. Written by the 30 Sep verification agent, kept for provenance.
Run: docker compose run --rm -T rein python3 - <run names> < reports/robustness/raha_seed_check.py"""
import os, shutil, sys, random
import numpy as np
from raha.detection import Detection
for run in sys.argv[1:]:
    src = "/rein/reports/robustness/runs/" + run
    ae = set(tuple(map(int, l.split(",")[:2])) for l in open(src + "/actual_errors.csv"))
    res = []
    for s in [1, 2, 3, 4, 5]:
        dst = "/tmp/rs_%s_%d" % (run, s)
        os.makedirs(dst, exist_ok=True)
        shutil.copy(src + "/dirty.csv", dst + "/dirty.csv")
        shutil.copy("/rein/datasets/nasa/clean.csv", dst + "/clean.csv")
        np.random.seed(s); random.seed(s)
        app = Detection(); app.SAVE_RESULTS = False
        det = app.run({"name": "rs_%s_%d" % (run, s), "path": dst + "/dirty.csv", "clean_path": dst + "/clean.csv"})
        tp = len(set(det) & ae); p = tp / len(det) if det else 0; r = tp / len(ae)
        f = 2 * p * r / (p + r) if p + r else 0
        res.append("s%d F1=%.3f (P %.3f R %.3f)" % (s, f, p, r))
        shutil.rmtree(dst)
    print(run, " | ".join(res), flush=True)
