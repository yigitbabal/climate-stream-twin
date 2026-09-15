"""Fetch a small ERA5 subset from Google's public ARCO-ERA5 Zarr store (anonymous access).

Run on a machine with internet access (not in CI). Requires: pip install -e ".[fetch]"
Store and variable names: https://github.com/google-research/arco-era5

Note: ARCO-ERA5 stores one global field per hour per variable, so even a small
region downloads whole-globe chunks. Keep the period short (1-2 weeks).
"""
from __future__ import annotations

import time
from pathlib import Path

import xarray as xr

ARCO_STORE = "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"
RENAME = {
    "2m_temperature": "t2m",
    "100m_u_component_of_wind": "u100",
    "100m_v_component_of_wind": "v100",
}
# Only harmless spelling differences are normalised. Anything else is left as-is
# so the quality gate in `check` catches it instead of this script hiding it.
UNIT_ALIASES = {"m s**-1": "m s-1", "m/s": "m s-1"}


def fetch(cfg, out: Path, store: str = ARCO_STORE) -> Path:
    region, period = cfg["region"], cfg["period"]
    t0 = time.perf_counter()

    print("[fetch] opening ARCO-ERA5 metadata (can take a minute)...", flush=True)
    # chunks=None: lazy access without building a dask graph for the whole
    # 2 PB store (hundreds of variables x ~750k hourly chunks), which is very slow.
    ds = xr.open_zarr(store, chunks=None, storage_options={"token": "anon"})
    print(f"[fetch] opened in {time.perf_counter() - t0:.0f} s; ERA5 available "
          f"{ds.attrs.get('valid_time_start')} .. {ds.attrs.get('valid_time_stop')}", flush=True)

    ds = ds[list(RENAME)].rename(RENAME)
    # ARCO-ERA5: latitude runs 90 -> -90, longitude 0 -> 360
    ds = ds.sel(
        time=slice(period["start"], f"{period['end']}T23:00"),
        latitude=slice(region["lat_max"], region["lat_min"]),
        longitude=slice(region["lon_min"] % 360, region["lon_max"] % 360),
    )
    days = sorted(set(ds.time.dt.floor("D").values))
    print(f"[fetch] subset: {dict(ds.sizes)}; downloading {len(days)} days...", flush=True)

    # Download one day at a time: visible progress and bounded memory.
    # Within a day, dask fetches the 24 hourly chunks in parallel threads.
    parts = []
    for i, day in enumerate(days, 1):
        t_day = time.perf_counter()
        tag = str(day)[:10]
        part = ds.sel(time=slice(tag, f"{tag}T23:00")).chunk({"time": 1}).load()
        parts.append(part)
        elapsed = time.perf_counter() - t0
        eta = (elapsed / i) * (len(days) - i)
        print(f"[fetch] day {i}/{len(days)} {tag} done in {time.perf_counter() - t_day:.0f} s "
              f"(elapsed {elapsed:.0f} s, ~{eta:.0f} s left)", flush=True)
    ds = xr.concat(parts, dim="time")

    for var in ds.data_vars:
        units = ds[var].attrs.get("units")
        ds[var].attrs["units"] = UNIT_ALIASES.get(units, units)
    # Zarr-specific encodings (compressor, chunks) break NetCDF writing
    for name in ds.variables:
        ds[name].encoding = {}
    ds.attrs = {"source": "ARCO-ERA5 (Google Research)", "store": store}

    out.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(out)
    size_mb = out.stat().st_size / 1e6
    print(f"[fetch] wrote {out} ({size_mb:.1f} MB) in {time.perf_counter() - t0:.0f} s")
    return out
