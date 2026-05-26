"""Read and parse AQuA2 output files (CSV or .mat HDF5 v7.3)."""
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
    """Load AQuA2 results from a results folder (prefers .mat, falls back to CSV).

    Args:
        results_folder: Path to a *_results folder produced by AQuA2.
        channel:        Channel number (default 1); used only for CSV fallback.

    Returns:
        (n_events, metrics_dict) where metrics_dict is {metric: [values]}.

    Example:
        n, data = load("Coculture_rep1_+ABO_results/")
        print(n, "events detected")
    """
    folder = Path(results_folder)
    mat_matches = list(folder.glob("*_AQuA2.mat"))
    if mat_matches:
        return load_mat(mat_matches[0])
    csv_path = find_csv(results_folder, channel)
    data = parse_csv(csv_path)
    n_events = len(next(iter(data.values()))) if data else 0
    return n_events, data


def find_mat(results_folder):
    """Auto-discover the AQuA2 .mat file inside a results folder.

    Args:
        results_folder: Path to a *_results folder produced by AQuA2.

    Returns:
        Path to the .mat file.

    Raises:
        FileNotFoundError: if no .mat file is found.
        ValueError:        if multiple .mat files match (ambiguous).
    """
    folder = Path(results_folder)
    matches = list(folder.glob("*_AQuA2.mat"))
    if not matches:
        raise FileNotFoundError(f"No AQuA2 .mat file found in {folder}")
    if len(matches) > 1:
        raise ValueError(f"Multiple AQuA2 .mat files in {folder}: {[m.name for m in matches]}")
    return matches[0]


def parse_mat(mat_path):
    """Parse an AQuA2 HDF5 v7.3 .mat file → dict of {metric_name: [float, ...]}.

    Metric names match the AQuA2 CSV column headers so STANDARD_METRICS and
    quantify.py work identically whether data came from CSV or .mat.

    Args:
        mat_path: Path to the AQuA2 *_AQuA2.mat file.

    Returns:
        dict mapping metric names to lists of per-event float values.
    """
    import h5py

    def _vec(ds):
        """Flatten a (N,1) or (1,N) dataset to a Python list of floats."""
        arr = ds[:]
        if arr.ndim == 2 and arr.shape[1] == 1:
            arr = arr[:, 0]
        elif arr.ndim == 2 and arr.shape[0] == 1:
            arr = arr[0, :]
        return arr.astype(float).tolist()

    data = {}
    with h5py.File(mat_path, "r") as f:
        fts = f["res/fts1"]

        # AQuA2 omits feature datasets entirely when 0 events are detected.
        if "basic/area" not in fts:
            return data

        # ── basic ─────────────────────────────────────────────────────────
        data["Basic - Area"] = _vec(fts["basic/area"])
        data["Basic - Perimeter (only for 2D video)"] = _vec(fts["basic/peri"])
        data["Basic - Circularity"] = _vec(fts["basic/circMetric"])

        # ── curve ─────────────────────────────────────────────────────────
        data["Curve - Max Df"] = _vec(fts["curve/dfMax"])
        data["Curve - Max Dff"] = _vec(fts["curve/dffMax"])
        data["Curve - Duration of visualized event overlay"] = _vec(fts["curve/duration"])
        data["Curve - Duration 50% to 50% based on averge dF/F"] = _vec(fts["curve/width55"])
        data["Curve - Duration 10% to 10% based on averge dF/F"] = _vec(fts["curve/width11"])
        data["Curve - Rising duration 10% to 90% based on averge dF/F"] = _vec(fts["curve/rise19"])
        data["Curve - Decaying duration 90% to 10% based on averge dF/F"] = _vec(fts["curve/fall91"])
        data["Curve - dat AUC"] = _vec(fts["curve/datAUC"])
        data["Curve - df AUC"] = _vec(fts["curve/dfAUC"])
        data["Curve - dff AUC"] = _vec(fts["curve/dffAUC"])
        data["Curve - Decay tau"] = _vec(fts["curve/decayTau"])

        # ── propagation ───────────────────────────────────────────────────
        # propGrowOverall rows: [Anterior, Posterior, Left, Right]; overall = sum
        grow = fts["propagation/propGrowOverall"][:]   # (4, N)
        data["Propagation - onset - overall"] = grow.sum(axis=0).tolist()
        for i, direction in enumerate(["Anterior", "Posterior", "Left", "Right"]):
            data[f"Propagation - onset - one direction - {direction}"] = grow[i].tolist()

        shrink = fts["propagation/propShrinkOverall"][:]  # (4, N)
        data["Propagation - offset - overall"] = shrink.sum(axis=0).tolist()
        for i, direction in enumerate(["Anterior", "Posterior", "Left", "Right"]):
            data[f"Propagation - offset - one direction - {direction}"] = shrink[i].tolist()

        # ── network ───────────────────────────────────────────────────────
        nsl = fts["network/nOccurSameLoc"][:]   # (2, N)
        data["Network - number of events in the same location"] = nsl[0].tolist()
        data["Network - number of events in the same location with similar size only"] = nsl[1].tolist()
        data["Network - maximum number of events appearing at the same time"] = _vec(fts["network/nOccurSameTime"])

    return data


def prestim_dff(mat_path, atp_frame):
    """Compute per-event dF/F using pre-stimulus mean as F0.

    F0 = mean fluorescence of each event's spatial footprint over frames
    [0, atp_frame).  Returns an (n_frames, n_events) float32 array.

    Args:
        mat_path:  Path to *_AQuA2.mat.
        atp_frame: First frame of drug addition (0-based).
    """
    import h5py

    with h5py.File(mat_path, "r") as f:
        dat = f["res/datOrg1"][:, 0, :, :]   # (n_frames, H, W)  uint16
        dat = dat.astype(np.float32)
        n_frames, H, _ = dat.shape
        n_events = f["res/fts1/loc/xSpa"].shape[0]

        dff = np.zeros((n_frames, n_events), dtype=np.float32)

        for i in range(n_events):
            ref  = f["res/fts1/loc/xSpa"][i, 0]
            # MATLAB linear indices: 1-based, column-major (rows vary fastest)
            idx  = f[ref][:].astype(int).ravel() - 1
            rows = idx % H
            cols = idx // H

            F    = dat[:, rows, cols].mean(axis=1)    # (n_frames,)
            F0   = F[:atp_frame].mean()
            if F0 > 0:
                dff[:, i] = (F - F0) / F0

    return dff


def load_mat(mat_path):
    """Load AQuA2 results directly from a .mat file.

    Args:
        mat_path: Path to the AQuA2 *_AQuA2.mat file.

    Returns:
        (n_events, metrics_dict) where metrics_dict is {metric: [values]}.
    """
    data = parse_mat(mat_path)
    n_events = len(next(iter(data.values()))) if data else 0
    return n_events, data
