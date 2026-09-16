#!/bin/bash
# One pipeline step = one Slurm job, running the same container image as on Kubernetes.
# Submitted by submit.sh as: sbatch ... step.sbatch <subcommand> [args], with RUN_ID exported
#SBATCH --job-name=cstwin
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:15:00
#SBATCH --output=%x_%j.out

set -euo pipefail
[ $# -ge 1 ] || { echo "usage: step.sbatch <cstwin subcommand> [args]"; exit 1; }
: "${RUN_ID:?RUN_ID not set}" "${SIF:?}" "${CONFIG:?}" "${SCRATCH_BASE:?}"

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
