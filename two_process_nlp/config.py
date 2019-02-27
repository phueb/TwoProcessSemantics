from pathlib import Path


class Dirs:
    root = Path(__file__).parent.parent
    src = root / 'two_process_nlp'
    tasks = root / 'tasks'
    corpora = root / 'corpora'
    local_runs = root / '{}_runs'.format(src.name)
    #
    remote_root = Path('/') / 'media' / 'lab' / '2StageNLP'
    remote_runs = remote_root / 'runs'


class Eval:
    debug = False   # catches tensorflow errors properly
    only_process1 = False
    shuffled_control = False
    resample = False
    verbose = True
    num_processes = 4  # if too high (e.g. 8) doesn't result in speed-up (4 is sweet spot, 3x speedup) on 8-core machine
    max_num_eval_rows = 600  # 1200x1200 uses over 32GB RAM
    max_num_eval_cols = 600  # 600  # should be as large as num_rows for full matching evaluation
    standardize_num_relata = False  # don't do this - it reduces performance dramatically
    only_negative_examples = False
    num_folds = 4
    num_opt_steps = 5
    num_evals = 10
    matching_metric = 'BalAcc'
    remove_duplicates_for_identification = False  # needs to be False to get above chance


class Embeddings:
    save_w2e = True
    verbose = True
    precision = 5


class Corpus:
    UNK = 'UNKNOWN'
    name = 'childes-20180319'
    # name = 'tasa-20181213'
    num_vocab = 4096
    vocab_sizes = [4096]  # also: 8192, 16384


class Glove:
    num_threads = 8