"""Subprocess entry for one search program. No network, no file reads."""

from __future__ import annotations

import os
import pickle
import resource
import sys


def _lock_down() -> None:
    import socket

    class _BlockedSocket:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("network disabled")

    socket.socket = _BlockedSocket
    socket.create_connection = _BlockedSocket
    socket.socketpair = _BlockedSocket

    def _audit(event, args):
        if event in {"open", "socket.connect", "socket.bind", "socket.send", "socket.sendto", "subprocess.Popen"} or event.startswith("socket."):
            raise RuntimeError(f"sandbox blocked {event}")

    sys.addaudithook(_audit)


def _scrub_env() -> None:
    for key in list(os.environ):
        upper = key.upper()
        if any(mark in upper for mark in ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD")):
            os.environ.pop(key, None)


def main() -> None:
    from graphs import BipartiteGraph
    from dsl.errors import ProgramError
    from projects.quasi.heuristics.runtime import execute

    payload = pickle.load(sys.stdin.buffer)
    _scrub_env()
    mem = int(payload["memory_bytes"])
    cpu = int(payload["cpu_seconds"])
    if mem > 0:
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    if cpu > 0:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    _lock_down()
    G = BipartiteGraph.from_edges(payload["edges"], payload["u"], payload["v"], name=payload.get("name"))
    try:
        S, T, steps = execute(
            payload["source"], G,
            payload["p"], payload["q"], payload["theta"],
            check_lint=not payload.get("skip_lint", False),
            step_limit_value=payload.get("step_limit"),
            rng_seed=payload.get("rng_seed"),
        )
        out = {"ok": True, "S": S, "T": T, "steps": steps, "error": None}
    except ProgramError as exc:
        out = {"ok": False, "S": [], "T": [], "steps": 0, "error": str(exc)}
    except MemoryError:
        out = {"ok": False, "S": [], "T": [], "steps": 0, "error": "memory limit"}
    except Exception as exc:
        out = {"ok": False, "S": [], "T": [], "steps": 0, "error": f"{type(exc).__name__}: {exc}"}
    pickle.dump(out, sys.stdout.buffer)


if __name__ == "__main__":
    main()
