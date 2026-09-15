import json

from cstwin.cli import main
from cstwin.producer import ready_chunks


def test_report_and_prune(cfg):
    common = ["--config", "config/pipeline.yaml", "--workdir", str(cfg.workdir)]
    main(common + ["sample", "--days", "7"])
    assert main(common + ["run-all"]) == 0
    assert main(common + ["report"]) == 0
    summary = json.loads((cfg.workdir / "run_report.json").read_text())
    assert [s["step"] for s in summary["steps"]] == ["sample", "produce", "check", "onepass", "indicator"]
    assert main(common + ["prune", "--keep-days", "2"]) == 0
    assert len(ready_chunks(cfg.path("stream"))) == 2
