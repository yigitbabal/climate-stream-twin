"""Data-quality gate. Any failure raises, which makes the pod/job fail and stops the workflow."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import xarray as xr


class DataQualityError(RuntimeError):
    pass


@dataclass
class Report:
    chunk: str
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def check_chunk(path: Path, rules: dict) -> Report:
    rep = Report(chunk=path.name)
    with xr.open_dataset(path) as ds:
        for var in rules["required_vars"]:
            if var not in ds:
                rep.errors.append(f"missing variable '{var}'")
                continue
            da = ds[var]
            expected = rules["units"].get(var)
            if expected and da.attrs.get("units") != expected:
                rep.errors.append(f"{var}: units '{da.attrs.get('units')}' != '{expected}'")
            n_nan = int(da.isnull().sum())
            if n_nan:
                rep.errors.append(f"{var}: {n_nan} missing values")
            lo, hi = rules["ranges"][var]
            vmin, vmax = float(da.min()), float(da.max())
            if vmin < lo or vmax > hi:
                rep.errors.append(f"{var}: values [{vmin:.1f}, {vmax:.1f}] outside [{lo}, {hi}]")

        if ds.sizes.get("time") != rules["steps_per_day"]:
            rep.errors.append(f"time steps {ds.sizes.get('time')} != {rules['steps_per_day']}")
        elif not np.all(np.diff(ds.time.values) == np.timedelta64(1, "h")):
            rep.errors.append("time axis is not strictly hourly")
    return rep


def check_all(chunks: list[Path], rules: dict) -> list[Report]:
    reports = [check_chunk(c, rules) for c in chunks]
    failed = [r for r in reports if not r.ok]
    for r in reports:
        print(f"[check] {r.chunk}: {'OK' if r.ok else 'FAIL'}")
        for e in r.errors:
            print(f"        - {e}")
    if not chunks:
        raise DataQualityError("no ready chunks found")
    if failed:
        raise DataQualityError(f"{len(failed)}/{len(reports)} chunks failed quality checks")
    return reports
