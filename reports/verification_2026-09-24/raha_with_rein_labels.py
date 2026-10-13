"""Run inside the container. Indicative, read-only (SAVE_RESULTS=False): Raha at budget 20, seed 1,
labeled once from its own positional diff and once from actual_errors.csv, both scored against actual_errors.csv."""
import csv, json, time, random
import numpy
from raha.detection import Detection
base = "/rein/datasets"
def prf(det, gt):
    tp = sum(1 for c in det if c in gt); fp = len(det) - tp; fn = len(gt) - tp
    p = tp / (tp + fp) if tp + fp else 0.0; r = tp / (tp + fn) if tp + fn else 0.0
    return dict(tp=tp, fp=fp, fn=fn, precision=round(p, 4), recall=round(r, 4), f1=round(2 * p * r / (p + r), 4) if p + r else 0.0)
for name in ["nasa", "bike", "smartfactory"]:
    gt = {}
    for row in csv.reader(open(f"{base}/{name}/actual_errors.csv")):
        try: gt[(int(row[0]), int(row[1]))] = "DUMMY VALUE"
        except Exception: pass
    dd = {"name": name, "path": f"{base}/{name}/dirty.csv", "clean_path": f"{base}/{name}/clean.csv"}
    out = {}
    for label_source in ["raha_own_diff", "actual_errors_csv"]:
        random.seed(1); numpy.random.seed(1)
        app = Detection(); app.LABELING_BUDGET = 20; app.SAVE_RESULTS = False; app.VERBOSE = False
        t0 = time.time()
        d = app.initialize_dataset(dd)
        if label_source == "actual_errors_csv":
            d.get_actual_errors_dictionary = lambda gt=gt: gt
        app.run_strategies(d); app.generate_features(d); app.build_clusters(d)
        while len(d.labeled_tuples) < app.LABELING_BUDGET:
            app.sample_tuple(d); app.label_with_ground_truth(d)
        app.propagate_labels(d); app.predict_labels(d)
        out[label_source] = dict(prf(d.detected_cells, gt), n_detections=len(d.detected_cells), seconds=round(time.time() - t0, 1))
    print(json.dumps({name: out}), flush=True)
