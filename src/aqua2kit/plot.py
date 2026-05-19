"""Plot Ca²⁺ event data from AQuA2 summaries."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy import stats

COLORS = {"treat": "#E8748A", "ctrl": "#4DADA0"}

plt.rcParams.update({
    "font.size": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
})


def _pval_stars(a, b):
    if len(a) < 2 or len(b) < 2:
        return ""
    _, p = stats.ttest_ind(a, b)
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."


def event_count_barplot(facets, summary_df, metric="n_events",
                        condition_col="condition", ctrl_label="control",
                        colors=None, title=None, out_path=None):
    """Bar plot of a Ca²⁺ metric, faceted by culture type or timepoint.

    Each facet is a subplot; each timepoint within a facet is one paired bar group
    (treatment vs control), with individual replicate dots and significance stars.

    Args:
        facets: list of dicts describing each subplot panel:
            {
              "title": "Astro only",
              "timepoints": [
                {
                  "label":      "day+3",        # x-axis tick label
                  "experiment": "3.31.26",       # must match 'experiment' column in summary_df
                  "treat":      "+amyloid",      # treatment condition label
                  "ctrl":       "control",       # control condition label (optional, overrides global)
                },
                ...
              ]
            }
        summary_df:     Per-sample summary DataFrame from quantify_samples().
                        Must have columns: condition_col, metric, and 'experiment'.
        metric:         Column to plot on Y axis (default 'n_events').
        condition_col:  Column name for condition labels (default 'condition').
        ctrl_label:     Default control label (default 'control').
        colors:         Dict with 'treat' and 'ctrl' keys for bar colors.
        title:          Figure suptitle.
        out_path:       If given, save figure to this path and close it.
                        If None, return the Figure object.

    Returns:
        matplotlib Figure if out_path is None, else None.

    Example:
        facets = [
            {"title": "Astro only", "timepoints": [
                {"label": "day+3", "experiment": "3.31.26", "treat": "+amyloid"},
            ]},
        ]
        fig = event_count_barplot(facets, summary_df)
        fig.savefig("figure.png", dpi=180, bbox_inches="tight")
    """
    if colors is None:
        colors = COLORS

    BAR_W = 0.32
    JIT = np.array([-0.07, 0.0, 0.07])

    fig, axes = plt.subplots(1, len(facets),
                             figsize=(4.5 * len(facets), 4.2),
                             sharey=True)
    if len(facets) == 1:
        axes = [axes]

    if title:
        fig.suptitle(title, fontsize=10, fontweight="bold", y=1.03)

    all_treat_labels = set()

    for ax, facet in zip(axes, facets):
        timepoints = facet["timepoints"]
        offset = {"treat": -BAR_W / 2 - 0.02, "ctrl": BAR_W / 2 + 0.02}

        for xi, tp in enumerate(timepoints):
            df_exp = summary_df[summary_df["experiment"] == tp["experiment"]]
            treat_lbl = tp.get("treat")
            ctrl_lbl = tp.get("ctrl", ctrl_label)
            all_treat_labels.add(treat_lbl)

            treat_vals = df_exp[df_exp[condition_col] == treat_lbl][metric].values.astype(float)
            ctrl_vals  = df_exp[df_exp[condition_col] == ctrl_lbl][metric].values.astype(float)

            for vals, role in [(treat_vals, "treat"), (ctrl_vals, "ctrl")]:
                xc = xi + offset[role]
                color = colors[role]
                mean_v = vals.mean() if len(vals) else 0
                sem_v = vals.std(ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0

                ax.bar(xc, mean_v, width=BAR_W, color=color, alpha=0.85,
                       yerr=sem_v, capsize=3,
                       error_kw=dict(lw=1.1, capthick=1.1), zorder=2)

                j = JIT[:len(vals)]
                ax.scatter(xc + j * 0.6, vals, color="white", edgecolors=color,
                           s=30, zorder=4, linewidths=1.1)

            n_pairs = min(len(treat_vals), len(ctrl_vals))
            for k in range(n_pairs):
                ax.plot(
                    [xi + offset["treat"] + JIT[k] * 0.6,
                     xi + offset["ctrl"]  + JIT[k] * 0.6],
                    [treat_vals[k], ctrl_vals[k]],
                    color="#888", lw=0.6, alpha=0.5, zorder=3,
                )

            stars = _pval_stars(treat_vals, ctrl_vals)
            if stars:
                ymax = max(treat_vals.max() if len(treat_vals) else 0,
                           ctrl_vals.max() if len(ctrl_vals) else 0)
                ytop = ymax * 1.12
                ax.plot(
                    [xi + offset["treat"], xi + offset["treat"],
                     xi + offset["ctrl"],  xi + offset["ctrl"]],
                    [ytop * 0.94, ytop, ytop, ytop * 0.94],
                    lw=0.8, color="k",
                )
                ax.text(xi, ytop * 1.02, stars, ha="center", va="bottom", fontsize=8)

        ax.set_xticks(range(len(timepoints)))
        ax.set_xticklabels([tp["label"] for tp in timepoints], fontsize=8.5)
        ax.set_title(facet["title"], fontsize=10, fontweight="bold")
        ax.set_xlabel("Days post treatment", fontsize=8)

    axes[0].set_ylabel(metric, fontsize=9)

    treat_legend = " / ".join(sorted(all_treat_labels - {None})) or "+treatment"
    fig.legend(
        handles=[Patch(color=colors["treat"], label=treat_legend),
                 Patch(color=colors["ctrl"],  label=ctrl_label)],
        loc="lower center", ncol=2, frameon=False, fontsize=9,
        bbox_to_anchor=(0.5, -0.07),
    )

    plt.tight_layout()

    if out_path:
        fig.savefig(out_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {out_path}")
        return None
    return fig
