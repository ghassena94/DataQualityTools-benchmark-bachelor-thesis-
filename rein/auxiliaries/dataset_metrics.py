# compute dataset baseliine metrics
# contains two functions 
# one that computes the metrics and the other do formats 


def compute_dataset_metrics(actual_errors, N, d, error_rate):
    """
    calculate dataset metrics

    Arguments: 
    - actual_errors: dataset actual_errors
    - N number of cases/rows in the data fraction
    - d datafraction dimensions 
    - error_rate: error rate in json file 

    Returns: 
    a datasetMetrics dictionary 
    """

    
    # R_true stores erroneous rows  
    R_True = set()
    d_error = set()
    for (i,j) in actual_errors: 
        R_True.add(i)
        d_error.add(j)

    fraction_dirty_rows= len(R_True)/ N 
    error_colums = len(d_error)
    cell_baseline= (2*error_rate)/(1+error_rate)
    row_baseline= (2*fraction_dirty_rows)/(1+fraction_dirty_rows)
    rousseeuw_prediction = 1-(1-error_rate)**d

    #define the toReturn datasetMetrics_dict
    datasetMetrics_dict={
        "cell_error_rate": error_rate,
        "dataset_dimension": d , 
        "rows_number": N,
        "error_columns": error_colums,
        "fraction_dirty_rows": fraction_dirty_rows, 
        "cell_baseline": cell_baseline,
        "row_baseline": row_baseline,
        "rousseeuw_prediction": rousseeuw_prediction

    }

    return datasetMetrics_dict


def format_dataset_metrics(dataset_name, metrics):
    """
    Renders the dataset metrics as a table for the log file.

    Arguments:
    dataset_name: name of the dataset being described
    metrics: output of compute_dataset_metrics()

    Returns:
    String: multi-line table
    """
    header = "--- Dataset metrics: {} ".format(dataset_name)

    return "\n".join([
        "",
        header + "-" * max(0, 56 - len(header)),
        "   rows (N)                      {:>12}".format(metrics["rows_number"]),
        "   dimension (d)                 {:>12}".format(metrics["dataset_dimension"]),
        "   columns with errors (d_err)   {:>12}".format(metrics["error_columns"]),
        "   cell error rate (eps)         {:>12.4f}".format(metrics["cell_error_rate"]),
        "   observed dirty row fraction   {:>12.4f}".format(metrics["fraction_dirty_rows"]),
        "   cell_baseline                  {:>12.4f}".format(metrics["cell_baseline"]),
        "   row_baseline                  {:>12.4f}".format(metrics["row_baseline"]),
        "   Rousseeuw prediction          {:>12.4f}".format(metrics["rousseeuw_prediction"]),
        "-" * 56,
    ])


def format_expectation_breakdown(dataset_name, tier, per_rule, actual_errors, n_rows):
    """
    Renders a per-expectation breakdown of a greatExpectations suite for the log.

    A suite reports one F1, and that number reads as a property of the suite. It
    usually is not: on most datasets a couple of rules carry nearly all of the
    score and the rest fire on nothing. This table says which is which, so a
    reader can tell a suite that works from a suite with one lucky rule in it.

    Columns:
      cells   how many cells this rule flagged on its own
      TP/FP   of those, how many were real errors and how many were not
      new     cells this rule contributed that no earlier rule had flagged
      newTP   of those new cells, how many were real errors -- this is the
              rule's actual marginal contribution to the suite's recall
      %rows   cells as a fraction of the row count, i.e. how much of its column
              the rule rejected. A rule near 100% is flagging the whole column
              rather than picking cells out of it.

    Arguments:
    dataset_name: name of the dataset being checked
    tier: which expectation tier produced the suite (dirty_profiled, clean_profiled, hand_written)
    per_rule: list of (column, expectation, kwargs, cells) as produced by the
        detector, in the order the rules were applied
    actual_errors: the ground truth dictionary, keyed by (row, column) cell
    n_rows: row count of the dirty frame, used for the %rows column

    Returns:
    String: multi-line table
    """
    truth = set(actual_errors)
    header = "--- greatExpectations:{} per-expectation breakdown: {} ".format(tier, dataset_name)
    lines = ["", header + "-" * max(0, 104 - len(header)),
             "   {:<26}{:<38}{:>7}{:>7}{:>7}{:>7}{:>7}{:>8}".format(
                 "column", "expectation", "cells", "TP", "FP", "new", "newTP", "%rows")]

    seen = set()
    silent, whole_column = [], []
    for column, expectation, kwargs, cells in per_rule:
        new = cells - seen
        seen |= cells
        tp = len(cells & truth)
        rule = expectation.replace("expect_column_values_", "")
        regex = kwargs.get("regex")
        if regex is not None:
            rule = "{} {}".format(rule, regex)
        if not cells:
            silent.append(column)
        if n_rows and len(cells) >= 0.99 * n_rows:
            whole_column.append(column)
        lines.append("   {:<26}{:<38}{:>7}{:>7}{:>7}{:>7}{:>7}{:>8}".format(
            column[:25], rule[:37], len(cells), tp, len(cells) - tp,
            len(new), len(new & truth),
            "{:.1%}".format(len(cells) / n_rows) if n_rows else "-"))

    lines.append("-" * 104)
    if silent:
        lines.append("   {} of {} rule(s) flagged nothing: {}".format(
            len(silent), len(per_rule), ", ".join(sorted(set(silent))[:12])
            + (" ..." if len(set(silent)) > 12 else "")))
    if whole_column:
        lines.append("   {} rule(s) rejected >=99% of their column, i.e. flagged the "
                     "column rather than cells in it: {}".format(
                         len(whole_column), ", ".join(sorted(set(whole_column))[:12])
                         + (" ..." if len(set(whole_column)) > 12 else "")))
    lines.append("")
    return "\n".join(lines)


def format_constraint_breakdown(dataset_name, constraints, dirtydf, actual_errors):
    """
    Renders a per-denial-constraint breakdown of a HoloClean run for the log.

    HoloClean reports one F1 for a whole constraint set, and that number reads as
    a property of HoloClean. On beers it is not: with all three constraints the
    set scores 0.5022, with the first one removed it scores 0.0566, so the gap is
    measuring one constraint rather than the tool. This table answers that
    question for every dataset, in the log, without a hand-run ablation.

    HoloClean returns one de-duplicated cell set, so which constraint produced
    which cell cannot be recovered from its output. Each constraint's own
    footprint is therefore recomputed here with the ViolationDetector's exact
    semantics (cleaners/holoclean/detect/violationdetector.py): group by the EQ
    columns, and where a group holds more than one distinct value of the IQ
    column, every row in that group violates and *every* attribute the constraint
    names -- the EQ columns as well as the IQ column -- is flagged for it. The
    numbers below are exact, not an attribution of HoloClean's merged output.

    That "every attribute it names" is the part worth watching. A constraint
    whose EQ column has few distinct values flags its whole columns rather than
    cells within them, which is what %rows exposes.

    Arguments:
    dataset_name: name of the dataset being checked
    constraints: the parsed DenialConstraint objects, in file order
    dirtydf: the dirty frame the detector ran on
    actual_errors: the ground truth dictionary, keyed by (row, column) cell

    Returns:
    String: multi-line table
    """
    truth = set(actual_errors)
    n_rows, n_columns = dirtydf.shape
    header = "--- HoloClean per-constraint breakdown: {} ".format(dataset_name)
    lines = ["", header + "-" * max(0, 104 - len(header))]

    if not constraints:
        lines += ["   No denial constraints loaded for this dataset, so the "
                  "ViolationDetector has nothing to violate.",
                  "   Its 0.0000 is the absence of a constraint set, not a "
                  "measurement of HoloClean.", "-" * 104, ""]
        return "\n".join(lines)

    def cells_of(constraint):
        eq = [p.components[0][1] for p in constraint.predicates if p.operation == '=']
        iq = [p.components[0][1] for p in constraint.predicates if p.operation == '<>']
        if not eq or not iq or any(c not in dirtydf.columns for c in eq + iq):
            return [], iq, set(), set()
        distinct = dirtydf.groupby(eq, sort=False, dropna=False)[iq[0]].transform('nunique')
        rows = set(dirtydf.index[distinct > 1])
        positions = [dirtydf.columns.get_loc(c) for c in eq + iq]
        return eq, iq, rows, {(r, c) for r in rows for c in positions}

    footprints = [cells_of(c) for c in constraints]
    everything = set().union(*[f[3] for f in footprints]) if footprints else set()

    def f1_of(predicted):
        tp = len(predicted & truth)
        precision = tp / len(predicted) if predicted else 0.0
        recall = tp / len(truth) if truth else 0.0
        return 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    full_f1 = f1_of(everything)
    error_rate = len(truth) / (n_rows * n_columns) if n_rows and n_columns else 0.0
    cell_baseline = 2 * error_rate / (1 + error_rate) if error_rate else 0.0

    lines.append("   {:<4}{:<46}{:>8}{:>7}{:>7}{:>8}{:>9}{:>8}".format(
        "k", "constraint (EQ columns -> IQ column)", "cells", "TP", "FP",
        "%rows", "dF1", "uniqTP"))
    for index, (eq, iq, rows, cells) in enumerate(footprints, 1):
        others = set().union(*[f[3] for j, f in enumerate(footprints) if j != index - 1]) \
            if len(footprints) > 1 else set()
        label = "{} -> {}".format(",".join(eq), ",".join(iq))
        lines.append("   {:<4}{:<46}{:>8}{:>7}{:>7}{:>8}{:>9}{:>8}".format(
            index, label[:45], len(cells), len(cells & truth),
            len(cells) - len(cells & truth),
            "{:.1%}".format(len(rows) / n_rows) if n_rows else "-",
            "{:+.4f}".format(full_f1 - f1_of(others)),
            len((cells - others) & truth)))

    lines.append("-" * 104)
    lines.append("   all {} constraint(s): F1={:.4f}, flagging {:.1%} of the table. "
                 "cell_baseline={:.4f} ({:+.4f}).".format(
                     len(constraints), full_f1, len(everything) / (n_rows * n_columns)
                     if n_rows and n_columns else 0.0, cell_baseline,
                     full_f1 - cell_baseline))
    lines.append("   dF1 = F1(all) - F1(all except this one): how much of the score "
                 "this one constraint carries.")
    lines.append("   uniqTP = true errors this constraint is the only one to flag. "
                 "%rows = share of rows it flags,")
    lines.append("   and every attribute it names is flagged for each of them, so "
                 "%rows near 100% means it is")
    lines.append("   rejecting whole columns rather than picking cells out of them.")
    lines.append("")
    return "\n".join(lines)
