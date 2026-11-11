"""Reducers matched to an evolved program's edge-reduction on one cell.

The random control shuffles vertices with a fixed seed. The degree control
orders vertices by decreasing degree. Both keep the prefix whose induced
edge count is closest to reduction * m.
"""

from __future__ import annotations

import random

from problem import seed as global_seed


def degree_order(G) -> list[tuple[str, int]]:
    ranked = [("U", u, G.degree_u(u)) for u in G.u_ids]
    ranked += [("V", v, G.degree_v(v)) for v in G.v_ids]
    ranked.sort(key=lambda item: (-item[2], 0 if item[0] == "U" else 1, item[1]))
    return [(side, vid) for side, vid, _deg in ranked]


def random_order(G, rng: random.Random) -> list[tuple[str, int]]:
    order = [("U", u) for u in G.u_ids] + [("V", v) for v in G.v_ids]
    rng.shuffle(order)
    return order


def keep_prefix(G, order, reduction: float) -> tuple[list[int], list[int]]:
    """First prefix whose induced edge count is closest to reduction * m."""
    if G.m <= 0 or reduction <= 0:
        return [], []
    target = float(reduction) * G.m
    kept_u: list[int] = []
    kept_v: list[int] = []
    in_u: set[int] = set()
    in_v: set[int] = set()
    edges = 0
    best_err = abs(target)
    best = ([], [])
    for side, vid in order:
        if side == "U":
            edges += sum(1 for v in G.neighbors_u(vid) if v in in_v)
            in_u.add(vid)
            kept_u.append(vid)
        else:
            edges += sum(1 for u in G.neighbors_v(vid) if u in in_u)
            in_v.add(vid)
            kept_v.append(vid)
        err = abs(edges - target)
        if err < best_err:
            best_err = err
            best = (list(kept_u), list(kept_v))
            if err == 0:
                break
    return best


def degree_keep(G, reduction: float) -> tuple[list[int], list[int]]:
    return keep_prefix(G, degree_order(G), reduction)


def random_keep(G, reduction: float, rng: random.Random) -> tuple[list[int], list[int]]:
    return keep_prefix(G, random_order(G, rng), reduction)


def control_rng(program_hash: str, rung: str, p: int, q: int, theta: int) -> random.Random:
    # Python 3.14 rejects a tuple seed. The same fields go in as one string.
    material = f"{int(global_seed())}|{program_hash}|{rung}|{int(p)}|{int(q)}|{int(theta)}"
    return random.Random(material)
