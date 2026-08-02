from ml.datasets.DataSet import DataSet


class SpecificDataset(DataSet):
    """Adapter for datasets whose dirty/clean frames are supplied by the caller.

    Upstream ED2 ships one DataSet subclass per benchmark dataset (e.g.
    ml/datasets/flights/FlightHoloClean.py); each loads its own CSVs and then
    calls DataSet.__init__(name, dirty_pd, clean_pd). REIN instead loads both
    frames itself (rein/detectors.py:2045 for clean.csv, rein/benchmark.py for
    the dirty frame) and hands them in, so no behaviour beyond DataSet is
    needed here.

    DataSet computes matrix_is_error as dirty_pd.values != clean_pd.values and
    DataSetBasic derives shape/is_column_applicable/get_applicable_columns from
    it, which is the full interface ml/classes and ml/active_learning consume.
    """

    def __init__(self, name, dirty_pd, clean_pd):
        super(SpecificDataset, self).__init__(name, dirty_pd, clean_pd)
