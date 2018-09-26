import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from src import config


def make_classifier_figs(cm, x_mat, train_acc_trajs, test_acc_trajs, cats):
    train_acc_traj = train_acc_trajs.mean(axis=0)
    test_acc_traj = test_acc_trajs.mean(axis=0)
    num_cats = len(cats)
    max_x = np.max(x_mat[:, -1])

    def make_classifier_accuracy_fig():
        """
        Returns fig showing accuracy of a classifier tasked to map hidden representations of probes to categories
        """
        fig, ax = plt.subplots(1, figsize=(config.Figs.width, 3), dpi=config.Figs.dpi)
        ax.set_ylim([0, 110])
        ax.set_xlim([0, max_x])
        ax.set_xlabel('Number of Training Samples', fontsize=config.Figs.axlabel_fontsize)
        ylabel = 'Accuracy'
        ylabel += ' (shuffled cats), ' if config.Categorization.shuffle_cats else ''
        ax.set_ylabel(ylabel, fontsize=config.Figs.axlabel_fontsize)
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.tick_params(axis='both', which='both', top='off', right='off')
        ax.yaxis.grid(True)
        # plot
        print(x_mat)
        x = np.arange(config.Categorization.num_evals)  # TODO
        ax.plot(x, train_acc_traj, '-', linewidth=config.Figs.line_width, label='train')
        ax.plot(x, test_acc_traj, '-', linewidth=config.Figs.line_width, label='test')
        ax.legend(loc='best')
        plt.tight_layout()
        return fig

    def make_classifier_accuracy_breakdown_fig():
        """
        Returns fig showing accuracy broken down by category of a classifier tasked to map hidden representations
         of probes to categories
        """
        fig, axarr = plt.subplots(num_cats, 1,
                                  figsize=(config.Figs.width, 3 * num_cats),
                                  dpi=config.Figs.dpi)
        for ax, train_hca_cat_traj, test_hca_cat_traj, cat, x in zip(
                axarr, train_acc_trajs, test_acc_trajs, cats, x_mat):
            ax.set_ylim([0, 110])
            ax.set_xlim([0, max_x])
            ax.set_xlabel('Number of Training Samples', fontsize=config.Figs.axlabel_fontsize)
            ylabel = 'Accuracy'
            ylabel += ' (shuffled cats), ' if config.Categorization.shuffle_cats else ''
            ax.set_ylabel(ylabel, fontsize=config.Figs.axlabel_fontsize)
            ax.spines['right'].set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.tick_params(axis='both', which='both', top='off', right='off')
            ax.yaxis.grid(True)
            # plot
            ax.plot(x, train_hca_cat_traj, '-', linewidth=config.Figs.line_width, label='{} (train)'.format(cat))
            ax.plot(x, test_hca_cat_traj, '-', linewidth=config.Figs.line_width, label='{} (test)'.format(cat))
            ax.legend()
        plt.tight_layout()
        return fig

    def make_classifier_conf_mat_fig():
        """
        Returns fig showing confusionmatrix of classifier trained to map hidden representations of probes to categories
        """
        fig, ax = plt.subplots(1, 1, figsize=(config.Figs.width, config.Figs.width),
                               dpi=config.Figs.dpi)
        # plot
        sns.heatmap(cm, ax=ax, square=True, annot=False, cbar_kws={"shrink": .5}, cmap='jet', vmin=0, vmax=100)
        # axis 2 (needs to be below plot for axes to be labeled)
        ax.set_yticklabels([cat + ' (truth)' for cat in sorted(cats, reverse=True)], rotation=0)
        ax.set_xticklabels(cats, rotation=90)
        ax.set_title('Confusion Matrix')
        # colorbar
        cbar = ax.collections[0].colorbar
        cbar.set_ticks([0, 50, 100])
        cbar.set_ticklabels(['0%', '50%', '100%'])
        cbar.set_label('Hits & False Alarms')
        plt.tight_layout()
        return fig

    figs = [make_classifier_accuracy_fig(),
            make_classifier_accuracy_breakdown_fig(),
            make_classifier_conf_mat_fig()]
    return figs
