"""Greedy one-vertex extension of a gamma-quasi-biclique.

Each step adds the vertex (either side) that keeps the pair valid and
increases |E(S, T)| the most. Ties break toward the smaller vertex id, and
toward U when the ids are equal. Stops when no such vertex exists.

The search is incremental: once the pair is valid, a candidate is accepted
exactly when the new vertex meets its test and every opposite vertex still
meets the stricter size. That matches `checker.is_valid` and avoids a full
rescan of both sides for every candidate.
"""

from __future__ import annotations

from checker import is_valid, value


def _hits(G, S, T):
    """hit_u[u] = |N(u) ∩ T|, hit_v[v] = |N(v) ∩ S|, for every vertex."""
    hit_u = {}
    for u in G.u_ids:
        hit_u[u] = sum(1 for v in G.neighbors_u(u) if v in T)
    hit_v = {}
    for v in G.v_ids:
        hit_v[v] = sum(1 for u in G.neighbors_v(v) if u in S)
    return hit_u, hit_v


def _candidates_u(G, S, T, p, q, theta, hit_u, hit_v):
    s_size = len(S)
    t_size = len(T)
    if s_size + 1 < theta or t_size < theta:
        return []
    need_v = p * (s_size + 1)
    critical = []
    for v in T:
        h = hit_v[v]
        if q * h >= need_v:
            continue
        # Even if the new u is adjacent, this v cannot reach the new bar.
        if q * (h + 1) < need_v:
            return []
        critical.append(v)
    need_u = p * t_size
    if critical:
        crit = sorted(critical, key=lambda v: (len(G.neighbors_v(v)), v))
        cands = set(G.neighbors_v(crit[0]))
        for v in crit[1:]:
            cands &= set(G.neighbors_v(v))
        out = []
        for u in cands:
            if u in S:
                continue
            if q * hit_u.get(u, 0) >= need_u:
                out.append(u)
        return out
    return [u for u in G.u_ids if u not in S and q * hit_u[u] >= need_u]


def _candidates_v(G, S, T, p, q, theta, hit_u, hit_v):
    s_size = len(S)
    t_size = len(T)
    if t_size + 1 < theta or s_size < theta:
        return []
    need_u = p * (t_size + 1)
    critical = []
    for u in S:
        h = hit_u[u]
        if q * h >= need_u:
            continue
        if q * (h + 1) < need_u:
            return []
        critical.append(u)
    need_v = p * s_size
    if critical:
        crit = sorted(critical, key=lambda u: (len(G.neighbors_u(u)), u))
        cands = set(G.neighbors_u(crit[0]))
        for u in crit[1:]:
            cands &= set(G.neighbors_u(u))
        out = []
        for v in cands:
            if v in T:
                continue
            if q * hit_v.get(v, 0) >= need_v:
                out.append(v)
        return out
    return [v for v in G.v_ids if v not in T and q * hit_v[v] >= need_v]


def _best_addition_slow(G, S, T, p, q, theta):
    """Full checker scan. Used only while the current pair is not yet valid."""
    base = value(G, S, T)
    best_key = None
    best = None
    for u in G.u_ids:
        if u in S:
            continue
        if not is_valid(G, S | {u}, T, p, q, theta):
            continue
        gain = value(G, S | {u}, T) - base
        key = (gain, -u, 0)
        if best_key is None or key > best_key:
            best_key = key
            best = ("U", u)
    for v in G.v_ids:
        if v in T:
            continue
        if not is_valid(G, S, T | {v}, p, q, theta):
            continue
        gain = value(G, S, T | {v}) - base
        key = (gain, -v, -1)
        if best_key is None or key > best_key:
            best_key = key
            best = ("V", v)
    return best


def _best_addition(G, S, T, p, q, theta, hit_u=None, hit_v=None):
    """Return ('U'|'V', vertex id) or None."""
    if hit_u is None or hit_v is None:
        hit_u, hit_v = _hits(G, S, T)
    best_key = None
    best = None
    for u in _candidates_u(G, S, T, p, q, theta, hit_u, hit_v):
        gain = hit_u[u]
        key = (gain, -u, 0)
        if best_key is None or key > best_key:
            best_key = key
            best = ("U", u)
    for v in _candidates_v(G, S, T, p, q, theta, hit_u, hit_v):
        gain = hit_v[v]
        key = (gain, -v, -1)
        if best_key is None or key > best_key:
            best_key = key
            best = ("V", v)
    return best


def _apply(G, S, T, hit_u, hit_v, side, vid):
    if side == "U":
        S.add(vid)
        for v in G.neighbors_u(vid):
            hit_v[v] = hit_v.get(v, 0) + 1
    else:
        T.add(vid)
        for u in G.neighbors_v(vid):
            hit_u[u] = hit_u.get(u, 0) + 1


def extend(G, S, T, p, q, theta):
    """Return (S', T') as sorted lists. Preserves validity when the input was valid."""
    S = set(S)
    T = set(T)
    started_valid = is_valid(G, S, T, p, q, theta)
    hit_u, hit_v = _hits(G, S, T)
    changed = False
    while True:
        if is_valid(G, S, T, p, q, theta):
            pick = _best_addition(G, S, T, p, q, theta, hit_u, hit_v)
        else:
            pick = _best_addition_slow(G, S, T, p, q, theta)
        if pick is None:
            break
        side, vid = pick
        _apply(G, S, T, hit_u, hit_v, side, vid)
        changed = True
        assert is_valid(G, S, T, p, q, theta)
    if started_valid or changed:
        assert is_valid(G, S, T, p, q, theta)
    return sorted(S), sorted(T)
