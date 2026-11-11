"""The evolver may read the frozen protocol files and must not be able to write them."""

from __future__ import annotations

import os
from pathlib import Path

from problem import ROOT

PROTOCOL_NAMES = ("config.yaml", "rungs.yaml")


def protocol_paths(root: Path | None = None) -> list[Path]:
    root = root or ROOT
    return [root / name for name in PROTOCOL_NAMES]


def assert_evolver_readonly(paths: list[Path] | None = None) -> None:
    """Refuse to run when a protocol file is writable by this process."""
    for path in paths if paths is not None else protocol_paths():
        if os.access(path, os.W_OK):
            raise SystemExit(f"evolver refuses to run: {path} is writable")
