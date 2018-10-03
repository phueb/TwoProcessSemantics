import time
import torch
import numpy as np
from cytoolz import itertoolz

from src.embedders import EmbedderBase
from src import config
from src.utils import matrix_to_w2e


class LSTMEmbedder(EmbedderBase):
    def __init__(self, corpus_name, ):
        super().__init__(corpus_name, 'lstm')
        self.model = LSTMModel()

    @staticmethod
    def docs_to_stacked_shuffled_windows(numeric_docs, batch_size, shuffle=True):  # TODO implement
        shape0 = len(numeric_docs[1])
        num_excluded = shape0 % batch_size
        print('Excluding {} sequences due to fixed batch size'.format(num_excluded))
        shape0_adj = shape0 - num_excluded
        x, y = [np.zeros((shape0_adj, config.LSTM.num_steps)).astype(np.int64) for _ in range(2)]
        if shuffle:
            rand_doc_ids = np.random.choice(shape0, shape0_adj, replace=False)  # TODO need to use adjusted shape here?
        else:
            rand_doc_ids = np.arange(shape0_adj)

        # TODO make windows
        numeric_docs_flat = np.hstack(numeric_docs)[rand_doc_ids]
        assert np.rank(numeric_docs) == 1
        for w in itertoolz.sliding_window(config.LSTM.num_steps, numeric_docs_flat):
            raise NotImplementedError

        return x, y

    @staticmethod
    def gen_batches(x, y, batch_size):
        num_batches = len(x) // batch_size
        print('Generating {} batches with size {}'.format(num_batches, batch_size))
        for x_b, y_b in zip(np.vsplit(x, num_batches),
                            np.vsplit(y, num_batches)):
            yield x_b, y_b

    def run_epoch(self, numeric_docs, is_train=False, lr=1.0):
        if is_train:
            self.model.batch_size = config.LSTM.batch_size
            self.model.train()
        else:
            self.model.batch_size = 1  # to process all the data
            self.model.eval()
        start_time = time.time()
        hidden = self.model.init_hidden()
        costs = 0.0
        iters = 0
        x, y = self.docs_to_stacked_shuffled_windows(numeric_docs, self.model.batch_size)
        for step, (x_b, y_b) in enumerate(self.gen_batches(x, y, self.model.batch_size)):
            inputs = torch.autograd.Variable(torch.from_numpy(x_b).transpose(0, 1).contiguous()).cuda()
            targets = torch.autograd.Variable(torch.from_numpy(y_b).transpose(0, 1).contiguous()).cuda()
            # forward step
            self.model.zero_grad()
            hidden = self.repackage_hidden(hidden)
            outputs, hidden = self.model(inputs, hidden)
            # backward step
            targets_flat = torch.squeeze(targets.view(-1, self.model.batch_size * self.model.num_steps))
            loss = torch.nn.CrossEntropyLoss()(outputs.view(-1, config.Corpora.num_vocab), targets_flat)
            costs += loss.data[0] * self.model.num_steps
            iters += self.model.num_steps
            if is_train:
                loss.backward()
                torch.nn.utils.clip_grad_norm(self.model.parameters(), config.LSTM.grad_clip)
                for p in self.model.parameters():
                    p.data.add_(-lr, p.grad.data)
                if step % 100 == 0:
                    print("step {:,} perplexity: {:8.2f} speed: {} wps".format(step, np.exp(costs / iters),
                                                                               iters * self.model.batch_size / (
                                                                                       time.time() - start_time)))
        return np.exp(costs / iters)

    def train(self):
        assert len(self.numeric_docs) > 200
        train_numeric_docs = self.numeric_docs[:-100]  # TODO assign split using percentage and shuffling
        valid_numeric_docs = self.numeric_docs[-100:50]
        test_numeric_docs = self.numeric_docs[-50:]
        lr = config.LSTM.initital_lr
        for epoch in range(config.LSTM.num_epochs):
            lr_decay = config.LSTM.lr_decay_base ** max(epoch - config.LSTM.num_epochs_with_flat_lr, 0)
            lr = lr * lr_decay  # decay lr if it is time
            train_p = self.run_epoch(train_numeric_docs, True, lr)
            print('Train perplexity at epoch {}: {:8.2f}'.format(epoch, train_p))
            print('Validation perplexity at epoch {}: {:8.2f}'.format(epoch, self.run_epoch(valid_numeric_docs)))
        print('Test Perplexity: {:8.2f}'.format(self.run_epoch(test_numeric_docs)))

        # TODO test
        embed_mat = self.model.wx
        w2e = matrix_to_w2e(embed_mat, self.vocab)
        return w2e

    def repackage_hidden(self, h):
        """Wraps hidden states in new Variables, to detach them from their history."""
        if type(h) == torch.autograd.Variable:
            return torch.autograd.Variable(h.data)
        else:
            return tuple(self.repackage_hidden(v) for v in h)


class LSTMModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.batch_size = config.LSTM.batch_size
        self.dropout = torch.nn.Dropout(config.LSTM.dropout_prob)
        self.wx = torch.nn.Embedding(config.Corpora.num_vocab, config.LSTM.embed_size)
        self.lstm = torch.nn.LSTM(input_size=config.LSTM.embed_size,  # TODO why is this embed_size?
                                  hidden_size=config.LSTM.embed_size,
                                  num_layers=config.LSTM.num_layers,
                                  dropout=config.LSTM.dropout_prob)
        self.wy = torch.nn.Linear(in_features=config.LSTM.embed_size,
                                  out_features=config.Corpora.num_vocab)
        self.init_weights()

    def init_weights(self):
        self.wx.weight.data.uniform_(-config.LSTM.embed_init_range, config.LSTM.embed_init_range)
        self.wy.bias.data.fill_(0.0)
        self.wy.weight.data.uniform_(-config.LSTM.embed_init_range, config.LSTM.embed_init_range)

    def init_hidden(self):
        weight = next(self.parameters()).data
        return (torch.autograd.Variable(weight.new(config.LSTM.num_layers,
                                                   self.batch_size,
                                                   config.LSTM.embed_size).zero_()),
                torch.autograd.Variable(weight.new(config.LSTM.num_layers,
                                                   self.batch_size,
                                                   config.LSTM.embed_size).zero_()))

    def forward(self, inputs, hidden):
        embeds = self.dropout(self.wx(inputs))
        lstm_out, hidden = self.lstm(embeds, hidden)
        lstm_out = self.dropout(lstm_out)
        logits = self.wy(lstm_out.view(-1, config.LSTM.embed_size))
        return logits.view(config.LSTM.num_steps, self.batch_size, config.Corpora.num_vocab), hidden

