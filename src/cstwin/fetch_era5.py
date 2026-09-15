"""Fetch a small ERA5 subset from Google's public ARCO-ERA5 Zarr store (anonymous access).

Run this on a machine with internet access (laptop), not inside CI.
Requires: pip install .[fetch]
Verify the store path/variable names against the ARCO-ERA5 README before first use:
https://github.com/google-research/arco-era5
"""
from __future__ import annotations

from pathlib import Path

import xarray as xr

ARCO_STORE = "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"
RENAME = {
    "2m_temperature": "t2m",
    "100m_u_component_of_wind": "u100",
    "100m_v_component_of_wind": "v100",
}
UNITS = {"t2m": "K", "u100": "m s-1", "v100": "m s-1"}


def fetch(cfg, out: Path) -> Path:
    region, period = cfg["region"], cfg["period"]
    ds = xr.open_zarr(ARCO_STORE, chunks=None, storage_options={"token": "anon"})
    ds = ds[list(RENAME)].rename(RENAME)
    # ARCO-ERA5 uses 0..360 longitudes and descending latitudes
    ds = ds.sel(
        time=slice(period["start"], f"{period['end']}T23:00"),
        latitude=slice(region["lat_max"], region["lat_min"]),
        longitude=slice(region["lon_min"] % 360, region["lon_max"] % 360),
    )
    for var, unit in UNITS.items():
        ds[var].attrs["units"] = unit
    out.parent.mkdir(parents=True, exist_ok=True)
    ds.load().to_netcdf(out)
    return out
