# Running cstwin on an HPC system (Slurm + Apptainer, CSC Roihu)

Same image and same `cstwin` steps as the Kubernetes version.

```bash
./hpc/slurm/submit.sh sample         # one job per step, chained with --dependency=afterok
./hpc/slurm/submit.sh sample-corrupt # quality gate fails -> later jobs cancelled
./hpc/slurm/submit.sh era5           # real ERA5 data
./hpc/slurm/submit.sh era5 single    # whole pipeline in one job
./hpc/slurm/sacct_report.sh <logdir> # queue wait, runtime, MaxRSS per job
```

| Kubernetes (Argo) | Slurm |
|---|---|
| Docker image from GHCR | same image converted to `cstwin.sif` |
| one pod per step | `chain` mode: one job per step (`step.sbatch`) |
| DAG `depends` | `--dependency=afterok` (+ `--kill-on-invalid-dep=yes`) |
| — | `single` mode: all steps in one job (`run_all.sbatch`) |
| PVC `/work` | `$SCRATCH_BASE/runs` bound to `/work` |
| ConfigMap | `config/pipeline.yaml` bound read-only to `/config` |

Job scripts follow the CSC Roihu batch-script structure: explicit `--time`, `--nodes=1`,
`--ntasks=1`, `--cpus-per-task=1`, modest `--mem`, programs launched with `srun`,
small serial steps in the `small` partition (`test` for first tries).
`--account` and `--partition` are passed by `submit.sh` from `env.local.sh`.
