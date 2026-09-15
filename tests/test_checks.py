import pytest

from cstwin.checks import DataQualityError, check_all, check_chunk
from cstwin.make_sample import make_sample
from cstwin.producer import produce, ready_chunks


def test_clean_data_passes(cfg):
    make_sample(cfg.path("raw"), days=2)
    produce(cfg.path("raw"), cfg.path("stream"))
    reports = check_all(ready_chunks(cfg.path("stream")), cfg["checks"])
    assert all(r.ok for r in reports)


def test_impossible_values_stop_workflow(cfg):
    make_sample(cfg.path("raw"), days=2, corrupt=True)
    produce(cfg.path("raw"), cfg.path("stream"))
    with pytest.raises(DataQualityError):
        check_all(ready_chunks(cfg.path("stream")), cfg["checks"])


def test_wrong_units_detected(cfg):
    import xarray as xr
    make_sample(cfg.path("raw"), days=1)
    chunk = produce(cfg.path("raw"), cfg.path("stream"))[0]
    ds = xr.load_dataset(chunk)
    ds["t2m"].attrs["units"] = "degC"
    ds.to_netcdf(chunk)
    rep = check_chunk(chunk, cfg["checks"])
    assert any("units" in e for e in rep.errors)
