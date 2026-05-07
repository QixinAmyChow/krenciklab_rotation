"""
AQuA2 analysis for astrocyte+neuron experiment.
3 experiments x 2 conditions x 3 replicates = 18 samples.
Produces panels c-g (same as coculture slides) + Excel summary.
"""

import csv, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy import stats

plt.rcParams.update({
    'font.size': 9,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
})

BASE = '/home/crnlqz/krenciklab/astrocyte+neuron_out'

# ── Sample map ────────────────────────────────────────────────────────────────
EXPERIMENTS = [
    {
        'id': '3.31.26',
        'label': 'Astro only — 3/31/26',
        'color_treat': '#E8748A',
        'color_ctrl':  '#4DADA0',
        'treat_label': '+amyloid (3d)',
        'samples': [
            dict(condition='control',    rep=1, folder='3.31.26 Astro+-Neuron+- ABO__astro_only_control_rep1_results',            csv='3.31.26 Astro+-Neuron+- ABO__astro_only_control_rep1_AQuA2_Ch1.csv'),
            dict(condition='control',    rep=2, folder='3.31.26 Astro+-Neuron+- ABO__astro_only_control_rep2_results',            csv='3.31.26 Astro+-Neuron+- ABO__astro_only_control_rep2_AQuA2_Ch1.csv'),
            dict(condition='control',    rep=3, folder='3.31.26 Astro+-Neuron+- ABO__astro_only_control_rep3_results',            csv='3.31.26 Astro+-Neuron+- ABO__astro_only_control_rep3_AQuA2_Ch1.csv'),
            dict(condition='+amyloid',   rep=1, folder='3.31.26 Astro+-Neuron+- ABO__astro_only_post_3_day_amyloid_rep1_results', csv='3.31.26 Astro+-Neuron+- ABO__astro_only_post_3_day_amyloid_rep1_AQuA2_Ch1.csv'),
            dict(condition='+amyloid',   rep=2, folder='3.31.26 Astro+-Neuron+- ABO__astro_only_post_3_day_amyloid_rep2_results', csv='3.31.26 Astro+-Neuron+- ABO__astro_only_post_3_day_amyloid_rep2_AQuA2_Ch1.csv'),
            dict(condition='+amyloid',   rep=3, folder='3.31.26 Astro+-Neuron+- ABO__atro_only_post_3_day_amyloid_rep3_results',  csv='3.31.26 Astro+-Neuron+- ABO__atro_only_post_3_day_amyloid_rep3_AQuA2_Ch1.csv'),
        ],
    },
    {
        'id': '4.1.26',
        'label': 'Astro+Neuron — 4/1/26  (ABO day 4)',
        'color_treat': '#E8748A',
        'color_ctrl':  '#4DADA0',
        'treat_label': '+ABO (d4)',
        'samples': [
            dict(condition='control', rep=1, folder='4.1.26 Astro+-Neuron+-ABO__astro+neuron_control_rep1_results',    csv='4.1.26 Astro+-Neuron+-ABO__astro+neuron_control_rep1_AQuA2_Ch1.csv'),
            dict(condition='control', rep=2, folder='4.1.26 Astro+-Neuron+-ABO__astro+neuron_control_rep2_results',    csv='4.1.26 Astro+-Neuron+-ABO__astro+neuron_control_rep2_AQuA2_Ch1.csv'),
            dict(condition='control', rep=3, folder='4.1.26 Astro+-Neuron+-ABO__astro+neuron_control_rep3_results',    csv='4.1.26 Astro+-Neuron+-ABO__astro+neuron_control_rep3_AQuA2_Ch1.csv'),
            dict(condition='+ABO',    rep=1, folder='4.1.26 Astro+-Neuron+-ABO__astro+neuron_+_ABO_day4_rep1_results', csv='4.1.26 Astro+-Neuron+-ABO__astro+neuron_+_ABO_day4_rep1_AQuA2_Ch1.csv'),
            dict(condition='+ABO',    rep=2, folder='4.1.26 Astro+-Neuron+-ABO__astro+neuron_+_ABO_rep2_results',      csv='4.1.26 Astro+-Neuron+-ABO__astro+neuron_+_ABO_rep2_AQuA2_Ch1.csv'),
            dict(condition='+ABO',    rep=3, folder='4.1.26 Astro+-Neuron+-ABO__astro+neuron_+_ABO_rep3_results',      csv='4.1.26 Astro+-Neuron+-ABO__astro+neuron_+_ABO_rep3_AQuA2_Ch1.csv'),
        ],
    },
    {
        'id': '4.3.26',
        'label': 'Astro+Neuron — 4/3/26  (ABO day 6)',
        'color_treat': '#E8748A',
        'color_ctrl':  '#4DADA0',
        'treat_label': '+ABO (d6)',
        'samples': [
            dict(condition='control', rep=1, folder='4.3.26 Astro+-Neuron+-ABO__astro+neuron_control_rep1_results',    csv='4.3.26 Astro+-Neuron+-ABO__astro+neuron_control_rep1_AQuA2_Ch1.csv'),
            dict(condition='control', rep=2, folder='4.3.26 Astro+-Neuron+-ABO__astro+neuron_control_rep2_results',    csv='4.3.26 Astro+-Neuron+-ABO__astro+neuron_control_rep2_AQuA2_Ch1.csv'),
            dict(condition='control', rep=3, folder='4.3.26 Astro+-Neuron+-ABO__astro+neuron_control_rep3_results',    csv='4.3.26 Astro+-Neuron+-ABO__astro+neuron_control_rep3_AQuA2_Ch1.csv'),
            dict(condition='+ABO',    rep=1, folder='4.3.26 Astro+-Neuron+-ABO__astro+neuron_+_ABO_day6_rep1_results', csv='4.3.26 Astro+-Neuron+-ABO__astro+neuron_+_ABO_day6_rep1_AQuA2_Ch1.csv'),
            dict(condition='+ABO',    rep=2, folder='4.3.26 Astro+-Neuron+-ABO__astro+neuron_+ABO_rep2_results',       csv='4.3.26 Astro+-Neuron+-ABO__astro+neuron_+ABO_rep2_AQuA2_Ch1.csv'),
            dict(condition='+ABO',    rep=3, folder='4.3.26 Astro+-Neuron+-ABO__astro+neuron_+_ABO_rep3_results',      csv='4.3.26 Astro+-Neuron+-ABO__astro+neuron_+_ABO_rep3_AQuA2_Ch1.csv'),
        ],
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_csv(path):
    if not os.path.exists(path):
        print(f'  [MISSING] {path}')
        return {}
    with open(path) as f:
        rows = list(csv.reader(f))
    data = {}
    for row in rows:
        vals = []
        for v in row[1:]:
            try:   vals.append(float(v))
            except: pass
        if vals:
            data[row[0]] = vals
    return data


def pval_label(a, b):
    if len(a) < 2 or len(b) < 2:
        return 'n.s.'
    _, p = stats.ttest_ind(a, b)
    return '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'n.s.'


def bar_panel(ax, a_vals, c_vals, a_mean, c_mean, a_sem, c_sem,
              ylabel, panel_letter, treat_label, color_treat, color_ctrl):
    jitter = np.array([-0.07, 0.0, 0.07])
    for xi, vals, mean, sem, cond, col in [
        (0, a_vals, a_mean, a_sem, treat_label, color_treat),
        (1, c_vals, c_mean, c_sem, 'control',   color_ctrl),
    ]:
        ax.bar(xi, mean, yerr=sem, color=col, width=0.5,
               capsize=4, error_kw=dict(lw=1.2, capthick=1.2), zorder=2)
        j = jitter[:len(vals)]
        ax.scatter(xi + j, vals, color='white', edgecolors=col,
                   s=35, zorder=4, linewidths=1.2)
    n_pairs = min(len(a_vals), len(c_vals))
    for k in range(n_pairs):
        ax.plot([0 + jitter[k], 1 + jitter[k]], [a_vals[k], c_vals[k]],
                color='#666666', lw=0.7, alpha=0.5, zorder=3)
    ann = pval_label(a_vals, c_vals)
    ymax = max(np.nanmax(a_vals) if len(a_vals) else 0,
               np.nanmax(c_vals) if len(c_vals) else 0)
    ytop = ymax * 1.25
    ax.plot([0, 0, 1, 1], [ytop * 0.94, ytop, ytop, ytop * 0.94], lw=0.8, color='k')
    ax.text(0.5, ytop * 1.02, ann, ha='center', va='bottom', fontsize=9)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([treat_label, 'ctrl'], fontsize=7)
    ax.set_xlim(-0.6, 1.6)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.set_title(panel_letter, loc='left', fontweight='bold')


# ── Main loop — one figure per experiment ─────────────────────────────────────
all_records = []
all_summaries = []

for exp in EXPERIMENTS:
    eid = exp['id']
    print(f'\n=== {exp["label"]} ===')

    records = []
    for s in exp['samples']:
        path = os.path.join(BASE, s['folder'], s['csv'])
        data = parse_csv(path)
        n = len(next(iter(data.values()))) if data else 0
        print(f"  {s['condition']} rep{s['rep']}: {n} events")
        for i in range(n):
            get = lambda k: data.get(k, [np.nan] * n)[i]
            records.append({
                'experiment':  eid,
                'sample':      f"{s['condition']}_rep{s['rep']}",
                'condition':   s['condition'],
                'rep':         s['rep'],
                'event_idx':   i + 1,
                'start_frame': get('Starting Frame'),
                'area':        get('Basic - Area'),
                'max_dff':     get('Curve - Max Dff'),
                'dff_auc':     get('Curve - dff AUC'),
                'duration50':  get('Curve - Duration 50% to 50% based on averge dF/F'),
                'propagation': get('Propagation - onset - overall'),
            })

    df = pd.DataFrame(records)
    all_records.extend(records)

    treat_cond = [s['condition'] for s in exp['samples'] if s['condition'] != 'control'][0]
    summary = (
        df.groupby(['condition', 'rep'])
        .agg(n_events=('event_idx', 'count'),
             mean_area=('area', 'mean'),
             mean_dff=('max_dff', 'mean'),
             mean_auc=('dff_auc', 'mean'))
        .reset_index()
    )
    summary['experiment'] = eid
    all_summaries.append(summary)

    def get_vals(cond, col):
        sub = summary[summary.condition == cond][col].dropna().values.astype(float)
        return sub, sub.mean() if len(sub) else np.nan, (sub.std(ddof=1) / np.sqrt(len(sub)) if len(sub) > 1 else 0)

    BIN, MAX_FRAME = 30, 441
    fig = plt.figure(figsize=(14, 3.5))
    fig.suptitle(exp['label'], fontsize=10, fontweight='bold', y=1.01)
    axes = fig.subplots(1, 5)

    # Panel c — events over time
    ax = axes[0]
    bins = np.arange(0, MAX_FRAME + BIN, BIN)
    centers = (bins[:-1] + bins[1:]) / 2
    for cond, col in [(treat_cond, exp['color_treat']), ('control', exp['color_ctrl'])]:
        reps = sorted(df[df.condition == cond]['rep'].unique())
        counts = np.zeros((len(reps), len(centers)))
        for j, rep in enumerate(reps):
            frames = df[(df.condition == cond) & (df.rep == rep)]['start_frame'].dropna().values
            counts[j], _ = np.histogram(frames, bins=bins)
        mean_tr = counts.mean(axis=0)
        sem_tr  = counts.std(axis=0, ddof=1) / np.sqrt(counts.shape[0]) if counts.shape[0] > 1 else np.zeros_like(mean_tr)
        label = exp['treat_label'] if cond == treat_cond else 'control'
        ax.errorbar(centers, mean_tr, yerr=sem_tr, color=col, lw=1.5,
                    capsize=2, elinewidth=0.8, marker='o', markersize=3, label=label)
    ax.set_xlabel('Frame', fontsize=8)
    ax.set_ylabel('Ca²⁺ events / bin', fontsize=8)
    ax.set_title('c', loc='left', fontweight='bold')
    ax.legend(frameon=False, fontsize=7)

    # Panel d — area vs duration scatter
    ax = axes[1]
    sub_all = df.dropna(subset=['area', 'duration50', 'start_frame'])
    for cond, col in [(treat_cond, exp['color_treat']), ('control', exp['color_ctrl'])]:
        sub = sub_all[sub_all.condition == cond]
        if len(sub):
            ax.scatter(sub['duration50'], sub['area'], c=col, s=30,
                       alpha=0.7, label=cond, zorder=3, edgecolors='none')
    ax.set_xlabel('Duration 50–50 (fr)', fontsize=8)
    ax.set_ylabel('Area (px²)', fontsize=8)
    ax.set_title('d', loc='left', fontweight='bold')
    ax.legend(frameon=False, fontsize=7)

    # Panel e — event count
    a_v, a_m, a_s = get_vals(treat_cond, 'n_events')
    c_v, c_m, c_s = get_vals('control',  'n_events')
    bar_panel(axes[2], a_v, c_v, a_m, c_m, a_s, c_s,
              'Ca²⁺ events (n)', 'e', exp['treat_label'],
              exp['color_treat'], exp['color_ctrl'])

    # Panel f — area
    a_v, a_m, a_s = get_vals(treat_cond, 'mean_area')
    c_v, c_m, c_s = get_vals('control',  'mean_area')
    bar_panel(axes[3], a_v, c_v, a_m, c_m, a_s, c_s,
              'Area (px²)', 'f', exp['treat_label'],
              exp['color_treat'], exp['color_ctrl'])

    # Panel g — amplitude
    a_v, a_m, a_s = get_vals(treat_cond, 'mean_dff')
    c_v, c_m, c_s = get_vals('control',  'mean_dff')
    bar_panel(axes[4], a_v, c_v, a_m, c_m, a_s, c_s,
              'Max ΔF/F', 'g', exp['treat_label'],
              exp['color_treat'], exp['color_ctrl'])

    plt.tight_layout()
    fname = f'astro_neuron_{eid.replace(".", "_")}_figure.pdf'
    fig.savefig(os.path.join(BASE, fname), dpi=300, bbox_inches='tight')
    fname_png = fname.replace('.pdf', '.png')
    fig.savefig(os.path.join(BASE, fname_png), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  → saved {fname}')


# ── Excel summary ─────────────────────────────────────────────────────────────
df_all = pd.DataFrame(all_records)
df_sum = pd.concat(all_summaries, ignore_index=True)

out_xlsx = os.path.join(BASE, 'astro_neuron_AQuA2_summary.xlsx')
with pd.ExcelWriter(out_xlsx, engine='openpyxl') as writer:
    df_all.to_excel(writer, sheet_name='All Events', index=False)
    df_sum.to_excel(writer, sheet_name='Per-Sample Summary', index=False)

print(f'\nExcel summary → {out_xlsx}')
print('\n── Per-sample event counts ──────────────────────────────')
print(df_sum[['experiment', 'condition', 'rep', 'n_events']].to_string(index=False))
