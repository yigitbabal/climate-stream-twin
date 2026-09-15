"""Impact indicator: wind-turbine capacity factor from the streamed wind-speed histogram.

Mirrors the Climate DT wind-energy use case: a weekly wind-speed distribution per grid
cell is combined with a turbine power curve, so the hourly series never has to be stored.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr


def power_curve(ws: np.ndarray, cut_in: float, rated: float, cut_out: float) -> np.ndarray:
    """Normalised power output (0..1) of a generic turbine."""
    ws = np.asarray(ws, dtype="float64")
    p = np.where((ws >= cut_in) & (ws < rated), (ws**3 - cut_in**3) / (rated**3 - cut_in**3), 0.0)
    return np.where((ws >= rated) & (ws < cut_out), 1.0, p)


def capacity_factor(stats_file: Path, turbine: dict, out_dir: Path) -> Path:
    with xr.open_dataset(stats_file) as ds:
        hist = ds["wind100_hist"]
        prob = hist / hist.sum("wind_bin")
        curve = xr.DataArray(power_curve(ds.wind_bin.values, **turbine), dims="wind_bin")
        cf = (prob * curve).sum("wind_bin")
        cf.attrs = {"units": "1", "long_name": "wind turbine capacity factor"}
        out = xr.Dataset({"capacity_factor": cf}, attrs=ds.attrs)
    path = out_dir / stats_file.name.replace("_weekly_stats.nc", "_capacity_factor.nc")
    out.to_netcdf(path)
    print(f"[indicator] {path.name}: domain-mean CF = {float(cf.mean()):.3f}")
    return path
