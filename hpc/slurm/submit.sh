#!/bin/bash
# Submit the pipeline to Slurm on Roihu.
#
#   ./hpc/slurm/submit.sh <source> [chain|single]
#     source: era5 | sample | sample-corrupt
#     chain  (default): one job per step, linked with --dependency=afterok;
#                       a failed quality gate cancels every later job
#     single:           whole pipeline in one job (fewer, cheaper scheduler jobs)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/env.sh"
[ -f "$HERE/env.local.sh" ] && source "$HERE/env.local.sh"

SOURCE="${1:-sample}"
MODE="${2:-chain}"
RUN_ID="slurm-$(date +%Y%m%d-%H%M%S)-$SOURCE-$MODE"
LOGDIR="$SCRATCH_BASE/logs/$RUN_ID"
[ -f "$SIF" ] || { echo "missing image $SIF (see hpc/README.md)"; exit 1; }
[ -f "$CONFIG" ] || { echo "missing config $CONFIG"; exit 1; }
mkdir -p "$LOGDIR"
export RUN_ID

case "$SOURCE" in
  era5)
    [ -f "$RAW_ERA5" ] || { echo "missing $RAW_ERA5"; exit 1; }
    # Light data staging on the login node (allowed: moving data), not a separate job.
    mkdir -p "$SCRATCH_BASE/runs/$RUN_ID/raw"
    cp "$RAW_ERA5" "$SCRATCH_BASE/runs/$RUN_ID/raw/era5_subset.nc"
    SOURCE_ARGS="" ;;
  sample)         SOURCE_ARGS="sample --days 14" ;;
  sample-corrupt) SOURCE_ARGS="sample --days 7 --corrupt" ;;
  *) echo "unknown source: $SOURCE"; exit 1 ;;
esac

COMMON=(--parsable --account="$CSC_PROJECT" --partition="$PARTITION" --chdir="$LOGDIR" --export=ALL)
ids=()

if [ "$MODE" = single ]; then
  export SOURCE_ARGS
  ids+=("$(sbatch "${COMMON[@]}" "$HERE/run_all.sbatch")")
elif [ "$MODE" = chain ]; then
  prev=""
  submit() {  # submit <cstwin subcommand> [args...]
    local dep=()
    [ -n "$prev" ] && dep=(--dependency="afterok:$prev" --kill-on-invalid-dep=yes)
    prev=$(sbatch "${COMMON[@]}" "${dep[@]}" --job-name="cstwin-$1" "$HERE/step.sbatch" "$@")
    ids+=("$prev")
  }
  # shellcheck disable=SC2086
  [ -n "$SOURCE_ARGS" ] && submit $SOURCE_ARGS
  for step in produce check onepass indicator report; do submit "$step"; done
else
  echo "unknown mode: $MODE (use chain or single)"; exit 1
fi

printf '%s\n' "${ids[@]}" > "$LOGDIR/job_ids.txt"
echo "run:     $RUN_ID"
echo "jobs:    ${ids[*]}"
echo "logs:    $LOGDIR"
echo "watch:   squeue --me"
echo "metrics: $HERE/sacct_report.sh $LOGDIR"
