import os
from pathlib import Path


class Dirs:
    tasks = Path(os.getenv('TASKS_DIR', Path(__file__).parent.parent / 'tasks'))
    corpora = Path(os.getenv('CORPORA_DIR', Path(__file__).parent.parent / 'corpora'))
    runs = Path(os.getenv('RUNS_DIR', Path(__file__).parent.parent / 'runs'))
    categories = Path(os.getenv('CATEGORIES_DIR', Path(__file__).parent.parent / 'categories'))


class Eval:
    debug = False   # catches tensorflow errors properly
    num_processes = 2  # too high (e.g. 8) doesn't result in speed-up (4 is sweet spot, 3x speedup) on 8-core machine
    max_num_eval_rows = 600
    max_num_eval_cols = 600  # 600  # should be as large as num_rows for full matching evaluation
    standardize_num_relata = False  # don't do this - it reduces performance dramatically
    only_negative_examples = False
    num_reps = 2
    num_folds = 4
    vocab_sizes = [4096, 8192, 16384]
    retrain = False
    save_scores = True
    save_figs = False
    num_opt_steps = 5
    device = 'cpu'  # gpu is faster only above mini batch sizes of 1024 (embed_size=200) - no performance gain
    num_evals = 10
    matching_metric = 'BalAcc'
    remove_duplicates_for_identification = False  # needs to be False to get above chance


class Embeddings:
    precision = 5
    retrain = False
    save = True
    sim_method = 'cosine'


class Corpus:
    spacy_batch_size = 50  # doesn't seem to affect speed loading childes-20180319
    UNK = 'UNKNOWN'
    # name = 'childes-20180319'  # TODO testing TASA
    name = 'tasa'
    num_vocab = 4096


class Figs:
    width = 7
    dpi = 196
    axlabel_fontsize = 12
    line_width = 2
    # hypernym_identification
    softmax_criterion = 0.5
    num_bins = 10
    num_diagnosticity_steps = 50


class Glove:
    num_threads = 8