"""Convert all series in each LIF file to multi-page TIFF (T x Y x X)."""
import os
import re
import numpy as np
import tifffile
from readlif.reader import LifFile

SRC_DIR = "/home/crnlqz/krenciklab/astrocyte+neuron"
OUT_DIR = os.path.join(SRC_DIR, "tiff")
os.makedirs(OUT_DIR, exist_ok=True)

lif_files = [f for f in os.listdir(SRC_DIR) if f.endswith(".lif")]

for lif_name in sorted(lif_files):
    lif_path = os.path.join(SRC_DIR, lif_name)
    lif_stem = os.path.splitext(lif_name)[0]
    print(f"\n=== {lif_name} ===")

    lif = LifFile(lif_path)
    for series in lif.get_iter_image():
        safe_series = re.sub(r'[^\w\s+-]', '', series.name).strip().replace(' ', '_')
        out_name = f"{lif_stem}__{safe_series}.tif"
        out_path = os.path.join(OUT_DIR, out_name)

        nt = series.nt
        frames = []
        for t in range(nt):
            frame = np.array(series.get_frame(z=0, t=t, c=0))
            frames.append(frame)

        stack = np.stack(frames, axis=0)  # shape: T x Y x X
        tifffile.imwrite(out_path, stack, photometric='minisblack')
        print(f"  saved: {out_name}  shape={stack.shape}  dtype={stack.dtype}")

print("\nDone.")
