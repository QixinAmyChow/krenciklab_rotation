#!/bin/bash
#SBATCH --job-name=aqua2
#SBATCH --partition=defq
#SBATCH --output=/home/crnlqz/krenciklab/krenciklab_rotation/%x_%j.log
#SBATCH --error=/home/crnlqz/krenciklab/krenciklab_rotation/%x_%j.err
#SBATCH --time=12:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=4

source "${1:?Usage: sbatch run_aqua2.sh <config_file>}"
module load matlab/R2024b
cd "$ROOT"

echo "=== AQuA2 event detection — $EXP ==="
matlab -batch "addpath('$ROOT/src'); run_aqua2('$TIFF_MC/', '$RESULTS/')"
echo "=== Done ==="
