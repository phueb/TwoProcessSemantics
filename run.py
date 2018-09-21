import numpy as np

from src import config
from src.tasks.cat_classification import CatClassification
from src.embedders.lstm import LSTMEmbedder
from src.embedders.random_control import RandomControlEmbedder
from src.embedders.skipgram import SkipgramEmbedder
from src.utils import make_probe_simmat


embedders = [LSTMEmbedder(config.Corpus.name),
             SkipgramEmbedder(config.Corpus.name),
             RandomControlEmbedder(config.Corpus.name)]
tasks = [CatClassification('semantic'),
         CatClassification('syntactic')]

# initialize
num_embedders = len(embedders)
num_tasks = len(tasks)
nov_scores_mat = np.zeros((num_embedders, num_tasks))
exp_scores_mat = np.zeros((num_embedders, num_tasks))

# train and score novices and experts on task_data
for i, embedder in enumerate(embedders):
    # embed
    if embedder.has_embeddings() and not config.Embedder.retrain:
        print('Found {} in {}'.format(embedder.embeddings_fname, embedder.embeddings_dir))
        w2e = embedder.load_w2e()
    else:
        print('Did not find {} in {}. Will try to train.'.format(embedder.embeddings_fname, embedder.embeddings_dir))
        w2e = embedder.train_w2e()
        if config.Embedder.save:
            embedder.save_w2e(w2e)

    # tasks
    for j, task in enumerate(tasks):  # TODO different probes for each task?
        # similarities
        probe_simmat = make_probe_simmat(w2e, task.probes, config.Global.sim_method)
        # score
        nov_scores_mat[i, j] = task.score_novice(probe_simmat)  # novice score
        exp_scores_mat[i, j] = task.train_and_score_expert(w2e)  # expert score
        # figs
        # TODO save all figs associated with task to disk


# save scores
# noinspection PyTypeChecker
np.savetxt('novice_scores.txt', nov_scores_mat)
# noinspection PyTypeChecker
np.savetxt('expert_scores.txt', exp_scores_mat)
