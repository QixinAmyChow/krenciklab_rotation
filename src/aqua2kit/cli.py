"""Command-line interface for aqua2kit."""
import argparse
import json
import sys
from pathlib import Path


def cmd_lif2tif(args):
    from .lif_io import convert
    for lif in args.input:
        print(f"\n=== {lif} ===")
        outputs = convert(lif, out_dir=args.outdir, channel=args.channel)
        print(f"{len(outputs)} TIFFs written to {Path(outputs[0]).parent if outputs else args.outdir}")


def cmd_quantify(args):
    from .quantify import quantify_samples, condition_summary, to_excel

    with open(args.samples) as f:
        samples = json.load(f)

    print(f"Quantifying {len(samples)} samples...")
    events_df, summary_df = quantify_samples(samples, channel=args.channel)
    cond_df = condition_summary(summary_df)
    to_excel(events_df, summary_df, args.output, cond_df)

    print("\n── Per-sample event counts ─────────────────────────────────────")
    cols = [c for c in ["experiment", "condition", "replicate", "n_events"] if c in summary_df.columns]
    print(summary_df[cols].to_string(index=False))

    print("\n── Condition summary ───────────────────────────────────────────")
    if not cond_df.empty:
        print(cond_df[["condition", "n_replicates", "n_events mean", "n_events sem"]].to_string(index=False))
    else:
        print("(no data)")


def cmd_join_tif(args):
    from .lif_io import join_tifs
    from pathlib import Path

    inputs = args.input
    if args.output:
        out = args.output
    else:
        # default: place next to first input, named after stem of first file + "_joined"
        first = Path(inputs[0])
        out = str(first.parent / (first.stem + "_joined.tif"))

    join_tifs(inputs, out)


def cmd_inspect_mat(args):
    from .utils import inspect_mat
    inspect_mat(args.mat)


def cmd_cell_assign(args):
    from .utils import print_cell_assignments
    print_cell_assignments(args.mat, args.label_map,
                           overlap_threshold=args.overlap_threshold)


def cmd_plot_cell_osc_freq(args):
    from .plot import plot_cell_oscillation_freq
    out = plot_cell_oscillation_freq(
        args.mat, args.label_map, args.atp_frame, args.fps,
        min_prominence=args.min_prominence,
        min_distance=args.min_distance,
        output=args.output, title=args.title)
    print(f"Saved {out}")


def cmd_plot_cell_event_rates(args):
    from .plot import plot_cell_event_rates
    out = plot_cell_event_rates(
        args.mat, args.label_map, args.atp_frame, args.fps,
        overlap_threshold=args.overlap_threshold,
        min_frame=args.min_frame,
        output=args.output, title=args.title)
    print(f"Saved {out}")


def cmd_plot_cell_peakcaller(args):
    from .plot import plot_cell_peakcaller
    out = plot_cell_peakcaller(
        args.mat, args.label_map, args.atp_frame, args.fps,
        ema_smoothness=args.ema_smoothness,
        rise=args.rise, fall=args.fall,
        lookback_frames=args.lookback_frames,
        lookahead_frames=args.lookahead_frames,
        output=args.output, title=args.title)
    print(f"Saved {out}")


def cmd_plot_cell_peakcaller_fc(args):
    from .plot import plot_cell_peakcaller_fc
    out = plot_cell_peakcaller_fc(
        args.mat, args.label_map, args.atp_frame, args.fps,
        ema_smoothness=args.ema_smoothness,
        rise=args.rise, fall=args.fall,
        lookback_frames=args.lookback_frames,
        lookahead_frames=args.lookahead_frames,
        output=args.output, title=args.title)
    print(f"Saved {out}")


def cmd_plot_cell_roi_map(args):
    from .plot import plot_cell_roi_map
    out = plot_cell_roi_map(args.mat, args.label_map,
                            output=args.output, title=args.title)
    print(f"Saved {out}")


def cmd_plot_event_direction(args):
    from .plot import plot_event_direction_distribution
    # parse atp_frames: "none" → None, else int
    atp_frames = []
    for v in args.atp_frames:
        atp_frames.append(None if v.lower() == "none" else int(v))
    if len(atp_frames) != len(args.mat):
        import sys
        print("error: --atp-frames must have same number of values as mat files", file=sys.stderr)
        sys.exit(1)
    out = plot_event_direction_distribution(
        args.mat, atp_frames, args.fps,
        prop_threshold=args.prop_threshold,
        min_frame=args.min_frame,
        output=args.output, title=args.title)
    print(f"Saved {out}")


def cmd_plot_event_trajectories(args):
    from .plot import plot_event_trajectories
    out = plot_event_trajectories(
        args.mat,
        prop_threshold=args.prop_threshold,
        output=args.output, title=args.title)
    print(f"Saved {out}")


def cmd_plot_events_per_frame(args):
    from .plot import plot_events_per_frame
    out = plot_events_per_frame(args.mat, args.atp_frame, args.fps,
                                min_frame=args.min_frame,
                                output=args.output, title=args.title)
    print(f"Saved {out}")


def cmd_plot_event_rate(args):
    from .plot import plot_event_rate
    out = plot_event_rate(args.mat, args.atp_frame, args.fps,
                          min_frame=args.min_frame,
                          output=args.output, title=args.title)
    print(f"Saved {out}")


def cmd_event_features(args):
    from .utils import print_event_features
    print_event_features(args.mat, args.atp_frame, args.fps,
                         prop_threshold=args.prop_threshold,
                         min_frame=args.min_frame)


def cmd_event_intervals(args):
    from .utils import event_intervals
    event_intervals(args.mat, args.fps, min_frame=args.min_frame)


def cmd_event_fft(args):
    from .utils import event_fft
    event_fft(args.mat, args.fps, plot_out=args.output)


def cmd_plot_dff(args):
    import h5py
    from .plot import plot_dff

    mat = args.mat
    fps = args.fps
    atp_frame = args.atp_frame
    atp_sec = args.atp_sec

    if fps is None:
        if args.total_sec is not None:
            with h5py.File(mat, "r") as f:
                n_frames = int(f["res/opts/sz"][3, 0])
            fps = n_frames / args.total_sec
        elif atp_frame is not None and atp_sec is not None:
            fps = atp_frame / atp_sec
        else:
            print("error: cannot determine fps — provide --fps, --total-sec, "
                  "or both --atp-frame and --atp-sec", file=sys.stderr)
            sys.exit(1)

    if atp_frame is None:
        if atp_sec is not None:
            atp_frame = int(round(atp_sec * fps))
        else:
            print("error: cannot determine atp-frame — provide --atp-frame or --atp-sec",
                  file=sys.stderr)
            sys.exit(1)

    out = plot_dff(mat, atp_frame, fps, output=args.output, title=args.title)
    print(f"Saved {out}  (fps={fps:.4f}, ATP at {atp_frame / fps:.1f} s)")


def cmd_stamp_tiff(args):
    from .stamp import stamp_tiff
    out = stamp_tiff(args.input, fps=args.fps, dst=args.output,
                     font_size=args.font_size)
    print(f"Stamped TIFF written to {out}")


def cmd_sample_template(args):
    template = [
        {
            "folder": "path/to/rep1_control_results",
            "experiment": "my_experiment",
            "condition": "control",
            "replicate": 1,
        },
        {
            "folder": "path/to/rep1_ABO_results",
            "experiment": "my_experiment",
            "condition": "+ABO",
            "replicate": 1,
        },
        {
            "folder": "path/to/rep2_control_results",
            "experiment": "my_experiment",
            "condition": "control",
            "replicate": 2,
        },
        {
            "folder": "path/to/rep2_ABO_results",
            "experiment": "my_experiment",
            "condition": "+ABO",
            "replicate": 2,
        },
    ]
    out = args.output or "samples.json"
    with open(out, "w") as f:
        json.dump(template, f, indent=2)
    print(f"Template written to {out}")
    print("Edit 'folder', 'experiment', 'condition', and 'replicate' for each sample,")
    print("then run:  aqua2kit quantify samples.json --output summary.xlsx")


def main():
    parser = argparse.ArgumentParser(
        prog="aqua2kit",
        description="Ca²⁺ imaging analysis tools — LIF conversion, AQuA2 quantification",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── lif2tif ──────────────────────────────────────────────────────────────
    p_lif = sub.add_parser("lif2tif", help="Convert LIF file(s) to TIFF")
    p_lif.add_argument("input", nargs="+", help="LIF file path(s)")
    p_lif.add_argument("--outdir", "-o", default=None,
                       help="Output directory (default: 'tiff/' folder next to each LIF)")
    p_lif.add_argument("--channel", type=int, default=0,
                       help="Channel index to extract (default: 0)")
    p_lif.set_defaults(func=cmd_lif2tif)

    # ── quantify ─────────────────────────────────────────────────────────────
    p_q = sub.add_parser("quantify", help="Quantify AQuA2 results → Excel summary")
    p_q.add_argument("samples",
                     help="JSON file listing samples (run 'aqua2kit template' to generate one)")
    p_q.add_argument("--output", "-o", default="aqua2_summary.xlsx",
                     help="Output Excel path (default: aqua2_summary.xlsx)")
    p_q.add_argument("--channel", type=int, default=1,
                     help="AQuA2 channel number (default: 1)")
    p_q.set_defaults(func=cmd_quantify)

    # ── join-tif ─────────────────────────────────────────────────────────────
    p_j = sub.add_parser("join-tif", help="Concatenate TIFF timeseries along the time axis")
    p_j.add_argument("input", nargs="+", help="TIFF files to join in order")
    p_j.add_argument("--output", "-o", default=None,
                     help="Output TIFF path (default: <first_stem>_joined.tif next to first input)")
    p_j.set_defaults(func=cmd_join_tif)

    # ── stamp-tiff ───────────────────────────────────────────────────────────
    p_s = sub.add_parser("stamp-tiff", help="Burn per-frame timestamps into a TIFF stack")
    p_s.add_argument("input", help="Input multi-page TIFF path")
    p_s.add_argument("--fps", type=float, required=True,
                     help="Frame rate in Hz (used to compute time per frame)")
    p_s.add_argument("--output", "-o", default=None,
                     help="Output TIFF path (default: <stem>_stamped.tif next to input)")
    p_s.add_argument("--font-size", type=int, default=14)
    p_s.set_defaults(func=cmd_stamp_tiff)

    # ── cell-assign ──────────────────────────────────────────────────────────
    p_ca = sub.add_parser("cell-assign",
                          help="Assign AQuA2 events to cells via label_map.tif overlap")
    p_ca.add_argument("mat", help="Path to *_AQuA2.mat")
    p_ca.add_argument("label_map", help="Path to *_label_map.tif")
    p_ca.add_argument("--overlap-threshold", type=float, default=0.0,
                      help="Min overlap fraction to assign an event (default 0.0)")
    p_ca.set_defaults(func=cmd_cell_assign)

    # ── inspect-mat ──────────────────────────────────────────────────────────
    p_i = sub.add_parser("inspect-mat", help="Print contents of an AQuA2 .mat file")
    p_i.add_argument("mat", help="Path to *_AQuA2.mat")
    p_i.set_defaults(func=cmd_inspect_mat)

    # ── plot-cell-osc-freq ────────────────────────────────────────────────────
    p_of = sub.add_parser("plot-cell-osc-freq",
                          help="Ca2+ oscillation frequency pre/post ATP per cell")
    p_of.add_argument("mat", help="Path to *_AQuA2.mat")
    p_of.add_argument("label_map", help="Path to *_label_map.tif")
    p_of.add_argument("--atp-frame", type=int, required=True)
    p_of.add_argument("--fps", type=float, required=True)
    p_of.add_argument("--min-prominence", type=float, default=0.05)
    p_of.add_argument("--min-distance", type=int, default=3)
    p_of.add_argument("--output", "-o", default=None)
    p_of.add_argument("--title", default=None)
    p_of.set_defaults(func=cmd_plot_cell_osc_freq)

    # ── plot-cell-event-rates ─────────────────────────────────────────────────
    p_cr = sub.add_parser("plot-cell-event-rates",
                          help="Mean ± SEM event rate pre/post ATP across cells")
    p_cr.add_argument("mat", help="Path to *_AQuA2.mat")
    p_cr.add_argument("label_map", help="Path to *_label_map.tif")
    p_cr.add_argument("--atp-frame", type=int, required=True)
    p_cr.add_argument("--fps", type=float, required=True)
    p_cr.add_argument("--overlap-threshold", type=float, default=0.0)
    p_cr.add_argument("--min-frame", type=int, default=2)
    p_cr.add_argument("--output", "-o", default=None)
    p_cr.add_argument("--title", default=None)
    p_cr.set_defaults(func=cmd_plot_cell_event_rates)

    # ── plot-cell-peakcaller ──────────────────────────────────────────────────
    p_pc = sub.add_parser("plot-cell-peakcaller",
                          help="PeakCaller-style Ca2+ peak frequency pre/post ATP per cell")
    p_pc.add_argument("mat", help="Path to *_AQuA2.mat")
    p_pc.add_argument("label_map", help="Path to *_label_map.tif")
    p_pc.add_argument("--atp-frame", type=int, required=True)
    p_pc.add_argument("--fps", type=float, required=True)
    p_pc.add_argument("--ema-smoothness", type=int, default=40,
                      help="EMA window k for baseline detrending (default 40)")
    p_pc.add_argument("--rise", type=float, default=0.10,
                      help="Required rise fraction above local min (default 0.10)")
    p_pc.add_argument("--fall", type=float, default=0.10,
                      help="Required fall fraction after peak (default 0.10)")
    p_pc.add_argument("--lookback-frames", type=int, default=5,
                      help="Frames to look back for rise detection (default 5)")
    p_pc.add_argument("--lookahead-frames", type=int, default=8,
                      help="Frames to look ahead for fall detection (default 8)")
    p_pc.add_argument("--output", "-o", default=None)
    p_pc.add_argument("--title", default=None)
    p_pc.set_defaults(func=cmd_plot_cell_peakcaller)

    # ── plot-cell-peakcaller-fc ───────────────────────────────────────────────
    p_pf = sub.add_parser("plot-cell-peakcaller-fc",
                          help="Fold change (post/pre ATP) in PeakCaller peak frequency per cell")
    p_pf.add_argument("mat", help="Path to *_AQuA2.mat")
    p_pf.add_argument("label_map", help="Path to *_label_map.tif")
    p_pf.add_argument("--atp-frame", type=int, required=True)
    p_pf.add_argument("--fps", type=float, required=True)
    p_pf.add_argument("--ema-smoothness", type=int, default=40)
    p_pf.add_argument("--rise", type=float, default=0.10)
    p_pf.add_argument("--fall", type=float, default=0.10)
    p_pf.add_argument("--lookback-frames", type=int, default=5)
    p_pf.add_argument("--lookahead-frames", type=int, default=8)
    p_pf.add_argument("--output", "-o", default=None)
    p_pf.add_argument("--title", default=None)
    p_pf.set_defaults(func=cmd_plot_cell_peakcaller_fc)

    # ── plot-cell-roi-map ─────────────────────────────────────────────────────
    p_rm = sub.add_parser("plot-cell-roi-map",
                          help="Plot cell ROIs from label_map.tif overlaid on max projection")
    p_rm.add_argument("mat", help="Path to *_AQuA2.mat")
    p_rm.add_argument("label_map", help="Path to *_label_map.tif")
    p_rm.add_argument("--output", "-o", default=None)
    p_rm.add_argument("--title", default=None)
    p_rm.set_defaults(func=cmd_plot_cell_roi_map)

    # ── plot-event-direction ──────────────────────────────────────────────────
    p_ed = sub.add_parser("plot-event-direction",
                          help="Stacked bar of event direction distribution across recordings/phases")
    p_ed.add_argument("mat", nargs="+", help="One or more *_AQuA2.mat paths")
    p_ed.add_argument("--atp-frames", nargs="+", required=True, metavar="FRAME_OR_NONE",
                      help="ATP frame per mat file (integer or 'none' for spontaneous)")
    p_ed.add_argument("--fps", type=float, required=True)
    p_ed.add_argument("--prop-threshold", type=float, default=3.0)
    p_ed.add_argument("--min-frame", type=int, default=2)
    p_ed.add_argument("--output", "-o", default=None)
    p_ed.add_argument("--title", default=None)
    p_ed.set_defaults(func=cmd_plot_event_direction)

    # ── plot-event-trajectories ───────────────────────────────────────────────
    p_et = sub.add_parser("plot-event-trajectories",
                          help="Plot event trajectories on FOV, labeled by index, colored by direction")
    p_et.add_argument("mat", help="Path to *_AQuA2.mat")
    p_et.add_argument("--prop-threshold", type=float, default=3.0,
                      help="avgPropSpeed (px/frame) below which an event is Static (default 3.0)")
    p_et.add_argument("--output", "-o", default=None)
    p_et.add_argument("--title", default=None)
    p_et.set_defaults(func=cmd_plot_event_trajectories)

    # ── plot-events-per-frame ─────────────────────────────────────────────────
    p_epf = sub.add_parser("plot-events-per-frame",
                           help="Event onset count per frame with ATP marker")
    p_epf.add_argument("mat", help="Path to *_AQuA2.mat")
    p_epf.add_argument("--atp-frame", type=int, required=True)
    p_epf.add_argument("--fps", type=float, required=True)
    p_epf.add_argument("--min-frame", type=int, default=2)
    p_epf.add_argument("--output", "-o", default=None)
    p_epf.add_argument("--title", default=None)
    p_epf.set_defaults(func=cmd_plot_events_per_frame)

    # ── plot-event-rate ──────────────────────────────────────────────────────
    p_er = sub.add_parser("plot-event-rate",
                          help="Bar plot of event rate pre vs post ATP, normalized by time")
    p_er.add_argument("mat", help="Path to *_AQuA2.mat")
    p_er.add_argument("--atp-frame", type=int, required=True,
                      help="First frame of ATP addition (0-based)")
    p_er.add_argument("--fps", type=float, required=True, help="True frame rate in Hz")
    p_er.add_argument("--min-frame", type=int, default=2,
                      help="Exclude events with t0 <= this (default 2)")
    p_er.add_argument("--output", "-o", default=None)
    p_er.add_argument("--title", default=None)
    p_er.set_defaults(func=cmd_plot_event_rate)

    # ── event-features ───────────────────────────────────────────────────────
    p_ef2 = sub.add_parser("event-features",
                           help="Print per-event features: area, duration, speed, direction, phase")
    p_ef2.add_argument("mat", help="Path to *_AQuA2.mat")
    p_ef2.add_argument("--atp-frame", type=int, required=True)
    p_ef2.add_argument("--fps", type=float, required=True)
    p_ef2.add_argument("--prop-threshold", type=float, default=3.0,
                       help="avgPropSpeed below which an event is Static (default 3.0)")
    p_ef2.add_argument("--min-frame", type=int, default=2)
    p_ef2.set_defaults(func=cmd_event_features)

    # ── event-intervals ──────────────────────────────────────────────────────
    p_ei = sub.add_parser("event-intervals", help="Inter-event interval stats from onset times")
    p_ei.add_argument("mat", help="Path to *_AQuA2.mat")
    p_ei.add_argument("--fps", type=float, required=True, help="True frame rate in Hz")
    p_ei.add_argument("--min-frame", type=int, default=2,
                      help="Exclude events with t0 <= this (default 2, filters frame-1 artifacts)")
    p_ei.set_defaults(func=cmd_event_intervals)

    # ── event-fft ────────────────────────────────────────────────────────────
    p_ef = sub.add_parser("event-fft", help="FFT of per-event dF/F traces")
    p_ef.add_argument("mat", help="Path to *_AQuA2.mat")
    p_ef.add_argument("--fps", type=float, required=True, help="True frame rate in Hz")
    p_ef.add_argument("--output", "-o", default=None,
                      help="Optional PNG path to save power spectrum + dominant freq histogram")
    p_ef.set_defaults(func=cmd_event_fft)

    # ── plot-dff ─────────────────────────────────────────────────────────────
    p_dff = sub.add_parser("plot-dff", help="Plot per-event dF/F traces vs time from a .mat file")
    p_dff.add_argument("mat", help="Path to *_AQuA2.mat")
    p_dff.add_argument("--atp-frame", type=int, default=None,
                       help="First frame of drug addition (0-based)")
    p_dff.add_argument("--atp-sec", type=float, default=None,
                       help="Time of drug addition in seconds")
    p_dff.add_argument("--fps", type=float, default=None,
                       help="Frame rate in Hz (overrides derivation)")
    p_dff.add_argument("--total-sec", type=float, default=None,
                       help="Total recording duration in seconds (used to derive fps)")
    p_dff.add_argument("--output", "-o", default=None,
                       help="Output PNG path (default: <mat_stem>_dff.png next to mat)")
    p_dff.add_argument("--title", default=None,
                       help="Plot title (default: mat filename stem)")
    p_dff.set_defaults(func=cmd_plot_dff)

    # ── template ─────────────────────────────────────────────────────────────
    p_t = sub.add_parser("template",
                         help="Generate a sample JSON template for 'aqua2kit quantify'")
    p_t.add_argument("--output", "-o", default=None,
                     help="Output filename (default: samples.json)")
    p_t.set_defaults(func=cmd_sample_template)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
