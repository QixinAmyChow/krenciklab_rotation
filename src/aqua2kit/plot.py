"""Plot Ca²⁺ event data from AQuA2 summaries and .mat files."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
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


def plot_dff(mat_path, atp_frame, fps, output=None, title=None):
    """Plot per-event dF/F traces vs time with mean and ATP-addition marker.

    Args:
        mat_path:  Path to *_AQuA2.mat.
        atp_frame: First frame of drug addition (0-based).
        fps:       Frame rate in Hz.
        output:    Output PNG path. Default: <mat_stem>_dff.png next to mat.
        title:     Plot title. Default: mat filename stem.

    Returns:
        Path to the saved PNG (str).
    """
    from pathlib import Path
    from .aqua2_io import prestim_dff

    mat_path = Path(mat_path)
    if output is None:
        output = mat_path.parent / (mat_path.stem + "_dff.png")
    if title is None:
        title = mat_path.stem

    dff = prestim_dff(mat_path, atp_frame)
    n_frames, n_events = dff.shape
    t = np.arange(n_frames) / fps
    atp_time = atp_frame / fps

    fig, ax = plt.subplots(figsize=(8, 6))

    for i in range(n_events):
        ax.plot(t, dff[:, i], color="steelblue", alpha=0.12, linewidth=0.6)

    ax.plot(t, dff.mean(axis=1), color="navy", linewidth=1.8, label="mean dF/F")
    ax.axvline(atp_time, color="crimson", linestyle="--", linewidth=1.4,
               label="ATP addition")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("dF/F")
    ax.set_title(title)
    ax.legend(fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)

    return str(output)


def plot_cell_oscillation_freq(mat_path, label_map_path, atp_frame, fps,
                               min_prominence=0.05, min_distance=3,
                               output=None, title=None):
    """Bar + dot plot of Ca2+ oscillation frequency pre/post ATP per cell.

    Args:
        mat_path:       Path to *_AQuA2.mat.
        label_map_path: Path to *_label_map.tif.
        atp_frame:      First frame of ATP addition (0-based).
        fps:            True frame rate in Hz.
        min_prominence: Peak detection prominence threshold (fraction of std).
        min_distance:   Min frames between peaks.
        output:         Output PNG path.
        title:          Plot title.

    Returns:
        Path to saved PNG (str).
    """
    from pathlib import Path
    from .utils import cell_oscillation_freq

    mat_path = Path(mat_path)
    if output is None:
        output = mat_path.parent / (mat_path.stem + "_osc_freq.png")
    if title is None:
        title = mat_path.stem

    data = cell_oscillation_freq(mat_path, label_map_path, atp_frame, fps,
                                 min_prominence=min_prominence,
                                 min_distance=min_distance)

    pre_rates  = np.array([d["freq_pre"]  for d in data])
    post_rates = np.array([d["freq_post"] for d in data])
    n = len(data)

    means = [pre_rates.mean(), post_rates.mean()]
    sems  = [pre_rates.std(ddof=1) / n**0.5, post_rates.std(ddof=1) / n**0.5]

    fig, ax = plt.subplots(figsize=(4, 4))
    colors = ["#4DADA0", "#E8748A"]

    for x, mean, sem, color in zip([0, 1], means, sems, colors):
        ax.bar(x, mean, width=0.5, color=color, alpha=0.85,
               yerr=sem, capsize=4, error_kw=dict(lw=1.2, capthick=1.2), zorder=2)

    rng = np.random.default_rng(0)
    jitter_pre  = rng.uniform(-0.1, 0.1, n)
    jitter_post = rng.uniform(-0.1, 0.1, n)

    for pre, post, jp, jq in zip(pre_rates, post_rates, jitter_pre, jitter_post):
        ax.plot([jp, 1 + jq], [pre, post],
                color="#888", lw=0.5, alpha=0.35, zorder=1)

    ax.scatter(jitter_pre,  pre_rates,  color="white", edgecolors=colors[0],
               s=25, zorder=3, linewidths=1)
    ax.scatter(1 + jitter_post, post_rates, color="white", edgecolors=colors[1],
               s=25, zorder=3, linewidths=1)

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["pre-ATP", "post-ATP"])
    ax.set_ylabel("Ca²⁺ oscillations / min")
    ax.set_title(f"{title}\n(n={n} cells)", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(-0.5, 1.5)

    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)

    return str(output)


def plot_cell_event_rates(mat_path, label_map_path, atp_frame, fps,
                          overlap_threshold=0.0, min_frame=2,
                          output=None, title=None):
    """Bar plot of mean ± SEM event rate pre/post ATP across cells (ROIs).

    Each cell is one data point. Shows mean ± SEM bars with individual cell dots.

    Args:
        mat_path:          Path to *_AQuA2.mat.
        label_map_path:    Path to *_label_map.tif.
        atp_frame:         First frame of ATP addition (0-based).
        fps:               True frame rate in Hz.
        overlap_threshold: Min overlap fraction for event-to-cell assignment.
        min_frame:         Exclude events with t0 <= this.
        output:            Output PNG path.
        title:             Plot title.

    Returns:
        Path to saved PNG (str).
    """
    from pathlib import Path
    from .utils import cell_event_rates

    mat_path = Path(mat_path)
    if output is None:
        output = mat_path.parent / (mat_path.stem + "_cell_rates.png")
    if title is None:
        title = mat_path.stem

    data = cell_event_rates(mat_path, label_map_path, atp_frame, fps,
                            overlap_threshold=overlap_threshold,
                            min_frame=min_frame)

    pre_rates  = np.array([d["rate_pre"]  for d in data])
    post_rates = np.array([d["rate_post"] for d in data])
    n = len(data)

    means = [pre_rates.mean(), post_rates.mean()]
    sems  = [pre_rates.std(ddof=1) / n**0.5, post_rates.std(ddof=1) / n**0.5]

    fig, ax = plt.subplots(figsize=(4, 4))

    colors = ["#4DADA0", "#E8748A"]
    labels = ["pre-ATP", "post-ATP"]
    xs = [0, 1]

    for x, mean, sem, color in zip(xs, means, sems, colors):
        ax.bar(x, mean, width=0.5, color=color, alpha=0.85,
               yerr=sem, capsize=4, error_kw=dict(lw=1.2, capthick=1.2), zorder=2)

    jitter = np.linspace(-0.1, 0.1, n)
    for pre, post in zip(pre_rates, post_rates):
        j = jitter[np.random.randint(n)]
        ax.plot([0 + j, 1 + j], [pre, post],
                color="#888", lw=0.5, alpha=0.4, zorder=1)

    ax.scatter(np.zeros(n) + np.random.uniform(-0.1, 0.1, n), pre_rates,
               color="white", edgecolors=colors[0], s=25, zorder=3, linewidths=1)
    ax.scatter(np.ones(n)  + np.random.uniform(-0.1, 0.1, n), post_rates,
               color="white", edgecolors=colors[1], s=25, zorder=3, linewidths=1)

    ax.set_xticks([0, 1])
    ax.set_xticklabels(labels)
    ax.set_ylabel("Events / min")
    ax.set_title(f"{title}\n(n={n} cells)", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(-0.5, 1.5)

    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)

    return str(output)


def plot_event_trajectories(mat_path, prop_threshold=3.0, output=None, title=None):
    """Plot event trajectories on the field of view, classified by propagation type.

    Static events (avgPropSpeed < prop_threshold) shown as dots.
    Propagative events shown as trajectory lines with an arrow, colored by
    dominant direction (Anterior / Posterior / Left / Right).

    Args:
        mat_path:       Path to *_AQuA2.mat.
        prop_threshold: avgPropSpeed (px/frame) below which an event is static.
        output:         Output PNG path.
        title:          Plot title.

    Returns:
        Path to saved PNG (str).
    """
    import h5py
    from pathlib import Path

    DIRS   = ["Anterior", "Posterior", "Left", "Right"]
    COLORS = {
        "Static":    "#888888",
        "Anterior":  "#4C72B0",
        "Posterior": "#DD8452",
        "Left":      "#55A868",
        "Right":     "#C44E52",
    }

    mat_path = Path(mat_path)
    if output is None:
        output = mat_path.parent / (mat_path.stem + "_trajectories.png")
    if title is None:
        title = mat_path.stem

    with h5py.File(mat_path, "r") as f:
        sz      = f["res/opts/sz"][:].ravel().astype(int)
        W, H    = sz[0], sz[1]
        T       = sz[3]
        n_evt   = f["res/fts1/loc/xSpaTemp"].shape[0]

        # max projection for background
        dat = f["res/datOrg1"][:, 0, :, :]   # (T, H, W)
        bg  = dat.max(axis=0).astype(float)

        avg_speed  = f["res/fts1/propagation/avgPropSpeed"][:, 0]
        prop_grow  = f["res/fts1/propagation/propGrowOverall"][:]  # (4, n_evt)
        centers    = []
        for i in range(n_evt):
            ref = f["res/fts1/basic/center"][i, 0]
            c   = f[ref][:].ravel()           # [row, col, frame] 1-based
            centers.append((c[0] - 1, c[1] - 1))   # 0-based (row, col)

        # decode xSpaTemp → per-frame centroids for each event
        trajectories = []
        for i in range(n_evt):
            ref = f["res/fts1/loc/xSpaTemp"][i, 0]
            idx = f[ref][:].astype(int).ravel() - 1   # 0-based 3D col-major
            fr  = idx // (H * W)
            rem = idx % (H * W)
            rows = rem % H
            cols = rem // H

            traj = []
            for fr_idx in sorted(np.unique(fr)):
                mask = fr == fr_idx
                traj.append((cols[mask].mean(), rows[mask].mean()))  # (x, y)
            trajectories.append(traj)

    # classify
    categories = []
    for i in range(n_evt):
        if avg_speed[i] < prop_threshold:
            categories.append("Static")
        else:
            dom = int(np.argmax(prop_grow[:, i]))
            categories.append(DIRS[dom])

    # normalise background for display
    bg_norm = (bg - bg.min()) / (bg.max() - bg.min() + 1e-9)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(bg_norm, cmap="gray", origin="upper", vmin=0, vmax=1)

    for i, (traj, cat) in enumerate(zip(trajectories, categories)):
        color = COLORS[cat]
        xs = [p[0] for p in traj]
        ys = [p[1] for p in traj]

        if cat == "Static":
            ax.plot(xs[0], ys[0], "o", color=color, markersize=4, alpha=0.7)
        else:
            ax.plot(xs, ys, "-", color=color, linewidth=0.8, alpha=0.6)
            if len(xs) >= 2:
                ax.annotate("", xy=(xs[-1], ys[-1]), xytext=(xs[-2], ys[-2]),
                            arrowprops=dict(arrowstyle="->", color=color,
                                           lw=1.2))

        cx, cy = centers[i]
        ax.text(cy + 3, cx + 3, str(i + 1),
                fontsize=5, color=color, alpha=0.85,
                ha="left", va="top")

    # legend
    legend_handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["Static"],
               markersize=6, label="Static"),
        Line2D([0], [0], color=COLORS["Anterior"],  lw=1.5, label="Anterior"),
        Line2D([0], [0], color=COLORS["Posterior"], lw=1.5, label="Posterior"),
        Line2D([0], [0], color=COLORS["Left"],      lw=1.5, label="Left"),
        Line2D([0], [0], color=COLORS["Right"],     lw=1.5, label="Right"),
    ]
    ax.legend(handles=legend_handles, fontsize=7, loc="upper right",
              framealpha=0.7)

    # counts in title
    from collections import Counter
    counts = Counter(categories)
    count_str = "  ".join(f"{k}: {counts[k]}" for k in
                          ["Static"] + [d for d in DIRS if d in counts])
    ax.set_title(f"{title}\n{count_str}", fontsize=8)
    ax.axis("off")

    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)

    return str(output)


def plot_cell_peakcaller(mat_path, label_map_path, atp_frame, fps,
                         ema_smoothness=40, rise=0.10, fall=0.10,
                         lookback_frames=5, lookahead_frames=8,
                         output=None, title=None):
    """Bar + dot plot of PeakCaller peak frequency pre/post ATP per cell.

    Args:
        mat_path:         Path to *_AQuA2.mat.
        label_map_path:   Path to *_label_map.tif.
        atp_frame:        First frame of ATP addition (0-based).
        fps:              True frame rate in Hz.
        ema_smoothness:   EMA window k for baseline detrending (default 40).
        rise:             Required rise fraction (default 0.10).
        fall:             Required fall fraction (default 0.10).
        lookback_frames:  Lookback window in frames (default 5).
        lookahead_frames: Lookahead window in frames (default 8).
        output:           Output PNG path.
        title:            Plot title.

    Returns:
        Path to saved PNG (str).
    """
    from pathlib import Path
    from .utils import cell_peakcaller

    mat_path = Path(mat_path)
    if output is None:
        output = mat_path.parent / (mat_path.stem + "_peakcaller.png")
    if title is None:
        title = mat_path.stem

    data = cell_peakcaller(mat_path, label_map_path, atp_frame, fps,
                           ema_smoothness=ema_smoothness,
                           rise=rise, fall=fall,
                           lookback_frames=lookback_frames,
                           lookahead_frames=lookahead_frames)

    pre_rates  = np.array([d["freq_pre"]  for d in data])
    post_rates = np.array([d["freq_post"] for d in data])
    n = len(data)

    means = [pre_rates.mean(), post_rates.mean()]
    sems  = [pre_rates.std(ddof=1) / n**0.5 if n > 1 else 0,
             post_rates.std(ddof=1) / n**0.5 if n > 1 else 0]

    fig, ax = plt.subplots(figsize=(4, 4))
    colors = ["#4DADA0", "#E8748A"]

    for x, mean, sem, color in zip([0, 1], means, sems, colors):
        ax.bar(x, mean, width=0.5, color=color, alpha=0.85,
               yerr=sem, capsize=4, error_kw=dict(lw=1.2, capthick=1.2), zorder=2)

    rng = np.random.default_rng(0)
    jitter_pre  = rng.uniform(-0.1, 0.1, n)
    jitter_post = rng.uniform(-0.1, 0.1, n)

    for pre, post, jp, jq in zip(pre_rates, post_rates, jitter_pre, jitter_post):
        ax.plot([jp, 1 + jq], [pre, post],
                color="#888", lw=0.5, alpha=0.35, zorder=1)

    ax.scatter(jitter_pre,       pre_rates,  color="white", edgecolors=colors[0],
               s=25, zorder=3, linewidths=1)
    ax.scatter(1 + jitter_post,  post_rates, color="white", edgecolors=colors[1],
               s=25, zorder=3, linewidths=1)

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["pre-ATP", "post-ATP"])
    ax.set_ylabel("Ca²⁺ peaks / min  (PeakCaller)")
    ax.set_title(f"{title}\n(n={n} cells, rise={rise:.0%}, fall={fall:.0%}, "
                 f"ema={ema_smoothness})", fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(-0.5, 1.5)

    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)

    return str(output)


def plot_cell_peakcaller_fc(mat_path, label_map_path, atp_frame, fps,
                            ema_smoothness=40, rise=0.10, fall=0.10,
                            lookback_frames=5, lookahead_frames=8,
                            output=None, title=None):
    """Bar + dot plot of fold change in PeakCaller peak frequency (post/pre ATP).

    Each window is detrended independently so the pre-ATP EMA baseline cannot
    be pulled up by the post-ATP Ca2+ surge.

    Fold change = freq_post / freq_pre per cell. Cells with freq_pre == 0 are
    excluded from the fold-change bar and reported as annotations.

    Args:
        mat_path:         Path to *_AQuA2.mat.
        label_map_path:   Path to *_label_map.tif.
        atp_frame:        First frame of ATP addition (0-based).
        fps:              True frame rate in Hz.
        ema_smoothness:   EMA window k for baseline detrending (default 40).
        rise:             Required rise fraction (default 0.10).
        fall:             Required fall fraction (default 0.10).
        lookback_frames:  Lookback window in frames (default 5).
        lookahead_frames: Lookahead window in frames (default 8).
        output:           Output PNG path.
        title:            Plot title.

    Returns:
        Path to saved PNG (str).
    """
    from pathlib import Path
    from .utils import cell_peakcaller

    mat_path = Path(mat_path)
    if output is None:
        output = mat_path.parent / (mat_path.stem + "_peakcaller_fc.png")
    if title is None:
        title = mat_path.stem

    data = cell_peakcaller(mat_path, label_map_path, atp_frame, fps,
                           ema_smoothness=ema_smoothness,
                           rise=rise, fall=fall,
                           lookback_frames=lookback_frames,
                           lookahead_frames=lookahead_frames)

    fold_changes = np.array([d["fold_change"] for d in data])
    n_total = len(data)

    fc_mask = np.isfinite(fold_changes)
    fc = fold_changes[fc_mask]
    n_fc = len(fc)
    n_newly_active  = sum(1 for d in data if d["freq_pre"] == 0 and d["freq_post"] > 0)
    n_always_silent = sum(1 for d in data if d["freq_pre"] == 0 and d["freq_post"] == 0)

    fig, ax = plt.subplots(figsize=(4, 4))

    if n_fc > 0:
        fc_mean = fc.mean()
        fc_sem  = fc.std(ddof=1) / n_fc**0.5 if n_fc > 1 else 0
        ax.bar(0, fc_mean, width=0.5, color="#9B59B6", alpha=0.85,
               yerr=fc_sem, capsize=4, error_kw=dict(lw=1.2, capthick=1.2), zorder=2)
        rng = np.random.default_rng(0)
        jitter = rng.uniform(-0.1, 0.1, n_fc)
        ax.scatter(jitter, fc, color="white", edgecolors="#9B59B6",
                   s=25, zorder=3, linewidths=1)

    ax.axhline(1.0, color="#888", linestyle="--", linewidth=1, zorder=0)

    info_lines = [f"n={n_fc} cells (fold change)"]
    if n_newly_active > 0:
        info_lines.append(f"{n_newly_active} newly active (0→>0 peaks)")
    if n_always_silent > 0:
        info_lines.append(f"{n_always_silent} always silent")
    ax.text(0.97, 0.97, "\n".join(info_lines),
            transform=ax.transAxes, ha="right", va="top", fontsize=7, color="#444")

    ax.set_xticks([0])
    ax.set_xticklabels(["post / pre"])
    ax.set_ylabel("Fold change in peak frequency")
    ax.set_title(f"{title}\n(rise={rise:.0%}, fall={fall:.0%}, ema={ema_smoothness})",
                 fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(-0.5, 0.5)

    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)

    return str(output)


def plot_cell_roi_map(mat_path, label_map_path, output=None, title=None):
    """Plot cell ROIs from label_map.tif overlaid on max projection, labeled by cell index.

    Args:
        mat_path:       Path to *_AQuA2.mat (used for background max projection).
        label_map_path: Path to *_label_map.tif.
        output:         Output PNG path.
        title:          Plot title.

    Returns:
        Path to saved PNG (str).
    """
    import h5py
    import tifffile
    from pathlib import Path
    from scipy import ndimage

    mat_path = Path(mat_path)
    if output is None:
        output = mat_path.parent / (mat_path.stem + "_roi_map.png")
    if title is None:
        title = mat_path.stem

    with h5py.File(mat_path, "r") as f:
        dat = f["res/datOrg1"][:, 0, :, :]   # (T, H, W)
    bg = dat.max(axis=0).astype(float)
    bg = (bg - bg.min()) / (bg.max() - bg.min() + 1e-9)

    lmap = tifffile.imread(label_map_path)
    cell_ids = sorted(c for c in np.unique(lmap) if c != 0)
    n_cells = len(cell_ids)

    cmap = plt.colormaps["tab20"]

    # build single RGBA overlay — all cells in one pass
    overlay = np.zeros((*lmap.shape, 4), dtype=float)
    centroids = {}
    for idx, cell_id in enumerate(cell_ids):
        mask = lmap == cell_id
        color = cmap(idx % 20)
        overlay[mask, :3] = color[:3]
        overlay[mask,  3] = 0.45
        cy, cx = ndimage.center_of_mass(mask)
        centroids[cell_id] = (cx, cy)

    fig, ax = plt.subplots(figsize=(9, 9))
    ax.imshow(bg, cmap="gray", origin="upper")
    ax.imshow(overlay, origin="upper", interpolation="nearest")

    for idx, cell_id in enumerate(cell_ids):
        cx, cy = centroids[cell_id]
        color = cmap(idx % 20)
        ax.text(cx, cy, str(cell_id),
                ha="center", va="center", fontsize=5.5, fontweight="bold",
                color="white",
                bbox=dict(boxstyle="round,pad=0.15", facecolor=color[:3],
                          alpha=0.75, edgecolor="none", linewidth=0))

    ax.set_title(f"{title}\n({n_cells} cells — colored by cell index)", fontsize=9)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)

    return str(output)


def plot_event_direction_distribution(mat_paths, atp_frames, fps,
                                      prop_threshold=3.0, min_frame=2,
                                      output=None, title=None):
    """Bar chart of propagative vs static event counts, split by recording phase.

    Args:
        mat_paths:      List of paths to *_AQuA2.mat files.
        atp_frames:     List of int-or-None, same length as mat_paths.
                        None means the entire recording is treated as spontaneous.
        fps:            Frame rate in Hz (same for all recordings).
        prop_threshold: avgPropSpeed below which an event is Static (default 3.0).
        min_frame:      Exclude events with t0 <= this (default 2).
        output:         Output PNG path.
        title:          Plot title.

    Returns:
        Path to saved PNG (str).
    """
    import h5py
    from pathlib import Path
    from collections import Counter

    DIRS = ["Anterior", "Posterior", "Left", "Right"]
    ALL_CATS = ["Static"] + DIRS
    CAT_COLORS = {
        "Static":    "#888888",
        "Anterior":  "#4C72B0",
        "Posterior": "#DD8452",
        "Left":      "#55A868",
        "Right":     "#C44E52",
    }

    if output is None:
        output = Path(mat_paths[0]).parent / "event_direction_distribution.png"
    if title is None:
        title = "Event direction distribution"

    # collect counts per phase
    phase_counts = {}   # phase_label -> Counter({cat: count})

    for mat_path, atp_frame in zip(mat_paths, atp_frames):
        with h5py.File(mat_path, "r") as f:
            n          = f["res/fts1/loc/xSpa"].shape[0]
            t0_all     = f["res/fts1/loc/t0"][:, 0].astype(int)
            speed_all  = f["res/fts1/propagation/avgPropSpeed"][:, 0].astype(float)
            prop_grow  = f["res/fts1/propagation/propGrowOverall"][:]

        stem = Path(mat_path).stem
        # derive a short label from filename
        if "rep1" in stem or atp_frame is None:
            rec_label = "rep1\n(spontaneous)"
        elif "rep2" in stem:
            rec_label = "rep2"
        else:
            rec_label = Path(mat_path).parent.parent.name

        for i in range(n):
            t0 = t0_all[i]
            if t0 <= min_frame:
                continue

            speed = speed_all[i]
            cat = "Static" if speed < prop_threshold else DIRS[int(np.argmax(prop_grow[:, i]))]

            if atp_frame is None:
                phase = f"{rec_label}"
            elif t0 < atp_frame:
                phase = f"{rec_label}\npre-ATP"
            else:
                phase = f"{rec_label}\npost-ATP"

            if phase not in phase_counts:
                phase_counts[phase] = Counter()
            phase_counts[phase][cat] += 1

    phases = list(phase_counts.keys())
    n_phases = len(phases)
    x = np.arange(n_phases)
    bar_w = 0.6

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(max(5, n_phases * 1.8), 6),
                                         gridspec_kw={"height_ratios": [3, 1]})

    # top: stacked bar of direction counts
    bottoms = np.zeros(n_phases)
    for cat in ALL_CATS:
        vals = np.array([phase_counts[p].get(cat, 0) for p in phases], dtype=float)
        ax_top.bar(x, vals, bar_w, bottom=bottoms,
                   color=CAT_COLORS[cat], label=cat, zorder=2)
        # label each segment if count > 0
        for xi, (v, b) in enumerate(zip(vals, bottoms)):
            if v > 0:
                ax_top.text(xi, b + v / 2, str(int(v)),
                            ha="center", va="center", fontsize=8,
                            color="white" if cat != "Static" else "white",
                            fontweight="bold")
        bottoms += vals

    # total above each bar
    totals = np.array([sum(phase_counts[p].values()) for p in phases])
    for xi, tot in enumerate(totals):
        ax_top.text(xi, tot + 0.3, str(int(tot)),
                    ha="center", va="bottom", fontsize=8, color="#333")

    ax_top.set_xticks(x)
    ax_top.set_xticklabels(phases, fontsize=8)
    ax_top.set_ylabel("Event count")
    ax_top.set_title(title, fontsize=10)
    ax_top.spines[["top", "right"]].set_visible(False)
    ax_top.legend(loc="upper left", fontsize=8, frameon=False)

    # bottom: propagative fraction per phase
    prop_frac = np.array([
        1 - phase_counts[p].get("Static", 0) / max(sum(phase_counts[p].values()), 1)
        for p in phases
    ])
    bars = ax_bot.bar(x, prop_frac * 100, bar_w, color="#9B59B6", alpha=0.8, zorder=2)
    for xi, v in enumerate(prop_frac * 100):
        ax_bot.text(xi, v + 0.5, f"{v:.0f}%",
                    ha="center", va="bottom", fontsize=8)
    ax_bot.set_xticks(x)
    ax_bot.set_xticklabels(phases, fontsize=8)
    ax_bot.set_ylabel("Propagative (%)")
    ax_bot.set_ylim(0, 110)
    ax_bot.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    out = str(output)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_events_per_frame(mat_path, atp_frame, fps, min_frame=2, output=None, title=None):
    """Plot event count per frame (onset histogram) with ATP marker.

    Args:
        mat_path:  Path to *_AQuA2.mat.
        atp_frame: First frame of ATP addition (0-based).
        fps:       True frame rate in Hz (used to label x-axis in seconds).
        min_frame: Exclude events with t0 <= this.
        output:    Output PNG path.
        title:     Plot title.

    Returns:
        Path to saved PNG (str).
    """
    import h5py
    from pathlib import Path

    mat_path = Path(mat_path)
    if output is None:
        output = mat_path.parent / (mat_path.stem + "_events_per_frame.png")
    if title is None:
        title = mat_path.stem

    with h5py.File(mat_path, "r") as f:
        t0 = f["res/fts1/loc/t0"][:, 0].astype(int)
        t1 = f["res/fts1/loc/t1"][:, 0].astype(int)
        T  = int(f["res/opts/sz"][3, 0])

    mask = t0 > min_frame
    t0, t1 = t0[mask], t1[mask]

    counts = np.zeros(T, dtype=int)
    for s, e in zip(t0, t1):
        counts[s:min(e + 1, T)] += 1

    frames = np.arange(T)
    atp_sec = atp_frame / fps

    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(frames, counts, color="steelblue", linewidth=1.2)
    ax.axvline(atp_frame, color="crimson", linestyle="--", linewidth=1.4,
               label=f"ATP addition (frame {atp_frame}, {atp_sec:.0f} s)")
    ax.set_xlabel("Frame")
    ax.set_ylabel("Events")
    ax.set_title(title, fontsize=9)
    ax.set_xlim(0, T)
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)

    return str(output)


def plot_event_rate(mat_path, atp_frame, fps, min_frame=2, output=None, title=None):
    """Bar plot of event rate (events/min) pre vs post ATP, normalized by time.

    Args:
        mat_path:  Path to *_AQuA2.mat.
        atp_frame: First frame of drug addition (0-based).
        fps:       True frame rate in Hz.
        min_frame: Exclude events with t0 <= this (frame-1 artifacts).
        output:    Output PNG path. Default: <mat_stem>_event_rate.png next to mat.
        title:     Plot title.

    Returns:
        Path to saved PNG (str).
    """
    import h5py
    from pathlib import Path

    mat_path = Path(mat_path)
    if output is None:
        output = mat_path.parent / (mat_path.stem + "_event_rate.png")
    if title is None:
        title = mat_path.stem

    with h5py.File(mat_path, "r") as f:
        t0 = f["res/fts1/loc/t0"][:, 0].astype(int)
        T  = int(f["res/opts/sz"][3, 0])

    t0 = t0[t0 > min_frame]
    pre_sec  = atp_frame / fps
    post_sec = (T - atp_frame) / fps

    n_pre  = int((t0 < atp_frame).sum())
    n_post = int((t0 >= atp_frame).sum())

    rate_pre  = n_pre  / pre_sec  * 60
    rate_post = n_post / post_sec * 60

    fig, ax = plt.subplots(figsize=(4, 4))
    bars = ax.bar(["pre-ATP", "post-ATP"], [rate_pre, rate_post],
                  color=["#4DADA0", "#E8748A"], width=0.5, edgecolor="white")

    for bar, rate in zip(bars, [rate_pre, rate_post]):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.05,
                f"{rate:.2f}", ha="center", va="bottom", fontsize=9)


    ax.set_ylabel("Events / min")
    ax.set_title(title, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(0, max(rate_pre, rate_post) * 1.25)

    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)

    return str(output)
