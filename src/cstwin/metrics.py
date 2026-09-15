"""Per-step performance and (optional) energy metrics written as JSON."""
from __future__ import annotations

import json
import resource
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


@contextmanager
def track(step: str, metrics_dir: Path):
    tracker = None
    try:  # energy estimate is optional: pip install .[energy]
        from codecarbon import OfflineEmissionsTracker

        tracker = OfflineEmissionsTracker(
            country_iso_code="FIN", save_to_file=False, log_level="error"
        )
        tracker.start()
    except Exception:
        tracker = None

    t0 = time.perf_counter()
    status = "ok"
    try:
        yield
    except Exception:
        status = "failed"
        raise
    finally:
        record = {
            "step": step,
            "status": status,
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "wall_seconds": round(time.perf_counter() - t0, 3),
            # ru_maxrss is KiB on Linux
            "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        }
        if tracker is not None:
            emissions_kg = tracker.stop()
            data = tracker.final_emissions_data
            record["energy_kwh"] = getattr(data, "energy_consumed", None)
            record["co2eq_kg"] = emissions_kg
        metrics_dir.mkdir(parents=True, exist_ok=True)
        (metrics_dir / f"{step}.json").write_text(json.dumps(record, indent=2))
