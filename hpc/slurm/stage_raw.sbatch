#!/bin/bash
# Copies the pre-downloaded ERA5 file into this run's raw/ folder (Slurm equivalent of Argo's stage-raw).
#SBATCH --job-name=cstwin-stage-raw
#SBATCH --ntasks=1
#SBATCH --mem=500M
#SBATCH --time=00:05:00
#SBATCH --output=%x_%j.out
set -euo pipefail
: "${RUN_ID:?}" "${SCRATCH_BASE:?}" "${RAW_ERA5:?}"
mkdir -p "$SCRATCH_BASE/runs/$RUN_ID/raw"
cp "$RAW_ERA5" "$SCRATCH_BASE/runs/$RUN_ID/raw/era5_subset.nc"
echo "[slurm] staged $RAW_ERA5"
