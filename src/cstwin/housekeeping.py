"""Run report (merged metrics) and streaming-window pruning."""
from __future__ import annotations

import json
from pathlib import Path


def report(metrics_dir: Path, out: Path) -> dict:
    order = ["sample", "fetch", "produce", "check", "onepass", "indicator"]
    recs = {p.stem: json.loads(p.read_text()) for p in metrics_dir.glob("*.json")}
    steps = [recs[s] for s in order if s in recs]
    summary = {
        "steps": steps,
        "total_wall_seconds": round(sum(s["wall_seconds"] for s in steps), 3),
        "max_peak_rss_mb": max((s["peak_rss_mb"] for s in steps), default=0),
        "total_energy_kwh": sum(s.get("energy_kwh") or 0 for s in steps) or None,
    }
    out.write_text(json.dumps(summary, indent=2))
    print(f"{'step':<10} {'status':<7} {'wall_s':>8} {'rss_MB':>8} {'energy_kWh':>11}")
    for s in steps:
        e = s.get("energy_kwh")
        print(f"{s['step']:<10} {s['status']:<7} {s['wall_seconds']:>8} {s['peak_rss_mb']:>8} "
              f"{(f'{e:.2e}' if e else '-'):>11}")
    return summary


def prune_stream(stream_dir: Path, keep_days: int) -> list[Path]:
    """Delete the oldest consumed chunks, keeping the newest `keep_days` (the streaming window)."""
    chunks = sorted(stream_dir.glob("*.nc"))
    removed = chunks[:-keep_days] if keep_days > 0 else chunks
    for c in removed:
        c.unlink()
        c.with_suffix(".ready").unlink(missing_ok=True)
        print(f"[prune] removed {c.name}")
    return removed
