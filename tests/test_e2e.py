import json

import xarray as xr

from cstwin.cli import main


def test_run_all_end_to_end(cfg):
    common = ["--config", "config/pipeline.yaml", "--workdir", str(cfg.workdir)]
    assert main(common + ["sample", "--days", "14"]) == 0
    assert main(common + ["run-all"]) == 0
    cf_files = sorted(cfg.path("outputs").glob("*_capacity_factor.nc"))
    assert len(cf_files) == 2
    cf = xr.load_dataset(cf_files[0])["capacity_factor"]
    assert float(cf.min()) >= 0 and float(cf.max()) <= 1
    for step in ("produce", "check", "onepass", "indicator"):
        rec = json.loads((cfg.path("metrics") / f"{step}.json").read_text())
        assert rec["status"] == "ok" and rec["wall_seconds"] >= 0


def test_quality_gate_returns_nonzero(cfg):
    common = ["--config", "config/pipeline.yaml", "--workdir", str(cfg.workdir)]
    main(common + ["sample", "--days", "7", "--corrupt"])
    assert main(common + ["run-all"]) == 2
    assert not list(cfg.path("outputs").glob("*.nc"))  # nothing downstream ran
