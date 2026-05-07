"""Read and parse AQuA2 output CSV files."""
import csv
from pathlib import Path
import numpy as np

STANDARD_METRICS = [
    "Basic - Area",
    "Curve - Max Dff",
    "Curve - Max Df",
    "Curve - Duration 50% to 50% based on averge dF/F",
    "Curve - Duration 10% to 10% based on averge dF/F",
    "Curve - Rising duration 10% to 90% based on averge dF/F",
    "Curve - Decaying duration 90% to 10% based on averge dF/F",
    "Curve - dff AUC",
    "Curve - df AUC",
    "Curve - Decay tau",
    "Propagation - onset - overall",
    "Network - number of events in the same location",
    "Network - maximum number of events appearing at the same time",
]


def parse_csv(path):
    """Parse an AQuA2 CSV file → dict of {metric_name: [float, ...]}.

    Each row in the AQuA2 CSV corresponds to one metric; columns are events.

    Args:
        path: Path to the AQuA2 CSV file.

    Returns:
        dict mapping metric names to lists of per-event float values.
    """
    with open(path) as f:
        rows = list(csv.reader(f))

    data = {}
    for row in rows:
        if not row:
            continue
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


def find_csv(results_folder, channel=1):
    """Auto-discover the AQuA2 CSV inside a results folder.

    AQuA2 saves one CSV per channel, named like:
        <experiment>_AQuA2_Ch1.csv

    Args:
        results_folder: Path to a *_results folder produced by AQuA2.
        channel:        Channel number (default 1).

    Returns:
        Path to the CSV file.

    Raises:
        FileNotFoundError: if no matching CSV is found.
        ValueError:        if multiple CSVs match (ambiguous).
    """
    folder = Path(results_folder)
    matches = list(folder.glob(f"*_AQuA2_Ch{channel}.csv"))
    if not matches:
        raise FileNotFoundError(
            f"No AQuA2 Ch{channel} CSV found in {folder}.\n"
            f"Expected a file matching *_AQuA2_Ch{channel}.csv"
        )
    if len(matches) > 1:
        raise ValueError(f"Multiple AQuA2 CSVs in {folder}: {[m.name for m in matches]}")
    return matches[0]


def load(results_folder, channel=1):
    """Load AQuA2 results from a results folder.

    Args:
        results_folder: Path to a *_results folder produced by AQuA2.
        channel:        Channel number (default 1).

    Returns:
        (n_events, metrics_dict) where metrics_dict is {metric: [values]}.

    Example:
        n, data = load_aqua2("Coculture_rep1_+ABO_results/")
        print(n, "events detected")
    """
    csv_path = find_csv(results_folder, channel)
    data = parse_csv(csv_path)
    n_events = len(next(iter(data.values()))) if data else 0
    return n_events, data
