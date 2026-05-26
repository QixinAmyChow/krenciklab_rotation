"""General utilities for aqua2kit."""
import numpy as np


def inspect_mat(mat_path):
    """Print the contents of an AQuA2 .mat HDF5 file to console.

    Args:
        mat_path: Path to *_AQuA2.mat.
    """
    import h5py
    import numpy as np
    from pathlib import Path

    KNOWN = {
        "datOrg1":               "raw fluorescence movie  uint16",
        "dF1":                   "delta-F movie",
        "dffMat1":               "[mean/max] x frames x events — precomputed dF/F traces",
        "dMat1":                 "[mean/max] x frames x events — precomputed dF traces",
        "evt1":                  "per-event object refs",
        "riseLst1":              "per-event rise-frame lists",
        "t0":                    "event start frame",
        "t1":                    "event end frame",
        "xSpa":                  "spatial footprint pixel indices (HDF5 object refs, MATLAB 1-based col-major)",
        "xSpaTemp":              "spatiotemporal footprint refs (per-frame pixel lists)",
        "area":                  "footprint area (px²)",
        "peri":                  "perimeter (px)",
        "circMetric":            "circularity  4π·area/perimeter²",
        "center":                "centroid",
        "map":                   "binary footprint map",
        "dffMax":                "peak dF/F",
        "dfMax":                 "peak dF",
        "dffAUC":                "dF/F area under curve",
        "dfAUC":                 "dF area under curve",
        "datAUC":                "raw F area under curve",
        "duration":              "event duration (frames)",
        "rise19":                "rise time 10→90% (frames)",
        "fall91":                "decay time 90→10% (frames)",
        "width55":               "half-width at 50% amplitude (frames)",
        "width11":               "width at 10% amplitude (frames)",
        "decayTau":              "decay tau (frames)",
        "dffMaxFrame":           "frame index of peak dF/F",
        "tBegin":                "curve fit start frame",
        "tEnd":                  "curve fit end frame",
        "propGrowOverall":       "wave onset speed  [Anterior, Posterior, Left, Right]",
        "propShrinkOverall":     "wave offset speed  [Anterior, Posterior, Left, Right]",
        "avgPropSpeed":          "mean propagation speed",
        "maxPropSpeed":          "max propagation speed",
        "nOccurSameTime":        "co-active events at same time",
        "nOccurSameLoc":         "co-active events at same location",
        "sz":                    "[W, H, C, T] — width, height, channels, frames",
        "maxVal":                "global max pixel value",
        "bd":                    "bounding box of analysis region",
        "ov":                    "overlap parameters",
    }

    def _row(name, shape, indent="  "):
        note = KNOWN.get(name, "")
        note_str = f"  # {note}" if note else ""
        print(f"{indent}{name:<26} {str(shape):<22}{note_str}")

    with h5py.File(mat_path, "r") as f:
        sz = f["res/opts/sz"][:].ravel().astype(int)
        W, H, C, T = sz
        n = f["res/fts1/loc/xSpa"].shape[0]

        print(f"File     : {Path(mat_path).name}")
        print(f"Recording: {W}x{H} px  {C} ch  {T} frames  {n} events")
        print()

        print("res/")
        print()
        print("  # Raw data")
        for key in ["datOrg1", "dF1", "dffMat1", "dMat1"]:
            try:
                _row(key, f[f"res/{key}"].shape)
            except KeyError:
                pass

        print()
        print("  # Event list")
        for key in ["evt1", "riseLst1"]:
            try:
                _row(key, f[f"res/{key}"].shape)
            except KeyError:
                pass

        print()
        print("  fts1/  # per-event features")

        groups = {
            "loc":         ["t0", "t1", "xSpa", "xSpaTemp"],
            "basic":       ["area", "peri", "circMetric", "center", "map"],
            "curve":       ["dffMax", "dfMax", "dffAUC", "dfAUC", "datAUC",
                            "duration", "rise19", "fall91", "width55", "width11",
                            "decayTau", "dffMaxFrame", "tBegin", "tEnd"],
            "propagation": ["propGrowOverall", "propShrinkOverall",
                            "avgPropSpeed", "maxPropSpeed"],
            "network":     ["nOccurSameTime", "nOccurSameLoc"],
        }

        for grp, keys in groups.items():
            print(f"    {grp}/")
            for key in keys:
                path = f"res/fts1/{grp}/{key}"
                try:
                    _row(key, f[path].shape, indent="      ")
                except KeyError:
                    pass

        print()
        print("  # Metadata")
        for key in ["sz", "maxVal", "bd", "ov"]:
            try:
                _row(key, f[f"res/opts/{key}"].shape)
            except KeyError:
                try:
                    _row(key, f[f"res/{key}"].shape)
                except KeyError:
                    pass


def cell_oscillation_freq(mat_path, label_map_path, atp_frame, fps,
                          min_prominence=0.05, min_distance=3):
    """Compute Ca2+ oscillation frequency pre/post ATP for each cell.

    Extracts each cell's mean fluorescence trace from the raw movie,
    counts peaks (rise-fall cycles) in pre and post ATP windows,
    returns frequency in cycles/min.

    Args:
        mat_path:       Path to *_AQuA2.mat.
        label_map_path: Path to *_label_map.tif.
        atp_frame:      First frame of ATP addition (0-based).
        fps:            True frame rate in Hz.
        min_prominence: Minimum peak prominence as fraction of trace std
                        (default 0.05 — filters noise).
        min_distance:   Minimum frames between peaks (default 3).

    Returns:
        List of dicts, one per cell:
          cell_id, freq_pre, freq_post  (cycles/min),
          n_peaks_pre, n_peaks_post, trace  (full fluorescence trace)
    """
    import h5py
    import numpy as np
    import tifffile
    from scipy.signal import find_peaks

    lmap = tifffile.imread(label_map_path)
    cell_ids = sorted(c for c in np.unique(lmap) if c != 0)

    pre_sec  = atp_frame / fps
    post_sec = None  # filled after loading T

    results = []

    with h5py.File(mat_path, "r") as f:
        dat = f["res/datOrg1"][:, 0, :, :].astype(np.float32)  # (T, H, W)
        T = dat.shape[0]

    post_sec = (T - atp_frame) / fps

    for cell_id in cell_ids:
        mask = lmap == cell_id
        if mask.sum() == 0:
            continue

        # mean fluorescence trace for this cell
        trace = dat[:, mask].mean(axis=1)   # (T,)

        # normalise: dF/F relative to full-trace mean as F0
        F0 = trace.mean()
        if F0 <= 0:
            continue
        dff_trace = (trace - F0) / F0

        prominence = min_prominence * dff_trace.std()

        pre_trace  = dff_trace[:atp_frame]
        post_trace = dff_trace[atp_frame:]

        pre_peaks,  _ = find_peaks(pre_trace,  prominence=prominence,
                                   distance=min_distance)
        post_peaks, _ = find_peaks(post_trace, prominence=prominence,
                                   distance=min_distance)

        results.append({
            "cell_id":      int(cell_id),
            "n_peaks_pre":  len(pre_peaks),
            "n_peaks_post": len(post_peaks),
            "freq_pre":     len(pre_peaks)  / pre_sec  * 60,
            "freq_post":    len(post_peaks) / post_sec * 60,
            "trace":        dff_trace,
        })

    return results


def cell_event_rates(mat_path, label_map_path, atp_frame, fps,
                     overlap_threshold=0.0, min_frame=2):
    """Compute pre/post ATP event rate for each cell (ROI).

    Args:
        mat_path:          Path to *_AQuA2.mat.
        label_map_path:    Path to *_label_map.tif.
        atp_frame:         First frame of ATP addition (0-based).
        fps:               True frame rate in Hz.
        overlap_threshold: Min overlap fraction for event assignment.
        min_frame:         Exclude events with t0 <= this.

    Returns:
        List of dicts, one per cell:
          cell_id, n_pre, n_post, rate_pre, rate_post  (rates in events/min)
    """
    import h5py
    import numpy as np

    assignments = assign_events_to_cells(mat_path, label_map_path, overlap_threshold)

    with h5py.File(mat_path, "r") as f:
        t0_all = f["res/fts1/loc/t0"][:, 0].astype(int)
        T = int(f["res/opts/sz"][3, 0])

    pre_sec  = atp_frame / fps
    post_sec = (T - atp_frame) / fps

    # build event_idx → t0 map (1-based)
    t0_map = {i + 1: int(t0_all[i]) for i in range(len(t0_all))}

    # group events by cell
    from collections import defaultdict
    cell_events = defaultdict(list)
    for a in assignments:
        if a["cell_id"] == 0:
            continue
        t0 = t0_map[a["event_idx"]]
        if t0 <= min_frame:
            continue
        cell_events[a["cell_id"]].append(t0)

    results = []
    for cell_id, onsets in sorted(cell_events.items()):
        onsets = np.array(onsets)
        n_pre  = int((onsets < atp_frame).sum())
        n_post = int((onsets >= atp_frame).sum())
        results.append({
            "cell_id":   cell_id,
            "n_pre":     n_pre,
            "n_post":    n_post,
            "rate_pre":  n_pre  / pre_sec  * 60,
            "rate_post": n_post / post_sec * 60,
        })

    return results


def assign_events_to_cells(mat_path, label_map_path, overlap_threshold=0.0):
    """Assign each AQuA2 event to the cell it most overlaps with.

    Uses the label_map.tif produced by AQuA2 (pixel value = cell ID, 0 = background)
    and each event's spatial footprint (xSpa) to find the best-matching cell.

    Args:
        mat_path:          Path to *_AQuA2.mat.
        label_map_path:    Path to *_label_map.tif.
        overlap_threshold: Minimum fraction of event footprint that must overlap
                           a cell to count as assigned (default 0.0 = any overlap).

    Returns:
        List of dicts, one per event:
          event_idx      : 1-based event index
          cell_id        : assigned cell label (0 = unassigned / background)
          overlap_px     : number of overlapping pixels with assigned cell
          footprint_px   : total event footprint size
          overlap_frac   : overlap_px / footprint_px
          all_cells      : dict of {cell_id: overlap_px} for all overlapping cells
    """
    import h5py
    import numpy as np
    import tifffile

    lmap = tifffile.imread(label_map_path)
    H = lmap.shape[0]

    results = []

    with h5py.File(mat_path, "r") as f:
        n_events = f["res/fts1/loc/xSpa"].shape[0]

        for i in range(n_events):
            ref  = f["res/fts1/loc/xSpa"][i, 0]
            idx  = f[ref][:].astype(int).ravel() - 1
            rows = idx % H
            cols = idx // H

            labels = lmap[rows, cols]
            footprint_px = len(labels)

            cell_ids, counts = np.unique(labels, return_counts=True)
            all_cells = {int(c): int(n) for c, n in zip(cell_ids, counts)}

            # exclude background (0)
            nonbg = {c: n for c, n in all_cells.items() if c != 0}

            if nonbg:
                best_cell = max(nonbg, key=nonbg.get)
                overlap_px = nonbg[best_cell]
                overlap_frac = overlap_px / footprint_px
            else:
                best_cell, overlap_px, overlap_frac = 0, 0, 0.0

            if overlap_frac < overlap_threshold:
                best_cell = 0

            results.append({
                "event_idx":    i + 1,
                "cell_id":      best_cell,
                "overlap_px":   overlap_px,
                "footprint_px": footprint_px,
                "overlap_frac": round(overlap_frac, 4),
                "all_cells":    all_cells,
            })

    return results


def print_cell_assignments(mat_path, label_map_path, overlap_threshold=0.0):
    """Print event-to-cell assignments to console.

    Args:
        mat_path:          Path to *_AQuA2.mat.
        label_map_path:    Path to *_label_map.tif.
        overlap_threshold: Minimum overlap fraction to assign (default 0.0).
    """
    assignments = assign_events_to_cells(mat_path, label_map_path, overlap_threshold)

    assigned   = [a for a in assignments if a["cell_id"] != 0]
    unassigned = [a for a in assignments if a["cell_id"] == 0]

    from collections import defaultdict
    cell_events = defaultdict(list)
    for a in assigned:
        cell_events[a["cell_id"]].append(a["event_idx"])

    print(f"Events: {len(assignments)}  "
          f"assigned: {len(assigned)}  "
          f"unassigned (background): {len(unassigned)}")
    print(f"Cells with events: {len(cell_events)}")
    print()
    print(f"{'Event':>6}  {'Cell':>6}  {'Overlap':>8}  {'Frac':>6}  All cells")
    print("-" * 60)
    for a in assignments:
        cells_str = ", ".join(f"{c}:{n}" for c, n in sorted(a["all_cells"].items()) if c != 0)
        print(f"{a['event_idx']:>6}  {a['cell_id']:>6}  "
              f"{a['overlap_px']:>8}  {a['overlap_frac']:>6.3f}  {cells_str}")
    print()
    print("Events per cell:")
    for cell_id in sorted(cell_events):
        print(f"  cell {cell_id:3d}: {len(cell_events[cell_id])} events  "
              f"{cell_events[cell_id]}")


def _ema_2sided_detrend(F, smoothness):
    """Return F / baseline where baseline is the average of forward and backward EMA.

    smoothness = k sets EMA weight p = 2/(k+1). Larger k → slower baseline.
    Applied per window (pre/post ATP) independently to avoid edge contamination.
    """
    T = len(F)
    p = 2.0 / (smoothness + 1)
    q = 1.0 - p

    ema_fwd = np.empty(T)
    ema_fwd[0] = F[0]
    for t in range(1, T):
        ema_fwd[t] = p * F[t] + q * ema_fwd[t - 1]

    ema_bwd = np.empty(T)
    ema_bwd[-1] = F[-1]
    for t in range(T - 2, -1, -1):
        ema_bwd[t] = p * F[t] + q * ema_bwd[t + 1]

    smoother = (ema_fwd + ema_bwd) * 0.5
    return F / np.maximum(smoother, 1e-6)


def _peakcaller_detect(detrended, rise, fall, lookback, lookahead):
    """Two-pass peak detection from Bhatt et al. 2017 (PeakCaller, BMC Neuroscience).

    Forward pass: for each local maximum, verify a rise of `rise` fraction within
    `lookback` frames before, and a fall of `fall` fraction within `lookahead` frames
    after. Backward pass: remove a peak if the valley to the next peak never drops
    below (1-fall)*peak_height (i.e., the signal never actually recovered).
    Returns array of peak frame indices into the input array.
    """
    T = len(detrended)
    candidates = [t for t in range(1, T - 1)
                  if detrended[t] > detrended[t - 1] and detrended[t] > detrended[t + 1]]

    provisional = []
    last_peak = 0
    for jj in candidates:
        lb_start = max(last_peak, jj - lookback)
        min_before = detrended[lb_start:jj].min() if jj > lb_start else detrended[jj]
        if min_before >= (1 - rise) * detrended[jj]:
            continue

        cap = jj + 1
        while cap < T and detrended[cap] < detrended[jj]:
            cap += 1
        la_end = min(cap, jj + lookahead)
        if la_end <= jj + 1:
            continue
        min_after = detrended[jj + 1:la_end].min()
        if min_after >= (1 - fall) * detrended[jj]:
            continue

        provisional.append(jj)
        last_peak = jj

    if not provisional:
        return np.array([], dtype=int)

    keep = [True] * len(provisional)
    for k in range(len(provisional) - 1):
        pk  = provisional[k]
        nxt = provisional[k + 1]
        seg = detrended[pk + 1:nxt]
        if len(seg) > 0 and seg.min() >= (1 - fall) * detrended[pk]:
            keep[k] = False

    return np.array([provisional[k] for k in range(len(provisional)) if keep[k]])


def cell_peakcaller(mat_path, label_map_path, atp_frame, fps,
                    ema_smoothness=40, rise=0.10, fall=0.10,
                    lookback_frames=5, lookahead_frames=8):
    """PeakCaller-style Ca2+ peak analysis per cell, pre/post ATP.

    Replicates the Cvetkovic et al. (Krencik lab) / Bhatt et al. 2017 pipeline:
    extract per-cell mean fluorescence from datOrg1 + label_map, apply EMA
    2-sided detrending, then detect peaks with the two-pass lookback/lookahead
    algorithm from PeakCaller.

    Args:
        mat_path:         Path to *_AQuA2.mat.
        label_map_path:   Path to *_label_map.tif.
        atp_frame:        First frame of ATP addition (0-based).
        fps:              True frame rate in Hz.
        ema_smoothness:   EMA window k — larger = slower baseline adaptation.
        rise:             Required rise fraction above local min (default 0.10).
        fall:             Required fall fraction after peak (default 0.10).
        lookback_frames:  Frames to look back for rise detection (default 5).
        lookahead_frames: Frames to look ahead for fall detection (default 8).

    Returns:
        List of dicts, one per cell:
          cell_id, n_peaks_pre, n_peaks_post,
          freq_pre, freq_post (peaks/min),
          peaks_pre, peaks_post (frame indices),
          trace_raw, trace_detrended
    """
    import h5py
    import tifffile

    lmap = tifffile.imread(label_map_path)
    cell_ids = sorted(c for c in np.unique(lmap) if c != 0)

    with h5py.File(mat_path, "r") as f:
        dat = f["res/datOrg1"][:, 0, :, :].astype(np.float32)  # (T, H, W)
        T = dat.shape[0]

    pre_sec  = atp_frame / fps
    post_sec = (T - atp_frame) / fps

    results = []
    for cell_id in cell_ids:
        mask = lmap == cell_id
        if mask.sum() == 0:
            continue

        F = dat[:, mask].mean(axis=1)
        if F.mean() <= 0:
            continue

        # Detrend each window independently: prevents the backward EMA of the
        # pre-ATP segment from being contaminated by the post-ATP Ca2+ surge.
        F_pre  = F[:atp_frame]
        F_post = F[atp_frame:]
        det_pre  = _ema_2sided_detrend(F_pre,  ema_smoothness)
        det_post = _ema_2sided_detrend(F_post, ema_smoothness)

        peaks_pre    = _peakcaller_detect(det_pre,  rise, fall, lookback_frames, lookahead_frames)
        peaks_post_r = _peakcaller_detect(det_post, rise, fall, lookback_frames, lookahead_frames)
        peaks_post   = peaks_post_r + atp_frame  # convert to absolute frame indices

        freq_pre  = len(peaks_pre)    / pre_sec  * 60 if pre_sec  > 0 else 0.0
        freq_post = len(peaks_post_r) / post_sec * 60 if post_sec > 0 else 0.0
        fold_change = freq_post / freq_pre if freq_pre > 0 else np.nan

        results.append({
            "cell_id":              int(cell_id),
            "n_peaks_pre":          len(peaks_pre),
            "n_peaks_post":         len(peaks_post_r),
            "freq_pre":             freq_pre,
            "freq_post":            freq_post,
            "fold_change":          fold_change,
            "peaks_pre":            peaks_pre,
            "peaks_post":           peaks_post,
            "trace_raw":            F,
            "trace_detrended_pre":  det_pre,
            "trace_detrended_post": det_post,
        })

    return results


def print_event_features(mat_path, atp_frame, fps, prop_threshold=3.0, min_frame=2):
    """Print per-event features: area, duration, speed, direction, location, phase.

    Args:
        mat_path:       Path to *_AQuA2.mat.
        atp_frame:      First frame of ATP addition (0-based).
        fps:            True frame rate in Hz.
        prop_threshold: avgPropSpeed below which an event is Static (default 3.0 px/frame).
        min_frame:      Exclude events with t0 <= this (default 2).
    """
    import h5py

    DIRS = ["Anterior", "Posterior", "Left", "Right"]

    with h5py.File(mat_path, "r") as f:
        n = f["res/fts1/loc/xSpa"].shape[0]
        t0_all       = f["res/fts1/loc/t0"][:, 0].astype(int)
        area_all     = f["res/fts1/basic/area"][:, 0].astype(float)
        duration_all = f["res/fts1/curve/duration"][:, 0].astype(float)
        speed_all    = f["res/fts1/propagation/avgPropSpeed"][:, 0].astype(float)
        prop_grow    = f["res/fts1/propagation/propGrowOverall"][:]  # (4, n)

        centers = []
        for i in range(n):
            ref = f["res/fts1/basic/center"][i, 0]
            c = f[ref][:].ravel()
            centers.append((float(c[1]) - 1, float(c[0]) - 1))  # (x_col, y_row) 0-based

    print(f"{'Evt':>4}  {'t0':>5}  {'Phase':>7}  "
          f"{'Area(px²)':>9}  {'Dur(fr)':>7}  {'Dur(s)':>6}  "
          f"{'Speed(px/fr)':>12}  {'Direction':>10}  "
          f"{'X(col)':>7}  {'Y(row)':>7}")
    print("-" * 95)

    for i in range(n):
        t0 = t0_all[i]
        if t0 <= min_frame:
            continue

        phase = "pre" if t0 < atp_frame else "post"

        speed = speed_all[i]
        if speed < prop_threshold:
            direction = "Static"
        else:
            direction = DIRS[int(np.argmax(prop_grow[:, i]))]

        dur_s = duration_all[i] / fps
        x, y  = centers[i]

        print(f"{i+1:>4}  {t0:>5}  {phase:>7}  "
              f"{area_all[i]:>9.1f}  {duration_all[i]:>7.0f}  {dur_s:>6.2f}  "
              f"{speed:>12.3f}  {direction:>10}  "
              f"{x:>7.1f}  {y:>7.1f}")


def event_intervals(mat_path, fps, min_frame=2):
    """Print inter-event interval statistics from event onset times.

    Args:
        mat_path:  Path to *_AQuA2.mat.
        fps:       True frame rate in Hz.
        min_frame: Exclude events with t0 <= this value (frame-1 artifacts).
    """
    import h5py
    import numpy as np

    with h5py.File(mat_path, "r") as f:
        t0 = f["res/fts1/loc/t0"][:, 0].astype(int)
        T  = int(f["res/opts/sz"][3, 0])

    total_sec = T / fps
    t0_filt = np.sort(t0[t0 > min_frame])
    n_filt  = len(t0_filt)
    n_excl  = len(t0) - n_filt

    intervals_frames = np.diff(t0_filt)
    intervals_sec    = intervals_frames / fps

    print(f"Total events     : {len(t0)}")
    print(f"Excluded (t0 ≤ {min_frame}): {n_excl}  (likely background detections)")
    print(f"Analysed events  : {n_filt}  over {total_sec:.1f} s")
    print(f"Event rate       : {n_filt / total_sec:.4f} events/s  "
          f"= {n_filt / total_sec * 60:.2f} events/min")
    print()
    if len(intervals_sec) == 0:
        print("Not enough events to compute intervals.")
        return
    print(f"Inter-event interval (s):")
    print(f"  mean   {intervals_sec.mean():.2f}")
    print(f"  median {np.median(intervals_sec):.2f}")
    print(f"  std    {intervals_sec.std(ddof=1):.2f}")
    print(f"  min    {intervals_sec.min():.2f}")
    print(f"  max    {intervals_sec.max():.2f}")
    print(f"  → dominant frequency ≈ {1/intervals_sec.mean():.4f} Hz")


def event_fft(mat_path, fps, plot_out=None):
    """Compute and print FFT of each event's dF/F trace (AQuA2 precomputed mean).

    Uses dffMat1[0] — AQuA2's precomputed mean-across-footprint dF/F trace.
    Prints dominant frequency per event, plus the population median.

    Args:
        mat_path: Path to *_AQuA2.mat.
        fps:      True frame rate in Hz.
        plot_out: If given, save a power spectrum plot to this path.
    """
    import h5py
    import numpy as np
    from numpy.fft import rfft, rfftfreq

    with h5py.File(mat_path, "r") as f:
        dffMat = f["res/dffMat1"][0, :, :]   # (n_frames, n_events) mean trace

    n_frames, n_events = dffMat.shape
    freqs = rfftfreq(n_frames, d=1.0 / fps)

    dom_freqs = []
    for i in range(n_events):
        trace = dffMat[:, i]
        trace -= trace.mean()                 # remove DC
        power = np.abs(rfft(trace)) ** 2
        # skip DC bin (index 0)
        dom_idx = np.argmax(power[1:]) + 1
        dom_freqs.append(freqs[dom_idx])

    dom_freqs = np.array(dom_freqs)

    print(f"Events: {n_events}   frames: {n_frames}   fps: {fps:.4f}")
    print()
    print("Dominant frequency per event (Hz):")
    for i, f_ in enumerate(dom_freqs):
        print(f"  event {i+1:3d}: {f_:.4f} Hz  (period {1/f_:.1f} s)")
    print()
    print(f"Population median dominant freq : {np.median(dom_freqs):.4f} Hz")
    print(f"Population mean   dominant freq : {dom_freqs.mean():.4f} Hz")
    print(f"  → median period : {1/np.median(dom_freqs):.1f} s")

    if plot_out:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(10, 4))

        # mean power spectrum across all events
        ax = axes[0]
        all_power = []
        for i in range(n_events):
            trace = dffMat[:, i] - dffMat[:, i].mean()
            all_power.append(np.abs(rfft(trace)) ** 2)
        mean_power = np.mean(all_power, axis=0)
        ax.plot(freqs[1:], mean_power[1:], color="steelblue", linewidth=1)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Power")
        ax.set_title("Mean power spectrum (all events)")
        ax.spines[["top", "right"]].set_visible(False)

        # dominant frequency histogram
        ax = axes[1]
        ax.hist(dom_freqs, bins=20, color="steelblue", edgecolor="white")
        ax.axvline(np.median(dom_freqs), color="crimson", linestyle="--",
                   linewidth=1.2, label=f"median {np.median(dom_freqs):.4f} Hz")
        ax.set_xlabel("Dominant frequency (Hz)")
        ax.set_ylabel("Count")
        ax.set_title("Dominant frequency distribution")
        ax.legend(fontsize=8)
        ax.spines[["top", "right"]].set_visible(False)

        fig.tight_layout()
        fig.savefig(plot_out, dpi=150)
        plt.close(fig)
        print(f"Saved plot: {plot_out}")
