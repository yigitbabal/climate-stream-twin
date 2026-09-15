# climate-stream-twin (`cstwin`)

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

<!-- Fill in after running: wall time, peak memory, energy per step, local vs k3s. -->

| Step | Local wall (s) | k3s wall (s) | Peak RSS (MB) | Energy (kWh) |
|---|---|---|---|---|
| produce | | | | |
| check | | | | |
| onepass | | | | |
| indicator | | | | |

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

## Layout

```
config/pipeline.yaml      region, period, check rules, window, turbine curve
src/cstwin/               cli, producer, checks, onepass, indicator, metrics, housekeeping, fetch_era5, make_sample
tests/                    unit + end-to-end tests (synthetic data, no network)
k8s/                      namespace, PVC, RBAC, data bridge, smoke Job, Argo Workflow
scripts/                  k3s_setup.sh, load_raw.sh
.github/workflows/ci.yml  CI/CD
```
