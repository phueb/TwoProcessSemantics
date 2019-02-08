from itertools import product

from two_stage_nlp import config


CORPUS_NAME = config.Corpus.name
NUM_VOCAB = config.Corpus.num_vocab

# for p in (config.Dirs.tasks / 'cohyponyms' / 'semantic').rglob('{}_{}.txt'.format(CORPUS_NAME, NUM_VOCAB)):
# for p in (config.Dirs.tasks / 'hypernyms').rglob('{}_{}.txt'.format(CORPUS_NAME, NUM_VOCAB)):
for p in config.Dirs.tasks.rglob('{}_{}*.txt'.format(CORPUS_NAME, NUM_VOCAB)):

    with p.open('r') as f:
        lines = f.read().splitlines()  # removes '\n' newline character

    pairs = set()
    pairs.update()
    num_possible = 0
    probes = set()
    for line in lines:
        probe = line.split()[0]
        relata = line.split()[1:]
        pairs.update(list(product([probe], relata)))
        probes.update([probe] + relata)
        num_possible += len(relata)
    print(p.relative_to(config.Dirs.tasks))
    print('Num positive pairs={:,}'.format(len(pairs)))
    print('Num positive possible={:,}'.format(num_possible))

    # TODO test
    print('NUm probes={}'.format(len(probes)))
    num_total = len(probes) ** 2

    print('Num total possible={:,}'.format(num_total))
    diff = num_possible - len(pairs)
    if diff > 0:
        print('WARNING: Difference={}. Duplicates exist'.format(diff))
    print()