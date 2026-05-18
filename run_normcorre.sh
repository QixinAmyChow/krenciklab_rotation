#!/bin/bash
#SBATCH --job-name=normcorre
#SBATCH --partition=defq
#SBATCH --output=/home/crnlqz/krenciklab/krenciklab_rotation/%x_%j.log
#SBATCH --error=/home/crnlqz/krenciklab/krenciklab_rotation/%x_%j.err
#SBATCH --time=6:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=4

source "${1:?Usage: sbatch run_normcorre.sh <config_file>}"
module load matlab/R2024b
cd "$ROOT"

echo "=== NoRMCorre drift correction — $EXP ==="
matlab -batch "addpath('$ROOT'); run_normcorre('$TIFF_IN/', '$TIFF_MC/')"
echo "=== Done ==="
