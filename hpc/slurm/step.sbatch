#!/bin/bash
# One pipeline step = one Slurm job, running the same container image as on Kubernetes.
# Submitted by submit.sh as: sbatch --account=... --partition=... step.sbatch <subcommand> [args]
# (--account and --partition are given on the sbatch command line so no project number is hard-coded.)
#SBATCH --job-name=cstwin-step
#SBATCH --time=00:10:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=512M                 # measured peak ~120 MB per step; keep request modest
#SBATCH --output=%x_%j.out

set -euo pipefail
[ $# -ge 1 ] || { echo "usage: step.sbatch <cstwin subcommand> [args]"; exit 1; }
: "${RUN_ID:?RUN_ID not set}" "${SIF:?}" "${CONFIG:?}" "${SCRATCH_BASE:?}"
command -v apptainer >/dev/null || module load apptainer

WORK="$SCRATCH_BASE/runs"
mkdir -p "$WORK/$RUN_ID"
echo "[slurm] job=$SLURM_JOB_ID step=$* run=$RUN_ID node=$(hostname) start=$(date -Is)"

# Image entrypoint is not used by `apptainer exec`, so call cstwin explicitly.
srun apptainer exec \
  --bind "$WORK:/work" \
  --bind "$(dirname "$CONFIG"):/config:ro" \
  "$SIF" \
  cstwin --config /config/pipeline.yaml --workdir "/work/$RUN_ID" "$@"

echo "[slurm] step=$* finished=$(date -Is)"
