"""
AQuA2 calcium imaging quantification for coculture experiment (3/17).
6 samples: 3 replicates x 2 conditions (+ABO, control)
Reads Ch1 CSV files, computes per-sample summary stats, writes Excel output.
"""

import csv
import os
import numpy as np
import pandas as pd

BASE = '/home/crnlqz/krenciklab/coculture_3_17_out'

SAMPLES = [
    {
        'name': 'rep1_+ABO',
        'condition': '+ABO',
        'replicate': 1,
        'folder': 'Coculture_rep1_+ABO_results',
        'csv': 'Coculture_rep1_+ABO_AQuA2_Ch1.csv',
    },
    {
        'name': 'rep1_control',
        'condition': 'control',
        'replicate': 1,
        'folder': 'Coculture_rep1_control_results',
        'csv': 'Coculture_rep1_control_AQuA2_Ch1.csv',
    },
    {
        'name': 'rep2_+ABO',
        'condition': '+ABO',
        'replicate': 2,
        'folder': 'Coculture_rep2_+ABO_results',
        'csv': 'Coculture_rep2_+ABO_AQuA2_Ch1.csv',
    },
    {
        'name': 'rep2_control',
        'condition': 'control',
        'replicate': 2,
        'folder': 'Coculture_rep2+control_results',
        'csv': 'Coculture_rep2+control_AQuA2_Ch1.csv',
    },
    {
        'name': 'rep3_+ABO',
        'condition': '+ABO',
        'replicate': 3,
        'folder': 'Coculture_rep3_+ABO_results',
        'csv': 'Coculture_rep3_+ABO_AQuA2_Ch1.csv',
    },
    {
        'name': 'rep3_control',
        'condition': 'control',
        'replicate': 3,
        'folder': 'Coculture_rep3+control_results',
        'csv': 'Coculture_rep3+control_AQuA2_Ch1.csv',
    },
]

# Metrics of interest (row labels in CSV)
METRICS = [
    'Basic - Area',
    'Curve - Max Dff',
    'Curve - Max Df',
    'Curve - Duration 50% to 50% based on averge dF/F',
    'Curve - Duration 10% to 10% based on averge dF/F',
    'Curve - Rising duration 10% to 90% based on averge dF/F',
    'Curve - Decaying duration 90% to 10% based on averge dF/F',
    'Curve - dff AUC',
    'Curve - df AUC',
    'Curve - Decay tau',
    'Propagation - onset - overall',
    'Network - number of events in the same location',
    'Network - maximum number of events appearing at the same time',
]


def parse_csv(path):
    """Parse AQuA2 CSV → dict of {metric: [values]}"""
    with open(path) as f:
        reader = csv.reader(f)
        rows = list(reader)

    data = {}
    for row in rows:
        label = row[0]
        values = []
        for v in row[1:]:
            try:
                values.append(float(v))
            except (ValueError, TypeError):
                pass
        if values:
            data[label] = values
    return data


def summarize(values):
    if not values:
        return {
            'n': 0, 'mean': np.nan, 'median': np.nan,
            'std': np.nan, 'min': np.nan, 'max': np.nan,
        }
    arr = np.array(values, dtype=float)
    return {
        'n': len(arr),
        'mean': np.mean(arr),
        'median': np.median(arr),
        'std': np.std(arr, ddof=1) if len(arr) > 1 else np.nan,
        'min': np.min(arr),
        'max': np.max(arr),
    }


# ── 1. Per-event data (long format) ───────────────────────────────────────────
all_events = []
sample_summaries = []

for s in SAMPLES:
    path = os.path.join(BASE, s['folder'], s['csv'])
    data = parse_csv(path)
    n_events = len(next(iter(data.values()))) if data else 0

    print(f"{s['name']}: {n_events} events")

    for ev_idx in range(n_events):
        row = {
            'sample': s['name'],
            'condition': s['condition'],
            'replicate': s['replicate'],
            'event_index': ev_idx + 1,
        }
        for metric in METRICS:
            vals = data.get(metric, [])
            row[metric] = vals[ev_idx] if ev_idx < len(vals) else np.nan
        all_events.append(row)

    # Per-sample summary
    summary = {
        'sample': s['name'],
        'condition': s['condition'],
        'replicate': s['replicate'],
        'n_events': n_events,
    }
    for metric in METRICS:
        vals = data.get(metric, [])
        stats = summarize(vals)
        for stat, val in stats.items():
            if stat == 'n':
                continue  # already stored as n_events
            summary[f"{metric} [{stat}]"] = val
    sample_summaries.append(summary)


# ── 2. Condition-level summary (mean of per-sample means) ─────────────────────
df_sum = pd.DataFrame(sample_summaries)
cond_summary_rows = []
for cond in ['+ABO', 'control']:
    sub = df_sum[df_sum['condition'] == cond]
    row = {'condition': cond, 'n_replicates': len(sub)}
    # event count stats
    row['n_events mean'] = sub['n_events'].mean()
    row['n_events sem'] = sub['n_events'].sem()
    for metric in METRICS:
        col = f"{metric} [mean]"
        if col in sub.columns:
            row[f"{metric} [mean of means]"] = sub[col].mean()
            row[f"{metric} [SEM of means]"] = sub[col].sem()
    cond_summary_rows.append(row)
df_cond = pd.DataFrame(cond_summary_rows)


# ── 3. Write Excel ─────────────────────────────────────────────────────────────
out_path = os.path.join(BASE, 'coculture_3_17_AQuA2_summary.xlsx')
df_events = pd.DataFrame(all_events)

with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
    df_events.to_excel(writer, sheet_name='All Events', index=False)
    df_sum.to_excel(writer, sheet_name='Per-Sample Summary', index=False)
    df_cond.to_excel(writer, sheet_name='Condition Summary', index=False)

print(f"\nOutput written to: {out_path}")
print("\n── Condition Summary ─────────────────────────────────────────────")
print(df_cond[['condition', 'n_replicates', 'n_events mean', 'n_events sem']].to_string(index=False))
print("\n── Per-sample event counts ───────────────────────────────────────")
print(df_sum[['sample', 'condition', 'replicate', 'n_events']].to_string(index=False))

# Print key metrics table
print("\n── Key metrics (mean ± SEM across replicates) ────────────────────")
key = ['Curve - Max Dff', 'Basic - Area', 'Curve - dff AUC',
       'Curve - Duration 50% to 50% based on averge dF/F']
for metric in key:
    mean_col = f"{metric} [mean of means]"
    sem_col = f"{metric} [SEM of means]"
    if mean_col in df_cond.columns:
        print(f"\n{metric}")
        for _, r in df_cond.iterrows():
            print(f"  {r['condition']}: {r[mean_col]:.4f} ± {r[sem_col]:.4f}")
