"""Subprocess entry for one candidate. No network and no imports in the candidate."""

from __future__ import annotations

import os
import pickle
import resource
import sys


_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "reversed": reversed,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "True": True,
    "False": False,
    "None": None,
}


def _blocked_import(name, *args, **kwargs):
    raise RuntimeError(f"import blocked: {name}")


def _scrub_env() -> None:
    for key in list(os.environ):
        upper = key.upper()
        if any(mark in upper for mark in ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD")):
            os.environ.pop(key, None)


def _lock_down() -> None:
    import socket

    class _BlockedSocket:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("network disabled")

    socket.socket = _BlockedSocket
    socket.create_connection = _BlockedSocket
    socket.socketpair = _BlockedSocket

    def _audit(event, args):
        if event in {"socket.connect", "socket.bind", "socket.send", "socket.sendto", "subprocess.Popen"} or event.startswith("socket."):
            raise RuntimeError(f"sandbox blocked {event}")

    sys.addaudithook(_audit)


def main() -> None:
    from graphs import BipartiteGraph

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
    namespace = {"__builtins__": {**_BUILTINS, "__import__": _blocked_import}, "__name__": "candidate"}
    try:
        exec(payload["source"], namespace, namespace)
        fn = namespace[payload["entry"]]
        result = fn(G, payload["params"])
        out = {"ok": True, "result": result, "error": None}
    except MemoryError:
        out = {"ok": False, "result": None, "error": "memory limit"}
    except Exception as exc:
        out = {"ok": False, "result": None, "error": f"{type(exc).__name__}: {exc}"}
    pickle.dump(out, sys.stdout.buffer)


if __name__ == "__main__":
    main()
