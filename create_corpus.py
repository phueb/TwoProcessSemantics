from src import wikicorpus
import sys

corpus_path = sys.argv[1]
corpus_name = sys.argv[2]

wiki_corpus = wikicorpus.Corpus()
wiki_corpus.generate_wiki_corpus(corpus_path, corpus_name)