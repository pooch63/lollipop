"""Run one search program against a read-only graph view.

`valid(S, T)` and `edges(S, T)` are the checker, bound to this cell.
`rng` is a Random seeded from config. The view counts every graph query
and stops the program past the step budget.
"""

from __future__ import annotations

import random

from checker import is_valid, value
from dsl.errors import ProgramError
from projects.quasi.heuristics.lint import lint
from problem import seed as config_seed

# A dense local search on a dev rung fits under this. A scan that ignores
# the graph size does not.
_STEP_FLOOR = 8_000_000


def step_limit(n_u: int, n_v: int, m: int) -> int:
    base = n_u + n_v + m
    return max(_STEP_FLOOR, 64 * base * max(n_u, n_v, 1))


class View:
    """The only graph object the candidate receives."""

    def __init__(self, G, limit: int):
        self._G = G
        self._limit = int(limit)
        self.steps = 0

    def _tick(self) -> None:
        self.steps += 1
        if self.steps > self._limit:
            raise ProgramError("step limit")

    @property
    def n_u(self) -> int:
        self._tick()
        return self._G.n_u

    @property
    def n_v(self) -> int:
        self._tick()
        return self._G.n_v

    @property
    def m(self) -> int:
        self._tick()
        return self._G.m

    @property
    def u_ids(self) -> list[int]:
        self._tick()
        return list(self._G.u_ids)

    @property
    def v_ids(self) -> list[int]:
        self._tick()
        return list(self._G.v_ids)

    def neighbors_u(self, u: int):
        self._tick()
        return self._G.neighbors_u(_as_id(u))

    def neighbors_v(self, v: int):
        self._tick()
        return self._G.neighbors_v(_as_id(v))

    def degree_u(self, u: int) -> int:
        self._tick()
        return self._G.degree_u(_as_id(u))

    def degree_v(self, v: int) -> int:
        self._tick()
        return self._G.degree_v(_as_id(v))

    def has_edge(self, u: int, v: int) -> bool:
        self._tick()
        return self._G.has_edge(_as_id(u), _as_id(v))


def _as_id(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProgramError("vertex id must be an int")
    return value


SAFE_BUILTINS = {
    "abs": abs,
    "min": min,
    "max": max,
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "sorted": sorted,
    "reversed": reversed,
    "sum": sum,
    "all": all,
    "any": any,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "int": int,
    "float": float,
    "bool": bool,
    "round": round,
    "pow": pow,
    "divmod": divmod,
    "map": map,
    "filter": filter,
    "isinstance": isinstance,
    "hash": hash,
    "repr": repr,
    "True": True,
    "False": False,
    "None": None,
}


def execute(source: str, G, p: int, q: int, theta: int, *, check_lint: bool = True, step_limit_value: int | None = None, rng_seed: int | None = None):
    """Return (S, T, steps). S and T are sorted id lists. Raises ProgramError."""
    if check_lint:
        lint(source)
    limit = step_limit(G.n_u, G.n_v, G.m) if step_limit_value is None else int(step_limit_value)
    view = View(G, limit)
    rng = random.Random(config_seed() if rng_seed is None else int(rng_seed))

    def valid(S, T) -> bool:
        return is_valid(view, S, T, int(p), int(q), int(theta))

    def edges(S, T) -> int:
        return value(view, S, T)

    env = {
        "__builtins__": SAFE_BUILTINS,
        "valid": valid,
        "edges": edges,
        "rng": rng,
    }
    try:
        exec(compile(source, "<search>", "exec"), env, env)
    except ProgramError:
        raise
    except Exception as exc:
        raise ProgramError(f"{type(exc).__name__}: {exc}") from exc
    fn = env.get("search")
    if not callable(fn):
        raise ProgramError("search is not defined")
    try:
        result = fn(view, int(p), int(q), int(theta))
    except ProgramError:
        raise
    except Exception as exc:
        raise ProgramError(f"{type(exc).__name__}: {exc}") from exc
    if not isinstance(result, tuple) or len(result) != 2:
        raise ProgramError("search must return (S, T)")
    return _as_ids(result[0], "S"), _as_ids(result[1], "T"), view.steps


def _as_ids(seq, name: str) -> list[int]:
    if isinstance(seq, (str, bytes)) or not isinstance(seq, (list, tuple, set)):
        raise ProgramError(f"{name} must be a list of vertex ids")
    out = []
    for item in seq:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ProgramError(f"{name} contains a non-int")
        out.append(int(item))
    return sorted(set(out))
