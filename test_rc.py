import numpy as np

from src import config
from src.architectures import comparator
from src.evaluators.matching import Matching
from src.embedders.base import w2e_to_sims

config.Eval.save_scores = False
config.Eval.only_negative_examples = False
config.Eval.matching_metric = 'CohensKappa'  # 'BalAcc'

LOAD_DUMMY_DATA = True
DATA_NAME1 = 'cohyponyms'
DATA_NAME2 = 'semantic'

EMBED_SIZE = 200
NUM_CATS = 30  # divide NUM_PROBES equally
NUM_PROBES = 600  # needs to be more than mb_size
NUM_RELATA = 600  # a smaller number than vocab size increases probability of reusing relata across probes
MIN_NUM_RELATA = 4  # this also changes prob of pos examples
MAX_NUM_RELATA = 50  # this also changes prob of pos examples
UNIFORM_RELATA_PROBS = False
PROBES_AS_RELATA = False

VERBOSE = True


def load_probes():
    data_dir = '{}/{}'.format(DATA_NAME1, DATA_NAME2) if DATA_NAME2 is not None else DATA_NAME1
    p = config.Dirs.tasks / data_dir / '{}_{}.txt'.format(
        config.Corpus.name, config.Corpus.num_vocab)
    probes = []
    probe_relata = []
    with p.open('r') as f:
        for line in f.read().splitlines():
            spl = line.split()
            probe = spl[0]
            relata = spl[1:]
            probes.append(probe)
            probe_relata.append(relata)
    return probes, probe_relata


class MatchingParams:
    prop_negative = [None]  # 0.3 is better than 0.1 or 0.2 but not 0.5
    # arch-evaluator interaction
    num_epochs = [100]  # 100 is better than 10 or 20 or 50


class RandomControlEmbedderDummy():
    def __init__(self, embed_size, vocab):
        self.embed_size = embed_size
        self.dim1 = embed_size
        self.vocab = vocab
        self.w2e = self.make_w2e()
        #
        self.name = 'random_control'
        self.time_of_init = 'test'

    def make_w2e(self):
        return {w: np.random.normal(-1.0, 1.0, self.embed_size) for w in self.vocab}


# embedder
p = config.Dirs.corpora / '{}_vocab.txt'.format(config.Corpus.name)
vocab = np.loadtxt(p, 'str')
embedder = RandomControlEmbedderDummy(EMBED_SIZE, vocab)

# probes + relata
if LOAD_DUMMY_DATA:
    print('LOADING DUMMY DATA')
    probes = np.random.choice(vocab, size=NUM_PROBES, replace=False).tolist()
    #
    if NUM_CATS is not None:
        print('Splitting dummy data into {} categories'.format(NUM_CATS))
        cat_sizes = np.random.randint(MIN_NUM_RELATA, MAX_NUM_RELATA + 1, size=NUM_CATS)
        probe_relata = []
        idx = 0
        probe_it = iter(probes)
        if PROBES_AS_RELATA:
            relata = probes
        else:
            relata = np.random.choice(vocab, size=NUM_PROBES, replace=False).tolist()
        for cs in cat_sizes:
            cat_relata = relata[idx: idx + cs]
            if len(cat_relata) == 0:
                continue
            idx += cs
            #
            for _ in range(cs):
                try:
                    probe = next(probe_it)
                except StopIteration:
                    break
                probe_relata.append([r for r in cat_relata if r != probe])
    else:
        relata = np.random.choice(vocab, size=NUM_RELATA, replace=False).tolist()
        if UNIFORM_RELATA_PROBS:
            from_vocab_probs = None
        else:
            num_rv = len(relata)
            logits = np.logspace(0, 1, num=num_rv)
            from_vocab_probs = logits / logits.sum()
        probe_relata = [np.random.choice(relata,
                                         size=np.random.randint(MIN_NUM_RELATA, MAX_NUM_RELATA + 1, size=1),
                                         replace=False,
                                         p=from_vocab_probs) for _ in range(NUM_PROBES)]
else:
    print('LOADING REAL DATA')
    probes, probe_relata = load_probes()
    # np.random.shuffle(probes)  # this abolishes above-chance performance


if VERBOSE:
    for p, pr, in zip(probes, probe_relata):
        print(p, len(pr), pr)
    raise SystemExit

# all_eval_probes + all_eval_candidates_mat
relata = sorted(np.unique(np.concatenate(probe_relata)))
all_eval_probes = probes
num_eval_probes = len(all_eval_probes)
all_eval_candidates_mat = np.asarray([relata for _ in range(num_eval_probes)])

# ev
ev = Matching(comparator, 'cohyponyms', 'semantic', matching_params=MatchingParams)
ev.probe2relata = {p: r for p, r in zip(probes, probe_relata)}

# prepare data
ev.row_words, ev.col_words, ev.eval_candidates_mat = ev.downsample(
    all_eval_probes, all_eval_candidates_mat, rep_id=0)
print('Shape of all eval data={}'.format(all_eval_candidates_mat.shape))
print('Shape of down-sampled eval data={}'.format(ev.eval_candidates_mat.shape))
ev.pos_prob = ev.calc_pos_prob()

# score
sims_mat = w2e_to_sims(embedder.w2e, ev.row_words, ev.col_words)  # sims can have duplicate rows
ev.score_novice(sims_mat)
ev.train_and_score_expert(embedder, rep_id=0)