"""Simulated model output stream: split the raw dataset into daily chunks.

Each chunk gets a `.ready` flag once fully written, mimicking the Climate DT
"data notifier" that tells consumers new data is available.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr


def produce(raw: Path, stream_dir: Path, max_days: int | None = None) -> list[Path]:
    stream_dir.mkdir(parents=True, exist_ok=True)
    ds = xr.open_dataset(raw)
    days = np.unique(ds.time.dt.floor("D").values)
    if max_days:
        days = days[:max_days]
    written = []
    for day in days:
        tag = str(day)[:10]
        chunk = ds.sel(time=slice(np.datetime64(tag), np.datetime64(tag) + np.timedelta64(23, "h")))
        path = stream_dir / f"{tag}.nc"
        tmp = path.with_suffix(".nc.tmp")
        chunk.to_netcdf(tmp)
        tmp.rename(path)                           # atomic: consumers never see partial files
        (stream_dir / f"{tag}.ready").touch()      # data notifier
        written.append(path)
    ds.close()
    return written


def ready_chunks(stream_dir: Path) -> list[Path]:
    return sorted(p.with_suffix(".nc") for p in stream_dir.glob("*.ready"))
