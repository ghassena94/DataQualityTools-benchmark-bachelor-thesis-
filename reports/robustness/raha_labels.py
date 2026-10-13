"""Raha label-composition check for the robustness report: reruns Raha 1.25 step by step with seeds 1-5
on a kept dirty file and logs how many of the 20 labelled tuples are dirty and how many error cells
(blanks / outliers) they contain. Reproduces raha_seed_check.py F1 values exactly.
Written by the 2 Oct verification agent, kept for provenance.
Run: docker compose run --rm -T rein python3 - <run names> < reports/robustness/raha_labels.py"""
import os, shutil, sys, random
import numpy as np
from raha.detection import Detection
for run in sys.argv[1:]:
    src = "/rein/reports/robustness/runs/" + run
    ae = set(tuple(map(int, l.split(",")[:2])) for l in open(src + "/actual_errors.csv"))
    import csv
    dirty = list(csv.reader(open(src + "/dirty.csv")))[1:]
    for s in [1, 2, 3, 4, 5]:
        dst = "/tmp/rl_%s_%d" % (run, s)
        os.makedirs(dst, exist_ok=True)
        shutil.copy(src + "/dirty.csv", dst + "/dirty.csv")
        shutil.copy("/rein/datasets/nasa/clean.csv", dst + "/clean.csv")
        np.random.seed(s); random.seed(s)
        app = Detection(); app.SAVE_RESULTS = False; app.VERBOSE = False
        dd = {"name": "rl_%s_%d" % (run, s), "path": dst + "/dirty.csv", "clean_path": dst + "/clean.csv"}
        d = app.initialize_dataset(dd)
        app.run_strategies(d); app.generate_features(d); app.build_clusters(d)
        while len(d.labeled_tuples) < app.LABELING_BUDGET:
            app.sample_tuple(d)
            app.label_with_ground_truth(d)
        app.propagate_labels(d); app.predict_labels(d)
        det = d.detected_cells
        tp = len(set(det) & ae); p = tp / len(det) if det else 0; r = tp / len(ae)
        f = 2 * p * r / (p + r) if p + r else 0
        lt = list(d.labeled_tuples)
        err_cells = [(i, j) for (i, j) in ae if i in d.labeled_tuples]
        blanks = [(i, j) for (i, j) in err_cells if dirty[i][j] == ""]
        cols = sorted({j for i, j in err_cells})
        print("%s s%d F1=%.3f P=%.3f R=%.3f | dirty labeled tuples %d/20, error cells %d (blank %d, outlier %d), error cols %s" % (
            run, s, f, p, r, len({i for i, j in err_cells}), len(err_cells), len(blanks), len(err_cells) - len(blanks), cols), flush=True)
        shutil.rmtree(dst)
