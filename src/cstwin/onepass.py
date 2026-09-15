"""One-pass (streaming) statistics with checkpointing.

Chunks are consumed one at a time; only running summaries are kept in memory, never the
full time series. State is checkpointed after every chunk, so a restarted pod resumes
where it stopped (the Climate DT uses the same idea for restarts after model failures).

This is a small self-contained implementation. Swapping in the DestinE `one_pass`
package (https://github.com/DestinE-Climate-DT/one_pass) is a good follow-up task.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import xarray as xr


class StreamingStats:
    def __init__(self, shape: tuple[int, int], bin_edges: np.ndarray):
        self.bin_edges = bin_edges
        self.n = 0
        self.t2m_sum = np.zeros(shape, dtype="float64")
        self.hist = np.zeros((*shape, bin_edges.size - 1), dtype="int64")

    def update(self, t2m: np.ndarray, wind: np.ndarray) -> None:
        """t2m, wind: arrays (time, lat, lon)."""
        self.n += t2m.shape[0]
        self.t2m_sum += t2m.sum(axis=0)
        idx = np.clip(np.digitize(wind, self.bin_edges) - 1, 0, self.hist.shape[-1] - 1)
        nt, ny, nx = idx.shape
        flat = (np.arange(ny * nx).reshape(1, ny, nx) * self.hist.shape[-1] + idx).ravel()
        self.hist += np.bincount(flat, minlength=self.hist.size).reshape(self.hist.shape)

    @property
    def t2m_mean(self) -> np.ndarray:
        return self.t2m_sum / max(self.n, 1)

    # --- checkpointing -------------------------------------------------------------
    def save(self, path: Path, meta: dict) -> None:
        tmp = path.with_suffix(".tmp.npz")
        np.savez(tmp, n=self.n, t2m_sum=self.t2m_sum, hist=self.hist, bin_edges=self.bin_edges)
        tmp.rename(path.with_suffix(".npz"))
        path.with_suffix(".json").write_text(json.dumps(meta))

    @classmethod
    def load(cls, path: Path) -> tuple["StreamingStats", dict]:
        z = np.load(path.with_suffix(".npz"))
        obj = cls(z["t2m_sum"].shape, z["bin_edges"])
        obj.n, obj.t2m_sum, obj.hist = int(z["n"]), z["t2m_sum"], z["hist"]
        return obj, json.loads(path.with_suffix(".json").read_text())


def run_onepass(chunks: list[Path], state_dir: Path, out_dir: Path, cfg: dict) -> list[Path]:
    state_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt = state_dir / "stats"
    edges = np.arange(0.0, cfg["hist_max"] + cfg["hist_bin_width"], cfg["hist_bin_width"])
    window = cfg["window_days"]

    stats, meta = None, {"consumed": [], "window_start": None}
    if ckpt.with_suffix(".json").exists():
        stats, meta = StreamingStats.load(ckpt)
        print(f"[onepass] resuming from checkpoint, {len(meta['consumed'])} chunks consumed")

    written = []
    for chunk in chunks:
        if chunk.name in meta["consumed"]:
            continue
        with xr.open_dataset(chunk) as ds:
            t2m = ds["t2m"].values
            wind = np.hypot(ds["u100"].values, ds["v100"].values)
            coords = {"latitude": ds.latitude.values, "longitude": ds.longitude.values}
        if stats is None:
            stats = StreamingStats(t2m.shape[1:], edges)
        if meta["window_start"] is None:
            meta["window_start"] = chunk.stem
        stats.update(t2m, wind)
        meta["consumed"].append(chunk.name)
        print(f"[onepass] consumed {chunk.name}")

        if len(meta["consumed"]) % window == 0:  # window complete -> emit statistic, reset summaries
            written.append(_emit(stats, coords, meta["window_start"], chunk.stem, out_dir))
            stats = StreamingStats(t2m.shape[1:], edges)
            meta["window_start"] = None
        stats.save(ckpt, meta)
    return written


def _emit(stats: StreamingStats, coords: dict, start: str, end: str, out_dir: Path) -> Path:
    centers = 0.5 * (stats.bin_edges[:-1] + stats.bin_edges[1:])
    ds = xr.Dataset(
        {
            "t2m_mean": (("latitude", "longitude"), stats.t2m_mean, {"units": "K"}),
            "wind100_hist": (("latitude", "longitude", "wind_bin"), stats.hist),
        },
        coords={**coords, "wind_bin": centers},
        attrs={"window_start": start, "window_end": end, "n_steps": stats.n},
    )
    path = out_dir / f"{start}to{end}_weekly_stats.nc"
    ds.to_netcdf(path)
    print(f"[onepass] wrote {path.name}")
    return path
