import numpy as np

from two_process_nlp.embedders.base import EmbedderBase


class RandomControlEmbedder(EmbedderBase):
    def __init__(self, param2val):
        super().__init__(param2val['param_name'], param2val['job_name'])
        self.embed_size = param2val['embed_size']
        self.random_type = param2val['random_type']
        #
        self.name = 'random_{}'.format(self.random_type)

    def train(self):
        if self.random_type == 'normal':
            self.w2e = {w: np.random.normal(0, 1.0, self.embed_size) for w in self.vocab}
        elif self.random_type == 'uniform':
            self.w2e = {w: np.random.uniform(-1.0, 1.0, self.embed_size) for w in self.vocab}
        else:
            raise NotImplementedError
