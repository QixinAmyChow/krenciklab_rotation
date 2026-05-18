#!/bin/bash
# Submit all three pipeline stages as chained SLURM jobs.
#
#   bash run_pipeline.sh <config_file>
#
# Each stage runs as its own job. Stage N starts only after stage N-1
# succeeds (afterok dependency). On failure, downstream stages are
# cancelled automatically.
#
# To re-run a single stage independently:
#   sbatch run_normcorre.sh config_3.11.26.sh
#   sbatch run_aqua2.sh     config_3.11.26.sh
#   sbatch run_quantify.sh  config_3.11.26.sh

CONFIG="${1:?Usage: bash run_pipeline.sh <config_file>}"
source "$CONFIG"

DIR="$(cd "$(dirname "$0")" && pwd)"

JID1=$(sbatch --parsable \
        --job-name="normcorre_${EXP}" \
        "$DIR/run_normcorre.sh" "$CONFIG")

JID2=$(sbatch --parsable \
        --job-name="aqua2_${EXP}" \
        --dependency=afterok:"$JID1" \
        "$DIR/run_aqua2.sh" "$CONFIG")

JID3=$(sbatch --parsable \
        --job-name="quantify_${EXP}" \
        --dependency=afterok:"$JID2" \
        "$DIR/run_quantify.sh" "$CONFIG")

echo "Submitted pipeline for experiment: $EXP"
echo "  Stage 1 normcorre : job $JID1"
echo "  Stage 2 aqua2     : job $JID2  (depends on $JID1)"
echo "  Stage 3 quantify  : job $JID3  (depends on $JID2)"
echo ""
echo "Monitor:  squeue -j $JID1,$JID2,$JID3"
echo "Cancel:   scancel $JID1 $JID2 $JID3"
