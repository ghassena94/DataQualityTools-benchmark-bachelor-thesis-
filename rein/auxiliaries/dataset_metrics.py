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
    row_baseline= (2*fraction_dirty_rows)/(1+fraction_dirty_rows)
    rousseeuw_prediction = 1-(1-error_rate)**d

    #define the toReturn datasetMetrics_dict
    datasetMetrics_dict={
        "cell_error_rate": error_rate,
        "dataset_dimension": d , 
        "rows_number": N,
        "error_columns": error_colums,
        "fraction_dirty_rows": fraction_dirty_rows, 
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
        "   row_baseline                    {:>12.4f}".format(metrics["row_baseline"]),
        "   Rousseeuw prediction          {:>12.4f}".format(metrics["rousseeuw_prediction"]),
        "-" * 56,
    ])