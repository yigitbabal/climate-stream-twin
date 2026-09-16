#!/bin/bash
# Whole pipeline in ONE Slurm job. For tiny steps this avoids queueing six separate jobs
# (CSC recommends not flooding the scheduler with very short jobs), and is the fair
# comparison point against the one-job-per-step chain.
#SBATCH --job-name=cstwin-run-all
#SBATCH --time=00:15:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=512M
#SBATCH --output=%x_%j.out

set -euo pipefail
: "${RUN_ID:?}" "${SIF:?}" "${CONFIG:?}" "${SCRATCH_BASE:?}" "${SOURCE_ARGS:=}"
command -v apptainer >/dev/null || module load apptainer

WORK="$SCRATCH_BASE/runs"
mkdir -p "$WORK/$RUN_ID"
run() {
  srun apptainer exec --bind "$WORK:/work" --bind "$(dirname "$CONFIG"):/config:ro" "$SIF" \
    cstwin --config /config/pipeline.yaml --workdir "/work/$RUN_ID" "$@"
}
echo "[slurm] job=$SLURM_JOB_ID run=$RUN_ID node=$(hostname) start=$(date -Is)"
# shellcheck disable=SC2086
[ -n "$SOURCE_ARGS" ] && run $SOURCE_ARGS
run run-all
run report
echo "[slurm] finished=$(date -Is)"
