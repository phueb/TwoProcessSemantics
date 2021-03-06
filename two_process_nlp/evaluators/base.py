import multiprocessing as mp
import numpy as np
import sys
from sortedcontainers import SortedDict
from sklearn import preprocessing

from two_process_nlp import config
from two_process_nlp.params import make_param2val_list, ObjectView


class ResultsData:
    def __init__(self, params_id, evaluator, embed_size):
        self.params_id = params_id
        self.eval_sims_mats = [np.full_like(evaluator.eval_candidates_mat, np.nan, dtype=float)
                               for _ in range(config.Eval.num_evals)]
        self.process2_embed_mats = [np.zeros((len(evaluator.row_words + config.Eval.tertiary_probes), embed_size))
                        for _ in range(config.Eval.num_evals)]


class Trial(object):
    def __init__(self, params_id, param2val):
        self.params_id = params_id
        self.params = ObjectView(param2val)
        self.df_row = None
        self.results = None


class EvalBase(object):
    def __init__(self,
                 arch_name,
                 arch_params,
                 init_results_data,
                 split_and_vectorize_eval_data,
                 make_graph,
                 train_expert_on_train_fold,
                 train_expert_on_test_fold,
                 name, data_name1, data_name2, suffix,
                 ev_params_class):
        # pass functions separately because module cannot be pickled (which multiprocessing requires)
        self.init_results_data = init_results_data
        self.split_and_vectorize_eval_data = split_and_vectorize_eval_data
        self.make_graph = make_graph
        self.train_expert_on_train_fold = train_expert_on_train_fold
        self.train_expert_on_test_fold = train_expert_on_test_fold
        #
        self.arch_name = arch_name
        self.name = name
        self.data_name1 = data_name1
        self.data_name2 = data_name2
        self.suffix = suffix
        self.full_name = '{}_{}_{}{}'.format(
            arch_name, self.name, data_name1, data_name2 if data_name2 is '' else '_' + data_name2)
        #
        self.param2val_list = make_param2val_list(arch_params, ev_params_class)
        self.trials = [Trial(n, param2val)
                       for n, param2val in enumerate(self.param2val_list)]
        merged_keys = set(list(arch_params.__dict__.keys()) + list(ev_params_class.__dict__.keys()))
        self.df_header = sorted([k for k in merged_keys if not k.startswith('_')])
        #
        self.num_epochs_in_eval_step = None
        self.probe2relata = None
        self.row_words = None
        self.col_words = None
        self.eval_candidates_mat = None
        self.pos_prob = None

    @property
    def data_name(self):
        res = '{}{}{}'.format(self.data_name1,
                              self.data_name2 if self.data_name2 is '' else '_' + self.data_name2,
                              self.suffix)
        return res

    # ////////////////////////////////////////////////////// evaluator-specific

    def make_all_eval_data(self, vocab_sims_mat, vocab):
        raise NotImplementedError('Must be implemented in child-class.')

    def check_negative_example(self, trial, p=None, c=None):
        raise NotImplementedError('Must be implemented in child-class.')

    def score(self, eval_sims_mat):
        raise NotImplementedError('Must be implemented in child-class.')

    def print_score(self, expert_score, eval_id=None):
        raise NotImplementedError('Must be implemented in child-class.')

    def to_eval_sims_mat(self, sims_mat):
        raise NotImplementedError('Must be implemented in child-class.')

    # //////////////////////////////////////////////////////

    def downsample(self, all_eval_probes, all_eval_candidates_mat):
        # shuffle + down sample rows & cols
        if not config.Eval.resample:
            np.random.seed(42)
        num_all_rows = len(all_eval_candidates_mat)
        min_num_all_rows = min(num_all_rows, config.Eval.max_num_eval_rows) if self.name == 'matching' else num_all_rows
        row_words = []
        eval_candidates_mat = []
        for rnd_id in np.random.choice(np.arange(min_num_all_rows), size=min_num_all_rows, replace=False):
            row_words.append(all_eval_probes[rnd_id])
            eval_candidates_mat.append(all_eval_candidates_mat[rnd_id, :config.Eval.max_num_eval_cols])
        eval_candidates_mat = np.vstack(eval_candidates_mat)
        col_words = sorted(np.unique(eval_candidates_mat).tolist())
        return row_words, col_words, eval_candidates_mat

    def make_p(self, embedder_location, process, fname):
        res = embedder_location / self.arch_name / self.name / self.data_name / process / fname
        if not res.parent.exists():
            res.parent.mkdir(parents=True)
        return res

    def calc_pos_prob(self):
        num_positive = 0
        num_total = self.eval_candidates_mat.size
        for row_word, candidates in zip(self.row_words, self.eval_candidates_mat):
            for c in candidates:
                if c in self.probe2relata[row_word]:
                    num_positive += 1
        prob = num_positive / num_total
        if config.Eval.verbose:
            print('Probability of positive examples={}'.format(prob))
        return prob

    # ////////////////////////////////////////////////////// train + score

    def score_novice(self, sims_mat):
        eval_sims_mat = self.to_eval_sims_mat(sims_mat)
        novice_score = self.score(eval_sims_mat)
        if config.Eval.verbose:
            self.print_score(novice_score)
        return [[novice_score] + [np.nan for _ in self.df_header] + [np.nan for _ in ['num_epochs']]]

    def train_and_score_expert(self, embedder, shuffled):
        # run each trial in separate process
        print('Training expert on "{}"'.format(self.full_name))
        pool = mp.Pool(processes=config.Eval.num_processes if not config.Eval.debug else 1)
        if config.Eval.debug:  # cannot pickle tensorflow errors
            self.do_trial(self.trials[0], embedder.w2e, embedder.dim1, embedder.location, shuffled)
            raise SystemExit('Exited debugging mode (without saving scores).'
                             'Turn off debugging mode to train on all tasks.')
        else:
            results = [pool.apply_async(self.do_trial, args=(
                trial, embedder.w2e, embedder.dim1, embedder.location, shuffled))
                       for trial in self.trials]
            scores = []
            try:
                for res in results:
                    for score in res.get():  # score is a list [score, param1, param2, ...]
                        scores.append(score)
                pool.close()
                sys.stdout.flush()
            except KeyboardInterrupt:
                pool.close()
                sys.stdout.flush()
                raise SystemExit('Interrupt occurred during multiprocessing. Closed worker pool.')
        return scores

    def get_scores_at_eval_steps(self, trial):
        best_score = 0
        best_epoch = 0
        res = []
        for eval_id, eval_sims_mat in enumerate(trial.results.eval_sims_mats):
            trial_score = self.score(eval_sims_mat)
            num_epochs = eval_id * self.num_epochs_in_eval_step
            #
            if config.Eval.verbose:
                self.print_score(trial_score, num_epochs)
            if trial_score > best_score:
                best_score = trial_score
                best_epoch = num_epochs
            # collect
            score_at_eval_step = [trial_score] + [trial.params.__dict__[p] for p in self.df_header] + [num_epochs]
            res.append(score_at_eval_step)
        if config.Eval.verbose:
            print('Expert score={:.2f} (at epoch {})'.format(best_score, best_epoch))
            sys.stdout.flush()
        return res

    @staticmethod
    def standardize_w2e(w2e):
        # to embed_mat
        embeds = []
        for w in w2e.keys():
            embeds.append(w2e[w])
        mat = np.vstack(embeds)
        print('mean before standardization={}'.format(mat.mean()))
        #
        scaler = preprocessing.StandardScaler()
        standardized_mat = scaler.fit_transform(mat)
        print('mean after standardization={}'.format(standardized_mat.mean()))
        # back to w2e
        res = SortedDict()
        vocab = sorted(w2e.keys())
        for n, w in enumerate(vocab):
            res[w] = standardized_mat[n]
        return res

    def do_trial(self, trial, w2e, embed_size, embedder_location, shuffled):
        trial.results = self.init_results_data(
            self, ResultsData(trial.params_id, self, embed_size))
        assert hasattr(trial.results, 'params_id')
        # standardize
        if trial.params.standardize:
            print('Standardizing embeddings')
            w2e = self.standardize_w2e(w2e)
        else:
            print('Not standardizing embeddings')
        # train on each train-fold separately (fold_id is test_fold)
        for fold_id in range(config.Eval.num_folds):
            if config.Eval.verbose:
                print('Fold {}/{}'.format(fold_id + 1, config.Eval.num_folds))
            data = self.split_and_vectorize_eval_data(self, trial, w2e, fold_id, shuffled)
            graph = self.make_graph(self, trial, w2e, embed_size)
            self.train_expert_on_train_fold(self, trial, w2e, graph, data, fold_id)
            #
            try:
                self.train_expert_on_test_fold(self, trial, graph, data, fold_id)  # TODO test
            except NotImplementedError:
                pass
        # save transformed word vectors - vectors for test words collected across all folds
        process = 'expert' if not shuffled else 'control'
        p = self.make_p(embedder_location, process, 'process2_embed_mats.npy')
        if not p.parent.exists():
            p.parent.mkdir(parents=True)
        np.save(p,  trial.results.process2_embed_mats)  # these are matrices of transformed vectors for each eval_step
        # scores
        scores_at_eval_steps = self.get_scores_at_eval_steps(trial)
        return scores_at_eval_steps
