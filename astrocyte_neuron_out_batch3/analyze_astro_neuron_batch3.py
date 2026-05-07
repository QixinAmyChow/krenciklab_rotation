"""
AQuA2 analysis — 3.25.26 day28 GCaMP8s Asteroids (spontaneous + ATP).
2 spontaneous reps + 1 +8ul ATP rep = 3 samples total.
Produces panels c-g + Excel summary.
Note: +ATP group has n=1, so no statistical comparison is drawn.
"""

import csv, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

plt.rcParams.update({
    'font.size': 9,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
})

BASE   = '/home/crnlqz/krenciklab/astrocyte+neuron_out_batch3'
STEM   = '3.25.26 day28 Asteroids GCaMP8s spont and ATP'
COLOR_SPONT = '#4DADA0'
COLOR_ATP   = '#E8748A'

SAMPLES = [
    dict(condition='spontaneous', rep=1,
         folder=f'{STEM}__rep1_spontaneous_results',
         csv=f'{STEM}__rep1_spontaneous_AQuA2_Ch1.csv'),
    dict(condition='spontaneous', rep=2,
         folder=f'{STEM}__rep2_spontaneous_results',
         csv=f'{STEM}__rep2_spontaneous_AQuA2_Ch1.csv'),
    dict(condition='+8ul ATP',    rep=3,
         folder=f'{STEM}__rep3_2min_+8ulATP_results',
         csv=f'{STEM}__rep3_2min_+8ulATP_AQuA2_Ch1.csv'),
]


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


records = []
for s in SAMPLES:
    path = os.path.join(BASE, s['folder'], s['csv'])
    data = parse_csv(path)
    n = len(next(iter(data.values()))) if data else 0
    print(f"  {s['condition']} rep{s['rep']}: {n} events")
    for i in range(n):
        get = lambda k, _i=i: data.get(k, [np.nan] * n)[_i]
        records.append({
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

summary = (
    df.groupby(['condition', 'rep'])
    .agg(n_events=('event_idx', 'count'),
         mean_area=('area', 'mean'),
         mean_dff=('max_dff', 'mean'),
         mean_auc=('dff_auc', 'mean'))
    .reset_index()
)

print('\n── Per-sample summary ──────────────────────────')
print(summary[['condition', 'rep', 'n_events', 'mean_area', 'mean_dff']].to_string(index=False))


def get_vals(cond, col):
    sub = summary[summary.condition == cond][col].dropna().values.astype(float)
    mean = sub.mean() if len(sub) else np.nan
    sem  = sub.std(ddof=1) / np.sqrt(len(sub)) if len(sub) > 1 else 0.0
    return sub, mean, sem


def bar_panel(ax, vals_dict, means_dict, sems_dict, ylabel, panel_letter):
    colors = {'spontaneous': COLOR_SPONT, '+8ul ATP': COLOR_ATP}
    labels = list(vals_dict.keys())
    jitter = np.array([-0.07, 0.0, 0.07])
    for xi, cond in enumerate(labels):
        vals = vals_dict[cond]
        col  = colors[cond]
        ax.bar(xi, means_dict[cond], yerr=sems_dict[cond], color=col, width=0.5,
               capsize=4, error_kw=dict(lw=1.2, capthick=1.2), zorder=2)
        j = jitter[:len(vals)]
        ax.scatter(xi + j, vals, color='white', edgecolors=col,
                   s=35, zorder=4, linewidths=1.2)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.set_title(panel_letter, loc='left', fontweight='bold')


BIN, MAX_FRAME = 30, 730
bins    = np.arange(0, MAX_FRAME + BIN, BIN)
centers = (bins[:-1] + bins[1:]) / 2

fig = plt.figure(figsize=(14, 3.5))
fig.suptitle('3.25.26 day28 GCaMP8s Asteroids — spontaneous vs +8ul ATP  (n=2 spont, n=1 ATP)',
             fontsize=9, fontweight='bold', y=1.01)
axes = fig.subplots(1, 5)

# Panel c — events over time
ax = axes[0]
for cond, col in [('spontaneous', COLOR_SPONT), ('+8ul ATP', COLOR_ATP)]:
    reps = sorted(df[df.condition == cond]['rep'].unique())
    counts = np.zeros((len(reps), len(centers)))
    for j, rep in enumerate(reps):
        frames = df[(df.condition == cond) & (df.rep == rep)]['start_frame'].dropna().values
        counts[j], _ = np.histogram(frames, bins=bins)
    mean_tr = counts.mean(axis=0)
    sem_tr  = counts.std(axis=0, ddof=1) / np.sqrt(counts.shape[0]) if counts.shape[0] > 1 else np.zeros_like(mean_tr)
    ax.errorbar(centers, mean_tr, yerr=sem_tr, color=col, lw=1.5,
                capsize=2, elinewidth=0.8, marker='o', markersize=3, label=cond)
ax.set_xlabel('Frame', fontsize=8)
ax.set_ylabel('Ca²⁺ events / bin', fontsize=8)
ax.set_title('c', loc='left', fontweight='bold')
ax.legend(frameon=False, fontsize=7)

# Panel d — area vs duration scatter
ax = axes[1]
sub_all = df.dropna(subset=['area', 'duration50'])
for cond, col in [('spontaneous', COLOR_SPONT), ('+8ul ATP', COLOR_ATP)]:
    sub = sub_all[sub_all.condition == cond]
    if len(sub):
        ax.scatter(sub['duration50'], sub['area'], c=col, s=30,
                   alpha=0.7, label=cond, zorder=3, edgecolors='none')
ax.set_xlabel('Duration 50–50 (fr)', fontsize=8)
ax.set_ylabel('Area (px²)', fontsize=8)
ax.set_title('d', loc='left', fontweight='bold')
ax.legend(frameon=False, fontsize=7)

# Panels e/f/g — bar plots
conds = ['spontaneous', '+8ul ATP']
for ax, col_key, ylabel, panel in [
    (axes[2], 'n_events', 'Ca²⁺ events (n)', 'e'),
    (axes[3], 'mean_area', 'Area (px²)',       'f'),
    (axes[4], 'mean_dff',  'Max ΔF/F',         'g'),
]:
    vals_d  = {c: get_vals(c, col_key)[0] for c in conds}
    means_d = {c: get_vals(c, col_key)[1] for c in conds}
    sems_d  = {c: get_vals(c, col_key)[2] for c in conds}
    bar_panel(ax, vals_d, means_d, sems_d, ylabel, panel)

plt.tight_layout()
fname = 'astro_neuron_3_25_26_figure.pdf'
fig.savefig(os.path.join(BASE, fname), dpi=300, bbox_inches='tight')
fig.savefig(os.path.join(BASE, fname.replace('.pdf', '.png')), dpi=150, bbox_inches='tight')
plt.close(fig)
print(f'\n→ saved {fname}')

# Excel summary
out_xlsx = os.path.join(BASE, 'astro_neuron_batch3_AQuA2_summary.xlsx')
with pd.ExcelWriter(out_xlsx, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='All Events', index=False)
    summary.to_excel(writer, sheet_name='Per-Sample Summary', index=False)
print(f'→ Excel summary: {out_xlsx}')
