# Site settings for Roihu. Copy to env.local.sh and edit, or export these before submitting.
# env.local.sh is ignored by git so your project number stays out of the repo.
export CSC_PROJECT="${CSC_PROJECT:-project_XXXXXXX}"
export PARTITION="${PARTITION:-small}"            # use "test" for a quick first try
export SCRATCH_BASE="${SCRATCH_BASE:-/scratch/$CSC_PROJECT/$USER/cstwin}"
export SIF="${SIF:-$SCRATCH_BASE/images/cstwin.sif}"
export CONFIG="${CONFIG:-$SCRATCH_BASE/config/pipeline.yaml}"
export RAW_ERA5="${RAW_ERA5:-$SCRATCH_BASE/shared/era5_subset.nc}"
