"""Run a candidate in a fresh process with no network.

The linter runs in the parent first. A violating program costs no compute.
The child is `dsl.worker`. On Linux we prefix it with `unshare -n` when that
command succeeds, which drops the process into an empty network namespace.
"""

from __future__ import annotations

import pickle
import shutil
import subprocess
import sys

from dsl.errors import LintError, ProgramError
from dsl.lint import lint
from problem import ROOT, child_env, config


def _unshare_prefix() -> list[str]:
    if shutil.which("unshare") is None:
        return []
    try:
        probe = subprocess.run(["unshare", "-n", "true"], capture_output=True, timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if probe.returncode == 0:
        return ["unshare", "-n", "--"]
    return []


_PREFIX = None


def launcher(module: str = "dsl.worker") -> list[str]:
    global _PREFIX
    if _PREFIX is None:
        _PREFIX = _unshare_prefix()
    return [*_PREFIX, sys.executable, "-m", module]


def run(source: str, G, p: int, q: int, theta: int, tier: str, *, skip_lint: bool = False, wall_seconds: float | None = None, memory_bytes: int | None = None, cpu_seconds: int | None = None):
    """Return {ok, keep_u, keep_v, cost, error}.

    skip_lint is only for the sandbox-escape test. Production callers lint.
    """
    cfg = config()
    if not skip_lint:
        try:
            lint(source, tier)
        except LintError as exc:
            return {"ok": False, "keep_u": None, "keep_v": None, "cost": 0, "error": f"lint: {exc}"}
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
        "tier": tier,
        "memory_bytes": int(memory_bytes),
        "cpu_seconds": int(cpu_seconds),
        "skip_lint": bool(skip_lint),
    }
    try:
        proc = subprocess.run(
            launcher(),
            input=pickle.dumps(payload),
            capture_output=True,
            timeout=wall_seconds,
            cwd=str(ROOT),
            env=child_env(),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "keep_u": None, "keep_v": None, "cost": 0, "error": "wall-clock timeout"}
    if proc.returncode != 0 or not proc.stdout:
        err = proc.stderr.decode("utf-8", "replace")[-500:]
        return {"ok": False, "keep_u": None, "keep_v": None, "cost": 0, "error": f"sandbox exit {proc.returncode}: {err}"}
    try:
        out = pickle.loads(proc.stdout)
    except Exception as exc:
        raise ProgramError(f"sandbox returned garbage: {exc}") from exc
    return out
