"""Generate a small synthetic ERA5-like dataset (used by tests and CI, no network)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


def make_sample(out: Path, days: int = 14, nlat: int = 12, nlon: int = 14, seed: int = 0,
                corrupt: bool = False) -> Path:
    rng = np.random.default_rng(seed)
    time = pd.date_range("2024-01-01", periods=days * 24, freq="h")
    lat = np.linspace(70.0, 60.0, nlat)
    lon = np.linspace(20.0, 31.0, nlon)
    shape = (time.size, nlat, nlon)
    hours = np.arange(time.size)[:, None, None]

    t2m = 265.0 + 5.0 * np.sin(2 * np.pi * hours / 24) + rng.normal(0, 2, shape)
    u100 = 6.0 + rng.normal(0, 4, shape)
    v100 = rng.normal(0, 4, shape)

    ds = xr.Dataset(
        {
            "t2m": (("time", "latitude", "longitude"), t2m.astype("float32"), {"units": "K"}),
            "u100": (("time", "latitude", "longitude"), u100.astype("float32"), {"units": "m s-1"}),
            "v100": (("time", "latitude", "longitude"), v100.astype("float32"), {"units": "m s-1"}),
        },
        coords={"time": time, "latitude": lat, "longitude": lon},
        attrs={"source": "synthetic sample for cstwin tests"},
    )
    if corrupt:  # physically impossible values to prove the check stops the workflow
        ds["t2m"][30, 2, 3] = 500.0
    out.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(out)
    return out
