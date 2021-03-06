import numpy as np
import matplotlib.pyplot as plt

from two_process_nlp.aggregator import Aggregator
from analyze.utils import to_label


FACTOR = 'task'
NUM_EPOCHS_LIST = [0, 20, 40]
ARCHITECTURES = ['comparator', 'classifier']
REGIMES = ['novice', 'expert']

LEG_FONTSIZE = 16
AX_FONTSIZE = 16
FIGSIZE = (10, 6)
DPI = 200


ag = Aggregator()
df = ag.make_df(load_from_file=True, verbose=True)


for num_epochs in NUM_EPOCHS_LIST:
    # include
    df_filtered = df.copy()
    df_filtered = df_filtered[df_filtered['neg_pos_ratio'].isin([np.nan, 1.0])]
    df_filtered = df_filtered[df_filtered['num_epochs'].isin([np.nan, num_epochs])]
    # exclude
    df_filtered.drop(df_filtered[df_filtered['task'] == 'cohyponyms_syntactic'].index, inplace=True)
    df_filtered.drop(df_filtered[df_filtered['embedder'] == 'random_normal'].index, inplace=True)

    # filter by arch
    df_filtered = df_filtered[df_filtered['arch'].isin(ARCHITECTURES)]
    if FACTOR == 'arch' and len(ARCHITECTURES) == 1:
        raise RuntimeWarning('Forgot to include an architecture in ARCHITECTURES?')

    # figure
    factor_levels = df_filtered[FACTOR].unique().tolist()
    level2color = {level: plt.cm.get_cmap('tab10')(n)
                   for n, level in enumerate(factor_levels)}

    fig, ax = plt.subplots(1, figsize=FIGSIZE, dpi=DPI)
    if FACTOR == 'embedder':
        factor = 'process-1-model'
    elif FACTOR == 'arch':
        factor = 'process-2-model'
    else:
        factor = FACTOR
    plt.title('Interaction between {} and regime\n process-2 architectures: {}\nnum_epochs={}'.format(
        factor, ', '.join(ARCHITECTURES), num_epochs), fontsize=AX_FONTSIZE)
    ax.set_ylim([0.5, 0.90])
    num_x = len(factor_levels)
    x = np.arange(2)
    ax.set_xticks(x)
    ax.set_xticklabels(REGIMES, fontsize=AX_FONTSIZE)
    ax.set_ylabel('Balanced Accuracy', fontsize=AX_FONTSIZE)
    ax.set_xlabel('Regime', fontsize=AX_FONTSIZE)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.tick_params(axis='both', which='both', top=False, right=False)
    # plot
    for level in factor_levels:
        df_subset = df_filtered[df_filtered[FACTOR] == level]
        y = []
        print(level)
        for regime in REGIMES:
            score = df_subset[df_subset['regime'] == regime]['score'].mean()
            print(regime, score)
            y.append(score)
        color = level2color[level]
        ax.plot(x, y, label=to_label(level), color=color, zorder=3, linewidth=2)
    ax.legend(loc='best', frameon=False, fontsize=LEG_FONTSIZE,
              bbox_to_anchor=(1.0, 1.0))
    plt.tight_layout()
    plt.show()


