from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Config:
    raw: dict
    workdir: Path

    @classmethod
    def load(cls, path: str | Path, workdir: str | Path) -> "Config":
        with open(path) as fh:
            raw = yaml.safe_load(fh)
        return cls(raw=raw, workdir=Path(workdir))

    def path(self, key: str) -> Path:
        p = self.workdir / self.raw["paths"][key]
        (p.parent if p.suffix else p).mkdir(parents=True, exist_ok=True)
        return p

    def __getitem__(self, key: str):
        return self.raw[key]
