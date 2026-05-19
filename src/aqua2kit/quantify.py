"""Quantify AQuA2 events per sample and condition."""
import numpy as np
import pandas as pd
from pathlib import Path
from .aqua2_io import load, STANDARD_METRICS


def _stats(values):
    if not values:
        return {"n": 0, "mean": np.nan, "median": np.nan, "std": np.nan, "sem": np.nan}
    arr = np.array(values, dtype=float)
    n = len(arr)
    return {
        "n": n,
        "mean": np.mean(arr),
        "median": np.median(arr),
        "std": np.std(arr, ddof=1) if n > 1 else np.nan,
        "sem": np.std(arr, ddof=1) / np.sqrt(n) if n > 1 else np.nan,
    }


def quantify_samples(samples, metrics=None, channel=1):
    """Quantify a list of AQuA2 samples.

    Args:
        samples: list of dicts, each with at minimum:
                   'folder'    — path to the AQuA2 *_results folder
                   'condition' — condition label, e.g. 'control' or '+ABO'
                   'replicate' — replicate number
                 Any extra keys (e.g. 'experiment', 'cell_type') are kept as
                 metadata columns in the output DataFrames.
        metrics: list of AQuA2 metric names to extract.
                 Defaults to STANDARD_METRICS (all 13 standard metrics).
        channel: AQuA2 channel number (default 1).

    Returns:
        (events_df, summary_df)
          events_df   — one row per detected Ca²⁺ event (long format)
          summary_df  — one row per sample (mean/median/std/sem per metric)

    Example:
        samples = [
            {"folder": "rep1_control_results", "condition": "control", "replicate": 1},
            {"folder": "rep1_ABO_results",     "condition": "+ABO",    "replicate": 1},
        ]
        events, summary = quantify_samples(samples)
    """
    if metrics is None:
        metrics = STANDARD_METRICS

    all_events = []
    sample_summaries = []

    for s in samples:
        folder = s["folder"]
        meta = {k: v for k, v in s.items() if k != "folder"}
        n_events, data = load(folder, channel=channel)
        print(f"  {Path(folder).name}: {n_events} events")

        for ev_idx in range(n_events):
            row = {**meta, "event_index": ev_idx + 1}
            for metric in metrics:
                vals = data.get(metric, [])
                row[metric] = vals[ev_idx] if ev_idx < len(vals) else np.nan
            all_events.append(row)

        summary = {**meta, "n_events": n_events}
        for metric in metrics:
            vals = data.get(metric, [])
            for stat, val in _stats(vals).items():
                if stat == "n":
                    continue
                summary[f"{metric} [{stat}]"] = val
        sample_summaries.append(summary)

    return pd.DataFrame(all_events), pd.DataFrame(sample_summaries)


def condition_summary(summary_df, group_by="condition", metrics=None):
    """Aggregate per-sample summaries to condition level (mean ± SEM across replicates).

    Args:
        summary_df: output of quantify_samples (summary_df).
        group_by:   column to group by (default 'condition').
        metrics:    metric names to aggregate (default STANDARD_METRICS).

    Returns:
        DataFrame with one row per condition.
    """
    if metrics is None:
        metrics = STANDARD_METRICS

    if summary_df.empty or group_by not in summary_df.columns:
        return pd.DataFrame()

    rows = []
    for cond, grp in summary_df.groupby(group_by):
        row = {
            group_by: cond,
            "n_replicates": len(grp),
            "n_events mean": grp["n_events"].mean(),
            "n_events sem": grp["n_events"].sem(),
        }
        for metric in metrics:
            col = f"{metric} [mean]"
            if col in grp.columns:
                row[f"{metric} [mean]"] = grp[col].mean()
                row[f"{metric} [sem]"] = grp[col].sem()
        rows.append(row)
    return pd.DataFrame(rows)


def to_excel(events_df, summary_df, out_path, cond_df=None):
    """Write quantification results to an Excel file.

    Args:
        events_df:   long-format events DataFrame.
        summary_df:  per-sample summary DataFrame.
        out_path:    output .xlsx path.
        cond_df:     optional condition-level summary DataFrame.
    """
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        events_df.to_excel(writer, sheet_name="All Events", index=False)
        summary_df.to_excel(writer, sheet_name="Per-Sample Summary", index=False)
        if cond_df is not None:
            cond_df.to_excel(writer, sheet_name="Condition Summary", index=False)
    print(f"Saved: {out_path}")
