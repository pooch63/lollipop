"""Run one candidate program in a fresh process. Every project uses this.

A project does not get its own sandbox. `run.py` calls `run` here. The
process has no network, a memory cap, and a CPU cap. The candidate defines
`entry(G, params)` and may not import.
"""

from __future__ import annotations

import pickle
import subprocess

from dsl.errors import ProgramError
from dsl.sandbox import launcher
from problem import ROOT, child_env, config


def run(source: str, G, *, entry: str = "search", params: dict | None = None, wall_seconds: float | None = None, memory_bytes: int | None = None, cpu_seconds: int | None = None) -> dict:
    """Return `{ok, result, error}`.

    `result` is whatever `entry(G, params)` returned. On failure `result` is
    None and `error` is a short string.
    """
    cfg = config()
    if wall_seconds is None:
        wall_seconds = float(cfg["per_evaluation_wall_seconds"])
    if memory_bytes is None:
        memory_bytes = int(cfg["memory_cap_mb"]) * 1024 * 1024
    if cpu_seconds is None:
        cpu_seconds = int(cfg["cpu_seconds_per_eval"])
    payload = {
        "source": source,
        "entry": str(entry),
        "params": dict(params or {}),
        "u": list(G.u_ids),
        "v": list(G.v_ids),
        "edges": G.dump_edges(),
        "name": G.name,
        "memory_bytes": int(memory_bytes),
        "cpu_seconds": int(cpu_seconds),
    }
    try:
        proc = subprocess.run(
            launcher("agents.worker"),
            input=pickle.dumps(payload),
            capture_output=True,
            timeout=wall_seconds,
            cwd=str(ROOT),
            env=child_env(),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "result": None, "error": "wall-clock timeout"}
    if proc.returncode != 0 or not proc.stdout:
        err = proc.stderr.decode("utf-8", "replace")[-500:]
        return {"ok": False, "result": None, "error": f"sandbox exit {proc.returncode}: {err}"}
    try:
        out = pickle.loads(proc.stdout)
    except Exception as exc:
        raise ProgramError(f"sandbox returned garbage: {exc}") from exc
    return out
