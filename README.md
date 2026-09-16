# climate-stream-twin (`cstwin`)
![ci](https://github.com/yigitbabal/climate-stream-twin/actions/workflows/ci.yml/badge.svg)

A small, containerized **streaming climate-data consumer pipeline** running on Kubernetes (k3s).
It is a scaled-down exercise inspired by the data-consumer side of the Destination Earth
Climate Change Adaptation Digital Twin (Doblas-Reyes et al., 2026, *GMD* 19, 2821–2848).
It does **not** reproduce that system; it uses public ERA5 data (or synthetic data) to practise
the same engineering patterns.

```
source ─► produce ─► check ─► onepass ─► indicator ─┬─► publish ─► prune
(ERA5 or   (daily     (quality  (streaming   (wind       │   (S3 data   (streaming
 sample)    chunks +   gate:     stats with   capacity   │    bridge)    window)
            .ready     stops     checkpoint   factor)    └─► report
            flags)     the run)  + retries)                  (runtime / memory / energy)
```

| Pattern | Implementation here |
|---|---|
| Workflow orchestration | Argo Workflows DAG on k3s, each step in its own pod |
| Containerized, reproducible steps | One Docker image, one CLI subcommand per step |
| Data streaming + notifier | Producer writes daily chunks atomically with `.ready` flags |
| Automated data-quality control | `check` fails on missing variables, wrong units, NaNs, impossible values → workflow stops |
| One-pass statistics | Running mean and per-cell wind histograms, checkpointed after every chunk; retried pods resume |
| Impact indicator | Capacity factor from weekly wind distribution × turbine power curve |
| Data bridge + streaming window | Results synced to S3 (SeaweedFS), old stream chunks pruned |
| CI/CD with metrics | GitHub Actions: unit tests, manifest validation, container e2e run, quality-gate test, performance summary, image push to GHCR |

## Quick start (local, no cluster)

```bash
make install        # pip install -e ".[dev]"
make test
make run            # synthetic data -> full pipeline -> performance table
```

## On k3s

```bash
./scripts/k3s_setup.sh               # namespace, PVC, RBAC, SeaweedFS, Argo Workflows, ConfigMap
make docker-build k3s-import         # build image and load it into k3s containerd
kubectl apply -f k8s/job-smoke.yaml  # sanity check without Argo
kubectl -n cstwin logs -f job/cstwin-smoke

argo submit -n cstwin k8s/workflow.yaml --watch                          # happy path
argo submit -n cstwin k8s/workflow.yaml -p source=sample-corrupt --watch # quality gate stops the run
```

### Real ERA5 data (optional)

```bash
pip install -e ".[fetch]"
cstwin --workdir work fetch                       # Finland, Jan 2024 from public ARCO-ERA5 (edit config/pipeline.yaml)
./scripts/load_raw.sh work/raw/era5_subset.nc     # copy into the PVC
argo submit -n cstwin k8s/workflow.yaml -p source=era5 --watch
```

## Results

Synthetic test data: 14 days of hourly data on a 12 × 14 grid.
Local = plain Python on the server; k3s = Argo Workflows, one pod per step.

| Step | Local wall (s) | k3s wall (s) | Peak RSS in pod (MB) |
|---|---|---|---|
| produce | 0.175 | 0.182 | 97 |
| check | 0.150 | 0.174 | 95 |
| onepass | 0.157 | 0.967 | 96 |
| indicator | 0.026 | 0.049 | 96 |
| **Whole workflow** | < 1 | 91 (1.4 s of actual compute) | |

**Takeaway:** on small data, starting a pod for each step dominates run time
(about 90 of 91 seconds). Per-step pods pay off when steps are heavy or need
different resources; for tiny steps, grouping them into one pod would be faster.
Memory per pod stays under 100 MB, so the 2 Gi limit could be lowered to fit
more pods on a small node.


### Real data: ERA5 reanalysis (Finland, 1–14 January 2024)

Hourly 2 m temperature and 100 m wind from the public ARCO-ERA5 store,
45 × 53 grid points at 0.25°, 336 hours. All 14 daily chunks passed the quality gate.

| Week | Domain-mean capacity factor |
|---|---|
| 1–7 Jan | 0.19 |
| 8–14 Jan | 0.29 |

Local and k3s (Argo) runs produce identical capacity factors (0.189 and 0.289).

| Step | Wall (s) | Peak RSS (MB) |
|---|---|---|
| fetch (download, day by day) | 410 | 247 |
| produce + check + onepass + indicator | 0.8 | 120 |

Capacity factors use a generic turbine power curve and are illustrative, not site estimates.
The first fetch attempt built a dask graph for the whole 2 PB store and ran the server out of
memory; opening lazily and downloading day by day keeps memory under 250 MB.

### HPC: Slurm + Apptainer on CSC Roihu

Same image (pulled from GHCR into a `.sif` file) and same `cstwin` steps, run on Roihu's
`small` partition. Scripts and instructions: [`hpc/`](hpc/README.md).

| Mode | Jobs | First submit → last end | Capacity factors |
|---|---|---|---|
| single (whole pipeline in one job) | 1 | 6 s | 0.189, 0.289 |
| chain (one job per step, `--dependency=afterok`) | 5 | 30 s | 0.189, 0.289 |

Peak memory per step (Slurm `MaxRSS`, including the container runtime): 185–296 MB,
against a 512 MB request.

**Same results everywhere:** local, Kubernetes (Argo) and Slurm (both modes) produce
identical capacity factors on the same ERA5 input.

**Overhead:** each job itself runs in about 3 s; in chain mode, the scheduler adds about
3 s between jobs. For steps this small, a single job is the efficient choice. Chaining
pays off when steps are long or need different resources. On Kubernetes, pod start-up
on a small node added about 10 s per step.

**Note:** CSC's `test` partition allows only 2 submitted jobs per user, so chain mode
runs in `small`; `submit.sh` refuses the test + chain combination.

## Design notes

- **Fail loudly, early.** The quality gate exits with code 2 and nothing downstream runs.
- **Restartable consumers.** `onepass` checkpoints after each chunk; the Argo step has `retryStrategy`,
  and a test verifies that resuming gives the same result as an uninterrupted run.
- **Streaming equals batch.** Tests check the streamed mean against the batch mean.
- **Atomic writes.** Chunks and checkpoints are written to temp files and renamed.
- **Metrics per pod.** Each step records wall time and peak RSS; install `.[energy]` for CodeCarbon estimates.
  (In `run-all` all steps share one process, so peak RSS is cumulative there.)

## Roadmap

- [ ] Run the same steps on an HPC system via Slurm + Apptainer and compare against k3s
- [ ] Swap the in-house one-pass code for the DestinE `one_pass` package
- [ ] Per-day fan-out in Argo (check/consume each chunk as it arrives)
- [ ] Self-hosted GitHub runner on k3s (Actions Runner Controller) for cluster-level e2e tests
- [ ] Benchmark history dashboard on GitHub Pages; regrid to HEALPix; small AI emulator step
- [ ] Enable energy estimates per step (CodeCarbon, `pip install .[energy]`)

## Layout

```
config/pipeline.yaml      region, period, check rules, window, turbine curve
src/cstwin/               cli, producer, checks, onepass, indicator, metrics, housekeeping, fetch_era5, make_sample
tests/                    unit + end-to-end tests (synthetic data, no network)
k8s/                      namespace, PVC, RBAC, data bridge, smoke Job, Argo Workflow
scripts/                  k3s_setup.sh, load_raw.sh
.github/workflows/ci.yml  CI/CD
```
