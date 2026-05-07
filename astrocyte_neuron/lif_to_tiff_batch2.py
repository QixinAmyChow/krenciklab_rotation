import os, re
import numpy as np
import tifffile
from readlif.reader import LifFile

SRC_DIR = "/home/crnlqz/krenciklab/astrocyte+neuron"
OUT_DIR = os.path.join(SRC_DIR, "tiff_batch2")
os.makedirs(OUT_DIR, exist_ok=True)

lif_files = [
    "4.6.26 Astro only +-ABO.lif",
    "4.8.26 organoid +-ABO.lif",
    "4.9.26 GCaMP8s Asteroids d6+- ABO.lif",
    "4.10.26 GCaMP8s Astroid d7 +-ABO.lif",
]

for lif_name in lif_files:
    lif_path = os.path.join(SRC_DIR, lif_name)
    lif_stem = os.path.splitext(lif_name)[0]
    print(f"\n=== {lif_name} ===")
    lif = LifFile(lif_path)
    for series in lif.get_iter_image():
        safe = re.sub(r'[^\w\s+-]', '', series.name).strip().replace(' ', '_')
        out_path = os.path.join(OUT_DIR, f"{lif_stem}__{safe}.tif")
        frames = [np.array(series.get_frame(z=0, t=t, c=0)) for t in range(series.nt)]
        stack = np.stack(frames, axis=0)
        tifffile.imwrite(out_path, stack, photometric='minisblack')
        print(f"  saved: {os.path.basename(out_path)}  shape={stack.shape}")

print("\nDone.")
