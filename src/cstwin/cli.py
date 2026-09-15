"""Command-line entry point. Every step is a separate subcommand so each can run as its own
container/pod in the workflow, while `run-all` chains them for local runs and CI."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .checks import DataQualityError, check_all
from .config import Config
from .indicator import capacity_factor
from .metrics import track
from .producer import produce, ready_chunks


def step_sample(cfg, args):
    from .make_sample import make_sample
    make_sample(cfg.path("raw"), days=args.days, corrupt=args.corrupt)


def step_fetch(cfg, args):
    from .fetch_era5 import fetch
    fetch(cfg, cfg.path("raw"))


def step_produce(cfg, args):
    produce(cfg.path("raw"), cfg.path("stream"), max_days=args.max_days)


def step_check(cfg, args):
    check_all(ready_chunks(cfg.path("stream")), cfg["checks"])


def step_onepass(cfg, args):
    from .onepass import run_onepass
    run_onepass(ready_chunks(cfg.path("stream")), cfg.path("state"), cfg.path("outputs"), cfg["onepass"])


def step_indicator(cfg, args):
    files = sorted(cfg.path("outputs").glob("*_weekly_stats.nc"))
    if not files:
        raise RuntimeError("no weekly statistics found; did onepass run?")
    for f in files:
        capacity_factor(f, cfg["turbine"], cfg.path("outputs"))


def step_report(cfg, args):
    from .housekeeping import report
    report(cfg.path("metrics"), cfg.workdir / "run_report.json")


def step_prune(cfg, args):
    from .housekeeping import prune_stream
    prune_stream(cfg.path("stream"), args.keep_days)


STEPS = {
    "sample": step_sample, "fetch": step_fetch, "produce": step_produce,
    "check": step_check, "onepass": step_onepass, "indicator": step_indicator,
    "report": step_report, "prune": step_prune,
}
UNTRACKED = {"report", "prune"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cstwin")
    ap.add_argument("--config", default="config/pipeline.yaml")
    ap.add_argument("--workdir", default="work")
    sub = ap.add_subparsers(dest="step", required=True)
    s = sub.add_parser("sample"); s.add_argument("--days", type=int, default=14)
    s.add_argument("--corrupt", action="store_true")
    sub.add_parser("fetch")
    p = sub.add_parser("produce"); p.add_argument("--max-days", type=int, default=None)
    for name in ("check", "onepass", "indicator", "report"):
        sub.add_parser(name)
    pr = sub.add_parser("prune"); pr.add_argument("--keep-days", type=int, default=3)
    r = sub.add_parser("run-all"); r.add_argument("--max-days", type=int, default=None)
    args = ap.parse_args(argv)

    cfg = Config.load(args.config, args.workdir)
    steps = ["produce", "check", "onepass", "indicator"] if args.step == "run-all" else [args.step]
    try:
        for name in steps:
            if name in UNTRACKED:
                STEPS[name](cfg, args)
                continue
            with track(name, cfg.path("metrics")):
                STEPS[name](cfg, args)
    except DataQualityError as exc:
        print(f"[cstwin] STOPPED by quality gate: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
