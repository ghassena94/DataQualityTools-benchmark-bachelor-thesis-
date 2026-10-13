"""Replicate HoloClean's error detection on a kept robustness run from nasa's 4 denial constraints
(FDs L -> r): for every constraint, group the rows by their (string) values of L; in a group with
more than one value of r, every L and r cell of every row is flagged. The union over the
constraints is compared with the run's detections.csv, then three counterfactuals make injected
values unique before grouping, to find which value equalities create the extra flags:
  existing  = injected values equal to a clean value of their column
  injected  = injected values equal only to other injected values of their column
  all       = every injected value
Written 2 Oct for the robustness report (mechanism of HoloClean's F1 in the formatted variants).
Run from the repo root: python3 reports/robustness/holo_replicate.py <run folder name> [...]"""
import csv, re, sys

DCS = []
for line in open('rein-datasets/nasa/constraints/_all_constraints.txt'):
    if line.startswith('t1'):
        lhs = re.findall(r'EQ\(t1\.(\w+),', line)
        rhs = re.findall(r'IQ\(t1\.(\w+),', line)[0]
        DCS.append((lhs, rhs))
clean = list(csv.reader(open('rein-datasets/nasa/clean.csv')))
H = clean[0]; clean = clean[1:]
col = {h: j for j, h in enumerate(H)}


def detect(rows):
    flagged = set()
    for lhs, rhs in DCS:
        groups = {}
        for i, r in enumerate(rows):
            groups.setdefault(tuple(r[col[a]] for a in lhs), []).append(i)
        for members in groups.values():
            if len({rows[i][col[rhs]] for i in members}) > 1:
                for i in members:
                    for a in lhs + [rhs]:
                        flagged.add((i, col[a]))
    return flagged


def f1(det, actual):
    tp = len(det & actual)
    p = tp / len(det) if det else 0.0
    r = tp / len(actual) if actual else 0.0
    return 2 * p * r / (p + r) if p + r else 0.0


for run in sys.argv[1:]:
    d = 'reports/robustness/runs/' + run
    dirty = list(csv.reader(open(d + '/dirty.csv')))[1:]
    actual = {(int(a), int(b)) for a, b, *_ in csv.reader(open(d + '/actual_errors.csv'))}
    try:
        stored = {(int(a), int(b)) for a, b, *_ in csv.reader(open(d + '/detections.csv'))}
    except FileNotFoundError:
        stored = None
    det = detect(dirty)
    inj = [(i, j) for (i, j) in actual if dirty[i][j] != '']
    domain = [{r[j] for r in clean} for j in range(len(H))]
    existing = {(i, j) for (i, j) in inj if dirty[i][j] in domain[j]}
    counts = {}
    for i, j in inj:
        counts[(j, dirty[i][j])] = counts.get((j, dirty[i][j]), 0) + 1
    injected = {(i, j) for (i, j) in inj if (i, j) not in existing and counts[(j, dirty[i][j])] > 1}

    def unique(cells):
        rows = [list(r) for r in dirty]
        for k, (i, j) in enumerate(sorted(cells)):
            rows[i][j] = '__unique_%d' % k
        return detect(rows)

    print('%s: replication %s (%d flagged) | F1 %.3f | existing-value coincidences %d -> F1 %.3f | '
          'injected-injected coincidences %d -> F1 %.3f | all injected unique -> F1 %.3f' % (
              run, 'exact' if stored is None or det == stored else 'DIFFERS', len(det), f1(det, actual),
              len(existing), f1(unique(existing), actual), len(injected), f1(unique(injected), actual),
              f1(unique(set(inj)), actual)))
