"""Command-line interface for aqua2kit."""
import argparse
import json
import sys
from pathlib import Path


def cmd_lif2tif(args):
    from .lif_io import convert
    for lif in args.input:
        print(f"\n=== {lif} ===")
        outputs = convert(lif, out_dir=args.outdir,
                          skip_snapshots=not args.keep_snapshots,
                          channel=args.channel)
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
    print(cond_df[["condition", "n_replicates", "n_events mean", "n_events sem"]].to_string(index=False))


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
    p_lif.add_argument("--keep-snapshots", action="store_true",
                       help="Include single-frame series (skipped by default)")
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
