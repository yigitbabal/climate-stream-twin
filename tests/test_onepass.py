import numpy as np
import xarray as xr

from cstwin.make_sample import make_sample
from cstwin.onepass import run_onepass
from cstwin.producer import produce, ready_chunks


def test_streaming_mean_equals_batch_mean(cfg):
    make_sample(cfg.path("raw"), days=7)
    produce(cfg.path("raw"), cfg.path("stream"))
    out = run_onepass(ready_chunks(cfg.path("stream")), cfg.path("state"), cfg.path("outputs"), cfg["onepass"])
    assert len(out) == 1
    batch = xr.load_dataset(cfg.path("raw"))["t2m"].mean("time").values
    streamed = xr.load_dataset(out[0])["t2m_mean"].values
    np.testing.assert_allclose(streamed, batch, rtol=1e-5)


def test_histogram_counts_every_timestep(cfg):
    make_sample(cfg.path("raw"), days=7)
    produce(cfg.path("raw"), cfg.path("stream"))
    out = run_onepass(ready_chunks(cfg.path("stream")), cfg.path("state"), cfg.path("outputs"), cfg["onepass"])
    hist = xr.load_dataset(out[0])["wind100_hist"]
    assert (hist.sum("wind_bin") == 7 * 24).all()


def test_resume_from_checkpoint_gives_same_result(cfg, tmp_path):
    make_sample(cfg.path("raw"), days=7)
    chunks = produce(cfg.path("raw"), cfg.path("stream"))
    # simulate a pod crash after 3 chunks, then a restart that sees all chunks
    run_onepass(chunks[:3], cfg.path("state"), cfg.path("outputs"), cfg["onepass"])
    out = run_onepass(chunks, cfg.path("state"), cfg.path("outputs"), cfg["onepass"])
    batch = xr.load_dataset(cfg.path("raw"))["t2m"].mean("time").values
    np.testing.assert_allclose(xr.load_dataset(out[0])["t2m_mean"].values, batch, rtol=1e-5)
