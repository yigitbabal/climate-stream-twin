# Running cstwin on an HPC system (Slurm + Apptainer)

Same image and same `cstwin` steps as the Kubernetes version; each step is one Slurm job,
chained with `--dependency=afterok` so a failed quality gate stops the rest.

| Kubernetes (Argo) | Slurm |
|---|---|
| Docker image from GHCR | same image converted to `cstwin.sif` |
| one pod per step | one job per step (`step.sbatch`) |
| DAG `depends` | `--dependency=afterok` |
| PVC `/work` | `$SCRATCH_BASE/runs` bound to `/work` |
| ConfigMap | `config/pipeline.yaml` bound read-only to `/config` |
| run report | pipeline `report` step + `sacct_report.sh` (queue wait, MaxRSS) |
