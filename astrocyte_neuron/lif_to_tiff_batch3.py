"""Convert timeseries from 3.25.26 day28 Asteroids GCaMP8s LIF to TIFF (skip single-frame snapshots)."""
import os, re
import numpy as np
import tifffile
from readlif.reader import LifFile

SRC_DIR = "/home/crnlqz/krenciklab/astrocyte+neuron"
OUT_DIR = os.path.join(SRC_DIR, "tiff_batch3")
os.makedirs(OUT_DIR, exist_ok=True)

lif_name = "3.25.26 day28 Asteroids GCaMP8s spont and ATP (1).lif"
lif_stem = "3.25.26 day28 Asteroids GCaMP8s spont and ATP"

lif_path = os.path.join(SRC_DIR, lif_name)
print(f"\n=== {lif_name} ===")
lif = LifFile(lif_path)

for series in lif.get_iter_image():
    if series.nt <= 1:
        print(f"  skip (snapshot): {series.name!r}  nt={series.nt}")
        continue
    safe = re.sub(r'[^\w\s+-]', '', series.name).strip().replace(' ', '_').rstrip('_')
    out_path = os.path.join(OUT_DIR, f"{lif_stem}__{safe}.tif")
    frames = [np.array(series.get_frame(z=0, t=t, c=0)) for t in range(series.nt)]
    stack = np.stack(frames, axis=0)
    tifffile.imwrite(out_path, stack, photometric='minisblack')
    print(f"  saved: {os.path.basename(out_path)}  shape={stack.shape}")

print("\nDone.")
