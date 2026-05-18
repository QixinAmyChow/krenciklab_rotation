#!/bin/bash
#SBATCH --job-name=quantify
#SBATCH --partition=defq
#SBATCH --output=/home/crnlqz/krenciklab/krenciklab_rotation/%x_%j.log
#SBATCH --error=/home/crnlqz/krenciklab/krenciklab_rotation/%x_%j.err
#SBATCH --time=1:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1

source "${1:?Usage: sbatch run_quantify.sh <config_file>}"
cd "$ROOT"

echo "=== aqua2kit quantify — $EXP ==="

python3 - <<EOF
import json, pathlib, re

results_root = pathlib.Path("$RESULTS")
samples = []
for folder in sorted(results_root.glob("*_results")):
    name = folder.name.replace("_results", "")
    rep = 1
    m = re.search(r'rep(\d+)', name)
    if m:
        rep = int(m.group(1))
    n = name.lower()
    if "stopped" in n:
        condition = "stopped"
    elif "atp" in n:
        condition = "ATP"
    else:
        condition = "spontaneous"
    samples.append({
        "folder":     str(folder),
        "experiment": "$EXP",
        "condition":  condition,
        "replicate":  rep,
    })

out = pathlib.Path("$SAMPLES")
with open(out, "w") as f:
    json.dump(samples, f, indent=2)
print(f"Wrote {len(samples)} samples to {out}")
EOF

aqua2kit quantify "$SAMPLES" \
    --output "$SUMMARY" \
    --channel 1

echo "=== Done — summary: $SUMMARY ==="
