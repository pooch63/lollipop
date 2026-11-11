"""Subprocess entry point for one candidate program.

The parent launches this with `unshare -n` when that works. Before the
candidate runs we set RLIMIT_AS and RLIMIT_CPU, replace the socket type, and
install an audit hook that rejects open/socket/subprocess. Nothing here is
allowed to touch the network.
"""

from __future__ import annotations

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


def main() -> None:
    from graphs import BipartiteGraph
    from dsl.errors import ProgramError
    from dsl.runtime import execute

    payload = pickle.load(sys.stdin.buffer)
    mem = int(payload["memory_bytes"])
    cpu = int(payload["cpu_seconds"])
    # Virtual-memory cap. Set after imports so the interpreter can start,
    # and before the candidate runs.
    if mem > 0:
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    if cpu > 0:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    _lock_down()
    G = BipartiteGraph.from_edges(payload["edges"], payload["u"], payload["v"], name=payload.get("name"))
    try:
        keep_u, keep_v, cost = execute(
            payload["source"], G,
            payload["p"], payload["q"], payload["theta"], payload["tier"],
            check_lint=not payload.get("skip_lint", False),
        )
        out = {"ok": True, "keep_u": keep_u, "keep_v": keep_v, "cost": cost, "error": None}
    except ProgramError as exc:
        out = {"ok": False, "keep_u": None, "keep_v": None, "cost": 0, "error": str(exc)}
    except MemoryError:
        out = {"ok": False, "keep_u": None, "keep_v": None, "cost": 0, "error": "memory limit"}
    except Exception as exc:
        out = {"ok": False, "keep_u": None, "keep_v": None, "cost": 0, "error": f"{type(exc).__name__}: {exc}"}
    pickle.dump(out, sys.stdout.buffer)


if __name__ == "__main__":
    main()
