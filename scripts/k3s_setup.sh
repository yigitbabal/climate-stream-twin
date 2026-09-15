#!/usr/bin/env bash
# One-time setup of the cstwin stack on a single-node k3s cluster.
set -euo pipefail
ARGO_VERSION="${ARGO_VERSION:-v4.1.3}"   # check https://github.com/argoproj/argo-workflows/releases

echo ">> namespace, storage, RBAC, data bridge"
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-storage.yaml -f k8s/02-rbac.yaml -f k8s/03-data-bridge.yaml

echo ">> pipeline config as ConfigMap (edit config/pipeline.yaml, re-run to update)"
kubectl -n cstwin create configmap cstwin-config \
  --from-file=pipeline.yaml=config/pipeline.yaml --dry-run=client -o yaml | kubectl apply -f -

if ! kubectl get ns argo >/dev/null 2>&1; then
  echo ">> installing Argo Workflows ${ARGO_VERSION}"
  kubectl create namespace argo
  kubectl apply --server-side -n argo \
    -f "https://github.com/argoproj/argo-workflows/releases/download/${ARGO_VERSION}/install.yaml"
fi
kubectl -n argo rollout status deploy/workflow-controller --timeout=180s
kubectl -n cstwin rollout status deploy/seaweedfs --timeout=180s

cat <<MSG

Done. Next:
  make docker-build k3s-import        # load image into k3s
  kubectl apply -f k8s/job-smoke.yaml # sanity check without Argo
  make argo-submit                    # full DAG (needs the argo CLI)
Argo UI: kubectl -n argo port-forward svc/argo-server 2746:2746  ->  https://localhost:2746
MSG
