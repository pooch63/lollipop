"""Shared grid, seed, and config loading."""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
CONFIG_PATH = ROOT / "config.yaml"


def child_env() -> dict[str, str]:
    """Environment for a fresh interpreter that must import src/ and projects/."""
    env = os.environ.copy()
    roots = os.pathsep.join((str(SRC), str(ROOT)))
    prev = env.get("PYTHONPATH")
    env["PYTHONPATH"] = roots if not prev else roots + os.pathsep + prev
    return env

_cfg = None


def config() -> dict:
    global _cfg
    if _cfg is None:
        with open(CONFIG_PATH) as f:
            _cfg = yaml.safe_load(f)
    return _cfg


def reload_config() -> dict:
    global _cfg
    _cfg = None
    return config()


def write_lambda(value: float) -> None:
    """Replace the lambda line in config.yaml. Does not touch other keys."""
    text = CONFIG_PATH.read_text()
    rendered = f"{float(value):.2f}".rstrip("0").rstrip(".")
    if "." not in rendered:
        rendered += ".0"
    updated, n = re.subn(r"(?m)^lambda:.*$", f"lambda: {rendered}", text, count=1)
    if n != 1:
        raise RuntimeError("config.yaml has no lambda line to update")
    CONFIG_PATH.write_text(updated)
    reload_config()


def seed() -> int:
    return int(config()["seed"])


def gamma_grid() -> list[tuple[int, int]]:
    return [tuple(pair) for pair in config()["gamma"]]


def theta_grid() -> list[int]:
    return [int(t) for t in config()["theta"]]


def cells() -> list[tuple[int, int, int]]:
    """(p, q, theta) for every grid point. gamma = p/q in integers."""
    out = []
    for p, q in gamma_grid():
        for theta in theta_grid():
            out.append((int(p), int(q), int(theta)))
    return out


def ceil_div(num: int, den: int) -> int:
    """Smallest integer >= num/den. den > 0. Exact integer arithmetic."""
    if den <= 0:
        raise ValueError("denominator must be positive")
    if num <= 0:
        return 0
    return (num + den - 1) // den


def data_roots() -> list[str]:
    return [os.path.abspath(p) for p in config()["data_roots"]]
