#!/bin/bash
# Submit the pipeline as a chain of Slurm jobs linked with --dependency=afterok.
# If a job fails (e.g. the quality gate exits 2), every later job is never started.
#
#   ./hpc/slurm/submit.sh era5            # real data (needs $RAW_ERA5)
#   ./hpc/slurm/submit.sh sample          # synthetic data
#   ./hpc/slurm/submit.sh sample-corrupt  # quality gate should stop the chain
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/env.sh"
[ -f "$HERE/env.local.sh" ] && source "$HERE/env.local.sh"

SOURCE="${1:-sample}"
RUN_ID="slurm-$(date +%Y%m%d-%H%M%S)-$SOURCE"
LOGDIR="$SCRATCH_BASE/logs/$RUN_ID"
mkdir -p "$LOGDIR"
[ -f "$SIF" ] || { echo "missing image $SIF (see hpc/README.md)"; exit 1; }
[ -f "$CONFIG" ] || { echo "missing config $CONFIG"; exit 1; }

COMMON=(--parsable --account="$CSC_PROJECT" --partition="$PARTITION" --chdir="$LOGDIR")
export RUN_ID
submit() {  # submit <after-job-id|""> <cstwin subcommand> [args...]
  local after="$1"; shift
  local dep=()
  [ -n "$after" ] && dep=(--dependency="afterok:$after" --kill-on-invalid-dep=yes)
  sbatch "${COMMON[@]}" "${dep[@]}" --job-name="cstwin-$1" --export=ALL "$HERE/step.sbatch" "$@"
}

case "$SOURCE" in
  era5)           prev=$(sbatch "${COMMON[@]}" --export=ALL "$HERE/stage_raw.sbatch") ;;
  sample)         prev=$(submit "" sample --days 14) ;;
  sample-corrupt) prev=$(submit "" sample --days 7 --corrupt) ;;
  *) echo "unknown source: $SOURCE"; exit 1 ;;
esac
ids=("$prev")
for step in produce check onepass indicator report; do
  prev=$(submit "$prev" "$step")
  ids+=("$prev")
done

printf '%s\n' "${ids[@]}" > "$LOGDIR/job_ids.txt"
echo "run:  $RUN_ID"
echo "jobs: ${ids[*]}"
echo "logs: $LOGDIR"
echo "watch:   squeue --me"
echo "metrics: $HERE/sacct_report.sh $LOGDIR"
