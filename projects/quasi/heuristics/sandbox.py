"""Run a search candidate in a fresh process with no network.

The linter runs in the parent first. A violating program costs no compute.
The child is `projects.quasi.heuristics.worker`.
"""

from __future__ import annotations

import pickle
import subprocess

from dsl.errors import LintError, ProgramError
from dsl.sandbox import launcher
from projects.quasi.heuristics.lint import lint
from problem import ROOT, child_env, config, seed


def run(source: str, G, p: int, q: int, theta: int, *, skip_lint: bool = False, wall_seconds: float | None = None, memory_bytes: int | None = None, cpu_seconds: int | None = None, step_limit: int | None = None):
    """Return {ok, S, T, steps, error}."""
    cfg = config()
    if not skip_lint:
        try:
            lint(source)
        except LintError as exc:
            return {"ok": False, "S": [], "T": [], "steps": 0, "error": f"lint: {exc}"}
    if wall_seconds is None:
        wall_seconds = float(cfg["per_evaluation_wall_seconds"])
    if memory_bytes is None:
        memory_bytes = int(cfg["memory_cap_mb"]) * 1024 * 1024
    if cpu_seconds is None:
        cpu_seconds = int(cfg["cpu_seconds_per_eval"])
    payload = {
        "source": source,
        "u": G.u_ids,
        "v": G.v_ids,
        "edges": G.dump_edges(),
        "name": G.name,
        "p": int(p), "q": int(q), "theta": int(theta),
        "memory_bytes": int(memory_bytes),
        "cpu_seconds": int(cpu_seconds),
        "skip_lint": bool(skip_lint),
        "step_limit": step_limit,
        "rng_seed": int(seed()),
    }
    try:
        proc = subprocess.run(
            launcher("projects.quasi.heuristics.worker"),
            input=pickle.dumps(payload),
            capture_output=True,
            timeout=wall_seconds,
            cwd=str(ROOT),
            env=child_env(),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "S": [], "T": [], "steps": 0, "error": "wall-clock timeout"}
    if proc.returncode != 0 or not proc.stdout:
        err = proc.stderr.decode("utf-8", "replace")[-500:]
        return {"ok": False, "S": [], "T": [], "steps": 0, "error": f"sandbox exit {proc.returncode}: {err}"}
    try:
        out = pickle.loads(proc.stdout)
    except Exception as exc:
        raise ProgramError(f"sandbox returned garbage: {exc}") from exc
    return out
