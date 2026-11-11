"""Order, density, and neighborhoods out to 3 hops.

The graph is the bipartite object in src/graphs.py: neighbors_u from a U
vertex, neighbors_v from a V vertex. Hops alternate sides.
"""

from __future__ import annotations


def order(G) -> int:
    return int(G.n_u) + int(G.n_v)


def density(G) -> float:
    """Simple-edge density m / (|U| * |V|). Zero when either side is empty."""
    n_u = int(G.n_u)
    n_v = int(G.n_v)
    if n_u == 0 or n_v == 0:
        return 0.0
    return G.m / (n_u * n_v)


def hop_ball(G, vertex: int, side: str, hops: int) -> list[int]:
    """Vertices within `hops` of `vertex`, not counting `vertex` itself.

    `side` is "U" or "V". `hops` is 1, 2, or 3.
    """
    if hops not in (1, 2, 3):
        raise ValueError("hops must be 1, 2, or 3")
    side = str(side).upper()
    if side not in ("U", "V"):
        raise ValueError('side must be "U" or "V"')
    frontier = {int(vertex)}
    seen = set(frontier)
    current = side
    for _ in range(hops):
        nxt: set[int] = set()
        for node in frontier:
            if current == "U":
                nxt.update(G.neighbors_u(node))
            else:
                nxt.update(G.neighbors_v(node))
        current = "V" if current == "U" else "U"
        frontier = nxt - seen
        seen |= nxt
    seen.discard(int(vertex))
    return sorted(seen)


def hop_rank(G, side: str, hops: int) -> list[tuple[int, int]]:
    """`(ball size, id)` for every vertex on `side`. Largest ball first.

    Ties break toward the smaller id.
    """
    side = str(side).upper()
    if side == "U":
        ids = G.u_ids
    elif side == "V":
        ids = G.v_ids
    else:
        raise ValueError('side must be "U" or "V"')
    scored = [(len(hop_ball(G, i, side, hops)), int(i)) for i in ids]
    scored.sort(key=lambda row: (-row[0], row[1]))
    return scored
