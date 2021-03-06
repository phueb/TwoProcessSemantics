import numpy as np
import matplotlib.pyplot as plt

from two_process_nlp.aggregator import Aggregator
from analyze.utils import to_diff_df
from analyze.utils import to_label


LEG_FONTSIZE = 16
AX_FONTSIZE = 14
FIGSIZE = (12, 6)
DPI = 200


# make diff_df
ag = Aggregator()
df = ag.make_df(load_from_file=True, verbose=True)

# include
df = df[df['neg_pos_ratio'].isin([np.nan, 1.0])]
df = df[df['num_epochs'].isin([np.nan, NUM_EPOCHS])]
# exclude
df.drop(df[df['task'] == 'cohyponyms_syntactic'].index, inplace=True)
df.drop(df[df['embedder'] == 'random_normal'].index, inplace=True)

# make diff_df
diff_df = to_diff_df(df)

# data
task_names = diff_df['task'].unique()
print(task_names)
task_name2ys = {}
for n, task_name in enumerate(task_names):
    ys = diff_df[diff_df['task'] == task_name]['diff_score'].values
    task_name2ys[task_name] = ys
sorted_task_names = sorted(task_name2ys.keys(),
                           key=lambda task_name: np.mean(task_name2ys[task_name]))

# figure
task_name2color = {level: plt.cm.get_cmap('tab10')(n)
                   for n, level in enumerate(task_names)}

fig, ax = plt.subplots(1, figsize=FIGSIZE, dpi=DPI)
ax.set_ylim([-0.2, 0.20])
num_x = len(task_names)
x = np.arange(num_x)
ax.set_xticks(x)
ax.set_xticklabels([to_label(task_name).replace('_', '\n') for task_name in sorted_task_names], fontsize=AX_FONTSIZE)
ax.set_ylabel('Balanced Accuracy Difference\n(Classifier - Comparator)', fontsize=AX_FONTSIZE)
ax.set_xlabel('Task', fontsize=AX_FONTSIZE)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.tick_params(axis='both', which='both', top=False, right=False)
# plot
for n, task_name in enumerate(sorted_task_names):
    ys = task_name2ys[task_name]
    print(task_name, ys)
    color = task_name2color[task_name]
    ax.bar(x=n,
           height=ys.mean(),
           width=1.0,
           yerr=ys.std(),
           color=color,
           edgecolor='black')

plt.tight_layout()
plt.show()


