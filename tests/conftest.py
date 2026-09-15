from pathlib import Path

import pytest

from cstwin.config import Config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cfg(tmp_path):
    return Config.load(ROOT / "config" / "pipeline.yaml", tmp_path)
