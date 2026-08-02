import logging
import time

import pandas as pd

from ..dataset import AuxTables

 
class DetectEngine:
    def __init__(self, env, dataset):
        self.env = env
        self.ds = dataset

    def detect_errors(self, detectors):
        """
        Detects errors using a list of detectors.
        :param detectors: (list) of ErrorDetector objects
        """
        errors = []
        tic_total = time.time()

        # Initialize all error detectors.
        for detector in detectors:
            detector.setup(self.ds, self.env)

        # Run detection using each detector.
        for detector in detectors:
            tic = time.time()
            error_df = detector.detect_noisy_cells()
            toc = time.time()
            logging.debug("DONE with Error Detector: %s in %.2f secs", detector.name, toc-tic)
            errors.append(error_df)

        # Get unique errors only that might have been detected from multiple detectors.
        errors_df = pd.concat(errors, ignore_index=True).drop_duplicates().reset_index(drop=True)
        if errors_df.empty:
            # apply(axis=1) on an empty frame yields 0 items, and assigning that to a new
            # column raises "Wrong number of items passed 0, placement implies 1". A run
            # whose constraints simply never fire is a legitimate result, not an error.
            errors_df['_cid_'] = pd.Series(dtype='int64')
        else:
            errors_df['_cid_'] = errors_df.apply(lambda x: self.ds.get_cell_id(x['_tid_'], x['attribute']), axis=1)
        logging.info("detected %d potentially erroneous cells", errors_df.shape[0])

        # Store errors to db.
        # error_df.to_csv("/home/chrha/Desktop/holoclean_examples/error_df1.csv", index=False, encoding="utf-8")
        self.store_detected_errors(errors_df)
        status = "DONE with error detection."
        toc_total = time.time()
        detect_time = toc_total - tic_total
        return status, detect_time, errors_df
 
    def store_detected_errors(self, errors_df):
        if errors_df.empty:
            # Zero violations is a valid outcome (e.g. every DC holds on the data). Warn
            # and skip the aux table rather than aborting the whole detection run.
            logging.warning("Detected errors dataframe is empty - no cells flagged by any detector.")
            return
        self.ds.generate_aux_table(AuxTables.dk_cells, errors_df, store=True)
        self.ds.aux_table[AuxTables.dk_cells].create_db_index(self.ds.engine, ['_cid_'])

