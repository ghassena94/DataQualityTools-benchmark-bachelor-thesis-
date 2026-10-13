"""Run on the host (csv module only) from the repo root: scores rein-datasets/<ds>/raha/detections.csv
against actual_errors.csv and against the positional dirty-vs-clean diff, and classifies the false positives."""
import csv
base = "rein-datasets"
def feq(a, b):
    try: return float(a) == float(b)
    except Exception: return False
def cells(path):
    s = set()
    for row in csv.reader(open(path, newline="")):
        try: s.add((int(row[0]), int(row[1])))
        except Exception: pass
    return s
def prf(det, gt):
    tp = len(det & gt); fp = len(det - gt); fn = len(gt - det)
    p = tp / (tp + fp) if tp + fp else 0; r = tp / (tp + fn) if tp + fn else 0
    return tp, fp, fn, round(p, 4), round(r, 4), round(2 * p * r / (p + r), 4) if p + r else 0
for name in ["nasa", "bike", "smartfactory"]:
    rd = lambda p: [[c.strip() for c in row] for row in csv.reader(open(p, newline="", encoding="utf-8"))]
    dirty = rd(f"{base}/{name}/dirty.csv")[1:]; clean = rd(f"{base}/{name}/clean.csv")[1:]
    ncol = len(dirty[0])
    diff = set((i, j) for i in range(len(dirty)) for j in range(ncol) if dirty[i][j] != clean[i][j])
    gt = cells(f"{base}/{name}/actual_errors.csv"); det = cells(f"{base}/{name}/raha/detections.csv")
    tp, fp, fn, p, r, f1 = prf(det, gt); fps = det - gt
    print(f"{name}: detections={len(det)} | vs actual_errors: TP={tp} FP={fp} FN={fn} P={p} R={r} F1={f1} | "
          f"FP float-format-only={sum(1 for i, j in fps if feq(dirty[i][j], clean[i][j]))} FP inside positional diff={len(fps & diff)} | "
          f"vs positional diff TP/FP/FN/P/R/F1={prf(det, diff)}")
