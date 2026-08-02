####################################################
# Benchmark: convert learned FDs into HoloClean denial constraints (DCs)
#
# Reads  datasets/<name>/<name>_FDs_by_col.txt  (produced by
# scripts/generate_fd_rules.py, each line "LHS -> RHS\t# score=...")
# and writes datasets/<name>/constraints/<name>_dcs.txt in HoloClean's
# DC syntax.
#
# An FD "A,B -> C" becomes the denial constraint
#     t1&t2&EQ(t1.A,t2.A)&EQ(t1.B,t2.B)&IQ(t1.C,t2.C)
# i.e. "no two distinct tuples may agree on A and B yet disagree on C".
#
# "Useful" filtering: any FD whose LHS contains a (near-)unique column
# (uniqueness ratio >= --uniq_thresh on the ground-truth data -- this
# catches index / Index / Unnamed: 0 / unique-id columns) is dropped.
# EQ() on a near-unique column can only hold when t1 and t2 are the same
# row, so such a DC can never detect a real violation. This reproduces
# the hand-curated beers_dcs.txt exactly. Additionally, a column named
# "index" is always dropped because dcHoloCleaner removes it before
# loading, so a DC referencing it would fail schema validation.
####################################################

import argparse
import os

import pandas as pd

from rein.auxiliaries.datasets_dictionary import datasets_dictionary


def parse_fd_line(line):
    """'LHS,LHS2 -> RHS\t# score=0.12' -> (['LHS','LHS2'], 'RHS', '0.12') or None."""
    line = line.strip()
    if not line or line.startswith('#') or '->' not in line:
        return None
    fd_part, _, score_part = line.partition('#')
    lhs_str, _, rhs = fd_part.split('->')[0], '->', fd_part.split('->', 1)[1]
    lhs = [c.strip() for c in lhs_str.split(',') if c.strip()]
    rhs = rhs.strip()
    score = score_part.replace('score=', '').strip() if score_part else 'n/a'
    return lhs, rhs, score


def fd_to_dc(lhs, rhs):
    eq = "&".join("EQ(t1.{c},t2.{c})".format(c=c) for c in lhs)
    return "t1&t2&{eq}&IQ(t1.{r},t2.{r})".format(eq=eq, r=rhs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_name', default='beers')
    parser.add_argument('--uniq_thresh', type=float, default=0.9,
                        help='drop FDs whose LHS has a column with uniqueness ratio >= this')
    args = parser.parse_args()

    ds = args.dataset_name
    if ds not in datasets_dictionary:
        raise ValueError("Dataset {} is not known.".format(ds))

    dataset_path = datasets_dictionary[ds]["dataset_path"]
    fd_path = os.path.join(dataset_path, "{}_FDs_by_col.txt".format(ds))
    if not os.path.exists(fd_path):
        print("No FD file for {} ({}); nothing to convert.".format(ds, fd_path))
        raise SystemExit(0)

    gt = pd.read_csv(datasets_dictionary[ds]["groundTruth_path"])
    n = max(len(gt), 1)
    uniq_ratio = {col: gt[col].nunique(dropna=True) / n for col in gt.columns}

    def near_unique(col):
        # Unknown columns (not in GT) are treated as safe (keep).
        return col == "index" or uniq_ratio.get(col, 0.0) >= args.uniq_thresh

    kept, dropped = [], []
    with open(fd_path) as f:
        for line in f:
            parsed = parse_fd_line(line)
            if parsed is None:
                continue
            lhs, rhs, score = parsed
            bad = [c for c in lhs if near_unique(c)]
            if bad:
                dropped.append((lhs, rhs, score, bad))
            else:
                kept.append((lhs, rhs, score))

    if not kept:
        print("{}: 0 useful DCs after filtering ({} FDs dropped). "
              "No constraints file written.".format(ds, len(dropped)))
        raise SystemExit(0)

    out_dir = os.path.join(dataset_path, "constraints")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "{}_dcs.txt".format(ds))
    with open(out_path, 'w') as out:
        out.write("# Denial constraints derived from FDs learned by the FDX profiler\n")
        out.write("# (scripts/generate_fd_rules.py -> {}_FDs_by_col.txt), converted by\n".format(ds))
        out.write("# scripts/fds_to_dcs.py. FD 'A,B -> C' becomes:\n")
        out.write("#   t1&t2&EQ(t1.A,t2.A)&EQ(t1.B,t2.B)&IQ(t1.C,t2.C)\n")
        out.write("# {} FD(s) dropped: LHS contained a (near-)unique column "
                  "(uniqueness >= {}), whose EQ() can never match two distinct "
                  "rows.\n".format(len(dropped), args.uniq_thresh))
        out.write("# fit_error score: lower = FD holds cleanly (few violations).\n\n")
        for lhs, rhs, score in kept:
            out.write("# FD: {} -> {}  (fit_error={})\n".format(",".join(lhs), rhs, score))
            out.write(fd_to_dc(lhs, rhs) + "\n")

    print("{}: wrote {} DC(s) to {} ({} FD(s) dropped as near-unique).".format(
        ds, len(kept), out_path, len(dropped)))
