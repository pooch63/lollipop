"""Primitives, abstract costs, and in-process execution of a lint-clean program.

Costs are deterministic integers charged inside each primitive. They are not
wall-clock times. W = sum of squared degrees. See DECISIONS.md for id layout
and for floor(log2).
"""

from __future__ import annotations

import math

from dsl.errors import KillCapExceeded, ProgramError
from dsl.lint import lint

# Eight fixed odd multipliers. i < 8.
_MINHASH_SEEDS = (
    0x9E3779B1, 0x85EBCA77, 0xC2B2AE3D, 0x27D4EB2F,
    0x165667B1, 0xD3A2646C, 0xFD7046C5, 0xB55A4F09,
)


def floor_log2(n: int) -> int:
    if n <= 1:
        return 0
    return n.bit_length() - 1


def nlog2n(n: int) -> int:
    if n <= 1:
        return 0
    return n * floor_log2(n)


def f_tier(G, tier: str) -> int:
    if tier == "L":
        return G.n_u + G.n_v + G.m
    if tier == "N":
        if G.m <= 1:
            return 0
        return G.m * floor_log2(G.m)
    if tier == "Q":
        total = 0
        for u in G.u_ids:
            d = G.degree_u(u)
            total += d * d
        for v in G.v_ids:
            d = G.degree_v(v)
            total += d * d
        return total
    raise ValueError(f"unknown tier {tier}")


def kill_cap(G, tier: str) -> int:
    return 64 * f_tier(G, tier)


class Counter:
    def __init__(self, cap: int):
        self.cost = 0
        self.cap = cap

    def charge(self, n: int) -> None:
        self.cost += int(n)
        if self.cost > self.cap:
            raise KillCapExceeded(f"cost {self.cost} exceeded kill cap {self.cap}")


class View:
    """Bipartite graph with disjoint DSL ids.

    U ids are 0 .. n_u-1. V ids are n_u .. n_u+n_v-1. Arrays returned by
    map('V', ...) are indexed by the local V index, id - n_u.
    """

    def __init__(self, G, counter: Counter):
        self.G = G
        self.counter = counter
        self.n_u = G.n_u
        self.n_v = G.n_v
        self.m = G.m
        v_index = {v: i for i, v in enumerate(G.v_ids)}
        u_index = {u: i for i, u in enumerate(G.u_ids)}
        self.nbr_u = [tuple(v_index[v] for v in G.neighbors_u(u)) for u in G.u_ids]
        self.nbr_v = [tuple(u_index[u] for u in G.neighbors_v(v)) for v in G.v_ids]
        self.deg_u = [len(ns) for ns in self.nbr_u]
        self.deg_v = [len(ns) for ns in self.nbr_v]

    def _loc(self, x: int):
        x = int(x)
        if 0 <= x < self.n_u:
            return "U", x
        v = x - self.n_u
        if 0 <= v < self.n_v:
            return "V", v
        raise ProgramError(f"vertex id {x} is out of range")

    def degree(self, x: int) -> int:
        side, i = self._loc(x)
        return self.deg_u[i] if side == "U" else self.deg_v[i]

    def neighbor_locals(self, x: int):
        side, i = self._loc(x)
        if side == "U":
            return self.nbr_u[i]
        return self.nbr_v[i]


def _threshold_int(x) -> int:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ProgramError(f"threshold must be a number, got {type(x).__name__}")
    if isinstance(x, int):
        return x
    return int(math.ceil(x - 1e-12))


def make_primitives(view: View):
    """Return the name -> function map closed over `view`."""
    c = view.counter

    def n_U():
        c.charge(1)
        return view.n_u

    def n_V():
        c.charge(1)
        return view.n_v

    def m():
        c.charge(1)
        return view.m

    def deg(x):
        c.charge(1)
        return view.degree(x)

    def nbr_sum(x, arr):
        nbrs = view.neighbor_locals(x)
        c.charge(len(nbrs))
        total = 0
        for j in nbrs:
            total += arr[j]
        return total

    def nbr_count_if(x, mask):
        nbrs = view.neighbor_locals(x)
        c.charge(len(nbrs))
        return sum(1 for j in nbrs if mask[j])

    def minhash(x, i):
        i = int(i)
        if i < 0 or i >= 8:
            raise ProgramError("minhash index i must satisfy 0 <= i < 8")
        nbrs = view.neighbor_locals(x)
        c.charge(len(nbrs))
        seed = _MINHASH_SEEDS[i]
        salt = _MINHASH_SEEDS[(i + 3) % 8]
        best = None
        for y in nbrs:
            h = (y * seed + salt) & 0xFFFFFFFF
            if best is None or h < best:
                best = h
        return 0xFFFFFFFF if best is None else best

    def map(side, fn):
        if side == "U":
            ids = range(view.n_u)
        elif side == "V":
            ids = range(view.n_u, view.n_u + view.n_v)
        else:
            raise ProgramError("map side must be 'U' or 'V'")
        out = [fn(x) for x in ids]
        c.charge(len(out))
        return out

    def peel(a, b):
        c.charge(view.n_u + view.n_v + view.m)
        a = _threshold_int(a)
        b = _threshold_int(b)
        alive_u = [True] * view.n_u
        alive_v = [True] * view.n_v
        deg_u = list(view.deg_u)
        deg_v = list(view.deg_v)
        changed = True
        while changed:
            changed = False
            for u in range(view.n_u):
                if alive_u[u] and deg_u[u] < a:
                    alive_u[u] = False
                    changed = True
                    for v in view.nbr_u[u]:
                        if alive_v[v]:
                            deg_v[v] -= 1
            for v in range(view.n_v):
                if alive_v[v] and deg_v[v] < b:
                    alive_v[v] = False
                    changed = True
                    for u in view.nbr_v[v]:
                        if alive_u[u]:
                            deg_u[u] -= 1
        return alive_u, alive_v

    def threshold(arr, t):
        c.charge(len(arr))
        return [v >= t for v in arr]

    def sort_desc(arr):
        n = len(arr)
        c.charge(nlog2n(n))
        return sorted(range(n), key=lambda i: (-arr[i], i))

    def top_q(arr, q):
        n = len(arr)
        c.charge(nlog2n(n))
        if q <= 0 or n == 0:
            return [False] * n
        if q <= 1:
            k = int(math.ceil(q * n - 1e-12))
        else:
            k = int(q)
        k = max(0, min(n, k))
        order = sorted(range(n), key=lambda i: (-arr[i], i))
        mask = [False] * n
        for i in order[:k]:
            mask[i] = True
        return mask

    def rank(arr):
        n = len(arr)
        c.charge(nlog2n(n))
        order = sorted(range(n), key=lambda i: (-arr[i], i))
        ranks = [0] * n
        for r, i in enumerate(order):
            ranks[i] = r
        return ranks

    def _same_side(x, y):
        sx, ix = view._loc(x)
        sy, iy = view._loc(y)
        if sx != sy:
            raise ProgramError("common/jaccard require two vertices on the same side")
        return sx, ix, iy

    def common(x, y):
        _side, ix, iy = _same_side(x, y)
        nbrs_x = view.nbr_u[ix] if _side == "U" else view.nbr_v[ix]
        nbrs_y = view.nbr_u[iy] if _side == "U" else view.nbr_v[iy]
        c.charge(len(nbrs_x) + len(nbrs_y))
        return len(set(nbrs_x) & set(nbrs_y))

    def jaccard(x, y):
        _side, ix, iy = _same_side(x, y)
        nbrs_x = view.nbr_u[ix] if _side == "U" else view.nbr_v[ix]
        nbrs_y = view.nbr_u[iy] if _side == "U" else view.nbr_v[iy]
        c.charge(len(nbrs_x) + len(nbrs_y))
        a = set(nbrs_x)
        b = set(nbrs_y)
        union = len(a | b)
        if union == 0:
            return 0.0
        return len(a & b) / union

    def two_hop_count(x):
        side, i = view._loc(x)
        if side == "U":
            nbrs = view.nbr_u[i]
            total = sum(view.deg_v[j] for j in nbrs)
        else:
            nbrs = view.nbr_v[i]
            total = sum(view.deg_u[j] for j in nbrs)
        c.charge(total)
        return total

    return {
        "n_U": n_U, "n_V": n_V, "m": m, "deg": deg,
        "nbr_sum": nbr_sum, "nbr_count_if": nbr_count_if, "minhash": minhash,
        "map": map, "peel": peel, "threshold": threshold,
        "sort_desc": sort_desc, "top_q": top_q, "rank": rank,
        "common": common, "jaccard": jaccard, "two_hop_count": two_hop_count,
    }


def ceil(x):
    if isinstance(x, bool):
        raise ProgramError("ceil got a bool")
    if isinstance(x, int):
        return x
    return int(math.ceil(float(x)))


def floor(x):
    if isinstance(x, bool):
        raise ProgramError("floor got a bool")
    if isinstance(x, int):
        return x
    return int(math.floor(float(x)))


def execute(source: str, G, p: int, q: int, theta: int, tier: str, *, check_lint: bool = True):
    """Run reduce(G) in this process. Returns (keep_u, keep_v, cost).

    keep_* are boolean lists in side-local order. Raises ProgramError on
    a lint failure, a kill-cap hit, or a bad return value.
    """
    if check_lint:
        lint(source, tier)
    counter = Counter(kill_cap(G, tier))
    view = View(G, counter)
    prims = make_primitives(view)
    env = {
        "__builtins__": {},
        "min": min, "max": max, "abs": abs, "ceil": ceil, "floor": floor,
        "p": int(p), "q": int(q), "theta": int(theta),
    }
    env.update(prims)
    try:
        exec(source, env, env)
        fn = env.get("reduce")
        if not callable(fn):
            raise ProgramError("reduce is missing")
        result = fn(None)
    except KillCapExceeded:
        raise
    except ProgramError:
        raise
    except Exception as exc:
        raise ProgramError(f"runtime error: {type(exc).__name__}: {exc}") from exc
    keep_u, keep_v = _as_masks(result, view.n_u, view.n_v)
    return keep_u, keep_v, counter.cost


def _as_masks(result, n_u: int, n_v: int):
    if not isinstance(result, tuple) or len(result) != 2:
        raise ProgramError("reduce must return (keepU, keepV)")
    keep_u, keep_v = result
    if len(keep_u) != n_u or len(keep_v) != n_v:
        raise ProgramError(f"mask lengths {len(keep_u)}, {len(keep_v)} != {n_u}, {n_v}")
    return [bool(v) for v in keep_u], [bool(v) for v in keep_v]


def masks_to_ids(G, keep_u, keep_v):
    u_ids = [u for u, bit in zip(G.u_ids, keep_u) if bit]
    v_ids = [v for v, bit in zip(G.v_ids, keep_v) if bit]
    return u_ids, v_ids
