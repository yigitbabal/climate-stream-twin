#!/usr/bin/env bash
# Copy a locally fetched ERA5 subset into the work PVC at /work/shared/era5_subset.nc
#   cstwin --workdir work fetch            # on a machine with internet: pip install ".[fetch]"
#   ./scripts/load_raw.sh work/raw/era5_subset.nc
set -euo pipefail
SRC="${1:?usage: load_raw.sh path/to/era5_subset.nc}"

kubectl -n cstwin run pvc-loader --image=busybox:1.36 --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"pvc-loader","image":"busybox:1.36",
    "command":["sleep","600"],"volumeMounts":[{"name":"work","mountPath":"/work"}]}],
    "volumes":[{"name":"work","persistentVolumeClaim":{"claimName":"cstwin-work"}}]}}'
kubectl -n cstwin wait --for=condition=Ready pod/pvc-loader --timeout=120s
kubectl -n cstwin exec pvc-loader -- sh -c 'mkdir -p /work/shared && chmod 777 /work/shared'
kubectl -n cstwin cp "$SRC" pvc-loader:/work/shared/era5_subset.nc
kubectl -n cstwin exec pvc-loader -- ls -lh /work/shared
kubectl -n cstwin delete pod pvc-loader --wait=false
