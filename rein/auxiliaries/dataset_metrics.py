# compute dataset baseliine metrics
# contains two functions 
# one that computes the metrics and the other do formats 



from nt import error


def compute_dataset_metrics(actual_errors, N, d, error_rate):
    

    
    # R_true stores erroneous rows  
    R_True = set()
    d_error = set()
    for (i,j) in actual_errors: 
        R_True.add(i)
        d_error.add(j)

    fraction_dirty_rows= len(R_True)/ N 
    error_colums = len(d_error)

    rousseeuw_prediction = 1-(1-error_rate)**d

    #define the toReturn datasetMetrics_dict
    datasetMetrics_dict={
        "cell_error_rate": error_rate,
        "dataset_dimension": d , 
        "rows_number": N,
        "error_columns": error_colums,
        "fraction_dirty_rows": fraction_dirty_rows, 
        "rousseeuw_prediction": rousseeuw_prediction

    }

    return datasetMetrics_dict

