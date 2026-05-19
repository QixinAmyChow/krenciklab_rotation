"""Convert Leica LIF files to multi-page TIFF."""
import re
from pathlib import Path
import numpy as np
import tifffile
from readlif.reader import LifFile


def convert(lif_path, out_dir=None, channel=0):
    """Convert all series in a LIF file to separate TIFF files.

    Args:
        lif_path:        Path to .lif file.
        out_dir:         Output directory. A subdirectory named after the LIF file is
                         created inside it. Defaults to a 'tiff' folder next to the LIF.
        channel:         Channel index to extract (default 0).

    Returns:
        List of Path objects for the written TIFFs.

    Example:
        from aqua2kit import lif_to_tiff
        lif_to_tiff("experiment.lif", out_dir="tiff/")
    """
    lif_path = Path(lif_path)
    if not lif_path.exists():
        raise FileNotFoundError(lif_path)

    if out_dir is None:
        out_dir = lif_path.parent / "tiff"
    out_dir = Path(out_dir)

    lif_stem = lif_path.stem
    series_dir = out_dir / lif_stem
    series_dir.mkdir(parents=True, exist_ok=True)

    lif = LifFile(str(lif_path))
    outputs = []

    for series in lif.get_iter_image():

        safe_name = re.sub(r"[^\w\s+-]", "", series.name).strip().replace(" ", "_")
        out_path = series_dir / f"{lif_stem}__{safe_name}.tif"

        frames = [np.array(series.get_frame(z=0, t=t, c=channel))
                  for t in range(series.nt)]
        tifffile.imwrite(str(out_path), np.stack(frames))
        print(f"  wrote {out_path.name}  ({series.nt} frames)")
        outputs.append(out_path)

    return outputs


def read_fps(lif_path):
    """Return acquisition frame rate (Hz) from a LIF file.

    Uses the time scale of the first time-lapse series (nt > 1).
    Returns 1.0 if no time-lapse series is found.

    Args:
        lif_path: Path to .lif file.

    Returns:
        float: frames per second.
    """
    lif = LifFile(str(lif_path))
    for series in lif.get_iter_image():
        if series.nt > 1 and series.scale[3] is not None:
            return 1.0 / series.scale[3]
    return 1.0


def join_tifs(inputs, output):
    """Concatenate multiple TIFF timeseries into one along the time axis.

    Args:
        inputs: list of TIFF file paths to join in order.
        output: output TIFF path.

    Returns:
        Path to the written TIFF.

    Example:
        from aqua2kit import join_tifs
        join_tifs(["rep2-1.tif", "rep2-2.tif"], "rep2_joined.tif")
    """
    import tifffile
    import numpy as np

    parts = []
    for p in inputs:
        arr = tifffile.imread(str(p))
        if arr.ndim == 2:
            arr = arr[np.newaxis]  # single frame → (1, Y, X)
        parts.append(arr)
        print(f"  loaded {Path(p).name}  ({arr.shape[0]} frames)")

    joined = np.concatenate(parts, axis=0)
    output = Path(output)
    tifffile.imwrite(str(output), joined)
    print(f"Joined: {joined.shape[0]} frames → {output.name}")
    return output
