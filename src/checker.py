"""Single source of truth for gamma-quasi-biclique validity.

gamma = p/q with p, q integers. The membership test is integer-only:
    q * |N(u) intersect T| >= p * |T|   for every u in S
    q * |N(v) intersect S| >= p * |S|   for every v in T
and |S| >= theta, |T| >= theta.
"""

from __future__ import annotations


def _as_int(name: str, value) -> int:
    # bool is a subclass of int; reject it so True/False cannot sneak in.
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    return value


def is_valid(G, S, T, p, q, theta) -> bool:
    p = _as_int("p", p)
    q = _as_int("q", q)
    theta = _as_int("theta", theta)
    if q <= 0 or p < 0 or theta < 0:
        raise ValueError("require p >= 0, q > 0, theta >= 0")

    s_set = set(S)
    t_set = set(T)
    if len(s_set) < theta or len(t_set) < theta:
        return False

    t_size = len(t_set)
    s_size = len(s_set)
    need_u = p * t_size
    need_v = p * s_size

    for u in s_set:
        inter = 0
        for v in G.neighbors_u(u):
            if v in t_set:
                inter += 1
        if q * inter < need_u:
            return False

    for v in t_set:
        inter = 0
        for u in G.neighbors_v(v):
            if u in s_set:
                inter += 1
        if q * inter < need_v:
            return False
    return True


def value(G, S, T) -> int:
    """Number of edges with one end in S and the other in T."""
    t_set = set(T)
    total = 0
    seen = set()
    for u in S:
        if u in seen:
            continue
        seen.add(u)
        for v in G.neighbors_u(u):
            if v in t_set:
                total += 1
    return total
