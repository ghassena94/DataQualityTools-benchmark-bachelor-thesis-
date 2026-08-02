####################################################
# Benchmark: script for generating FD rules via the FDX profiler (tools/Profiler)
####################################################

import argparse
import os

from profiler.core import *

from rein.auxiliaries.datasets_dictionary import datasets_dictionary
from rein.datasets import Datasets

####################################################


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_name', default='beers')
    args = parser.parse_args()

    dataset_name = args.dataset_name

    if dataset_name not in datasets_dictionary:
        raise ValueError(f"Dataset {dataset_name} is not known.")

    app = Datasets(datasets_dictionary[dataset_name])

    # Same sequence as Datasets.generate_fd_rules() (rein/datasets.py), but with
    # an explicit absolute write_to so the output lands in the dataset directory
    # instead of the process's current working directory.
    pf = Profiler(workers=2, tol=0, eps=0.05, embedtxt=True)

    pf.session.load_data(name=dataset_name, src=DF, df=app.groundTruthDF, check_param=True, na_values='empty')

    embeddings_path = os.path.abspath(os.path.join(app.dataset_path, "embeddings"))
    store_load = [False, True] if os.path.exists(embeddings_path) else [True, False]
    pf.session.load_embedding(save=store_load[0], path=embeddings_path, load=store_load[1])

    pf.session.load_training_data(multiplier=None, difference=True)

    pf.session.learn_structure(sparsity=0, infer_order=True)

    write_to = os.path.join(app.dataset_path, f"{dataset_name}_FDs")
    pf.session.get_dependencies(score="fit_error", write_to=write_to)

    print(f"FD rules written to {write_to}_by_col.txt")
