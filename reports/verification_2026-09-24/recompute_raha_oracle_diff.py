"""Run inside the container: docker compose run --rm -T rein python3 - < this_file
Recomputes Raha's own label oracle (raha.dataset.Dataset.get_actual_errors_dictionary) and compares it with actual_errors.csv."""
import csv, json, collections
import numpy, raha
base = "/rein/datasets"
def feq(a, b):
    try: return float(a) == float(b)
    except Exception: return False
for name in ["nasa", "bike", "smartfactory", "breast_cancer", "beers", "soilmoisture", "adult"]:
    d = raha.dataset.Dataset({"name": name, "path": f"{base}/{name}/dirty.csv", "clean_path": f"{base}/{name}/clean.csv"})
    diff = d.get_actual_errors_dictionary()
    gt = set()
    for row in csv.reader(open(f"{base}/{name}/actual_errors.csv")):
        try: gt.add((int(row[0]), int(row[1])))
        except Exception: pass
    dcols, ccols = list(d.dataframe.columns), list(d.clean_dataframe.columns)
    extras = [c for c in diff if c not in gt]
    fmt = set(c for c in extras if feq(d.dataframe.iat[c[0], c[1]], d.clean_dataframe.iat[c[0], c[1]]))
    rec = dict(rows=int(d.dataframe.shape[0]), cols=int(d.dataframe.shape[1]), header_equal=dcols == ccols, header_same_set=set(dcols) == set(ccols),
               n_diff=len(diff), n_gt=len(gt), n_intersection=len(diff) - len(extras), n_extra=len(extras), n_extra_float_equal=len(fmt),
               n_extra_other=len(extras) - len(fmt), n_gt_missing_from_diff=len([c for c in gt if c not in diff]),
               extra_by_column=dict(collections.Counter(dcols[j] for _, j in extras).most_common(4)),
               examples=[(dcols[j], d.dataframe.iat[i, j], d.clean_dataframe.iat[i, j]) for i, j in sorted(extras)[:3]])
    if dcols != ccols and set(dcols) == set(ccols):
        aligned = d.clean_dataframe[dcols]
        mask = d.dataframe.values != aligned.values
        cells = set(zip(*[a.tolist() for a in numpy.where(mask)]))
        rec["after_name_alignment"] = dict(n_diff=int(mask.sum()), n_intersection=len(cells & gt), n_extra=len(cells - gt))
    print(json.dumps({name: rec}, default=str), flush=True)
