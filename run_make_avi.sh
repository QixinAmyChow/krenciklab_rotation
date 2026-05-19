#!/bin/bash
#SBATCH --job-name=make_avi
#SBATCH --partition=defq
#SBATCH --output=/home/crnlqz/krenciklab/krenciklab_rotation/%x_%j.log
#SBATCH --error=/home/crnlqz/krenciklab/krenciklab_rotation/%x_%j.err
#SBATCH --time=4:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=2

source "${1:?Usage: sbatch run_make_avi.sh <config_file>}"
module load matlab/R2024b
cd "$ROOT"

echo "=== Regenerating AVI overlays — $EXP ==="
FPS=$(python3 -c "from aqua2kit.lif_io import read_fps; print(read_fps('$LIF'))")
echo "FPS: $FPS"
matlab -batch "addpath('$ROOT/src'); make_avi('$RESULTS/', $FPS)"
echo "=== Done ==="
