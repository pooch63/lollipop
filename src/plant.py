"""Plant a known gamma-quasi-biclique and reject instances a degree baseline solves.

See DECISIONS.md. S* and T* are the `theta` highest-degree vertices on each
side among those whose degree already exceeds the opposite side's size.
The added edges are a minimum-cardinality set that makes (S*, T*) valid.
"""

from __future__ import annotations

from checker import is_valid, value
from extend import extend
from problem import ceil_div, config


def choose_planted_sets(G, theta):
    """Return (S, T) lists, or None if there are not enough high-degree vertices."""
    a = b = int(theta)
    cand_u = [u for u in G.u_ids if G.degree_u(u) > b]
    cand_v = [v for v in G.v_ids if G.degree_v(v) > a]
    if len(cand_u) < a or len(cand_v) < b:
        return None
    cand_u.sort(key=lambda u: (-G.degree_u(u), u))
    cand_v.sort(key=lambda v: (-G.degree_v(v), v))
    return cand_u[:a], cand_v[:b]


def minimum_added_edges(G, S, T, p, q):
    """Fewest missing edges inside S x T that make the pair pass the checker.

    max(U deficit, V deficit) is a lower bound. Existing edges can block a
    pairing that meets the bound, so the count is the optimum of a tiny
    CP-SAT model over the missing pairs. |S| and |T| are theta (<= 5).
    """
    from ortools.sat.python import cp_model

    S = list(S)
    T = list(T)
    t_set = set(T)
    s_set = set(S)
    req_u = ceil_div(p * len(T), q)
    req_v = ceil_div(p * len(S), q)
    if req_u > len(T) or req_v > len(S):
        raise ValueError("degree requirement exceeds the opposite side")
    have_u = {u: sum(1 for v in G.neighbors_u(u) if v in t_set) for u in S}
    have_v = {v: sum(1 for u in G.neighbors_v(v) if u in s_set) for v in T}
    present = {(u, v) for u in S for v in G.neighbors_u(u) if v in t_set}
    if all(have_u[u] >= req_u for u in S) and all(have_v[v] >= req_v for v in T):
        return []
    model = cp_model.CpModel()
    chosen = {}
    for u in S:
        for v in T:
            if (u, v) in present:
                continue
            chosen[(u, v)] = model.new_bool_var(f"e_{u}_{v}")
    for u in S:
        model.add(have_u[u] + sum(chosen[(u, v)] for v in T if (u, v) in chosen) >= req_u)
    for v in T:
        model.add(have_v[v] + sum(chosen[(u, v)] for u in S if (u, v) in chosen) >= req_v)
    model.minimize(sum(chosen.values()))
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = int(config()["seed"])
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("no edge set makes the planted pair valid")
    extra = sorted((u, v) for (u, v), var in chosen.items() if solver.value(var))
    return extra


def degree_threshold_baseline(G, p, q, theta):
    """Keep deg >= ceil(p*theta/q), drop the worst deficit, then extend.

    Returns (S, T) sorted lists. Empty when no valid pair is reached.

    Deficit on a side is an affine function of the hit count, so the worst
    vertex is the one with the smallest hit. A heap finds it in log time.
    Stale heap entries (from before a neighbor was dropped) are skipped.
    """
    import heapq

    t = ceil_div(int(p) * int(theta), int(q))
    S = {u for u in G.u_ids if G.degree_u(u) >= t}
    T = {v for v in G.v_ids if G.degree_v(v) >= t}
    hit_u = {u: 0 for u in S}
    hit_v = {v: 0 for v in T}
    for u in S:
        for v in G.neighbors_u(u):
            if v in T:
                hit_u[u] += 1
                hit_v[v] += 1
    # (hit, degree, id): smallest hit, then smaller degree, then smaller id.
    heap_u = [(hit_u[u], G.degree_u(u), u) for u in S]
    heap_v = [(hit_v[v], G.degree_v(v), v) for v in T]
    heapq.heapify(heap_u)
    heapq.heapify(heap_v)

    def peek(heap, alive, hits):
        while heap:
            h, d, vid = heap[0]
            if vid not in alive or hits[vid] != h:
                heapq.heappop(heap)
                continue
            return h, d, vid
        return None

    def worst():
        wu = peek(heap_u, S, hit_u)
        wv = peek(heap_v, T, hit_v)
        best = None
        best_key = None
        if wu is not None and q * wu[0] < p * len(T):
            deficit = p * len(T) - q * wu[0]
            key = (deficit, -wu[1], -wu[2], 0)
            best_key, best = key, ("U", wu[2])
        if wv is not None and q * wv[0] < p * len(S):
            deficit = p * len(S) - q * wv[0]
            key = (deficit, -wv[1], -wv[2], -1)
            if best_key is None or key > best_key:
                best = ("V", wv[2])
        return best

    while S and T:
        if len(S) < theta or len(T) < theta:
            return [], []
        drop = worst()
        if drop is None:
            break
        side, vid = drop
        if side == "U":
            S.remove(vid)
            for v in G.neighbors_u(vid):
                if v in T:
                    hit_v[v] -= 1
                    heapq.heappush(heap_v, (hit_v[v], G.degree_v(v), v))
        else:
            T.remove(vid)
            for u in G.neighbors_v(vid):
                if u in S:
                    hit_u[u] -= 1
                    heapq.heappush(heap_u, (hit_u[u], G.degree_u(u), u))
    if len(S) < theta or len(T) < theta:
        return [], []
    if not is_valid(G, S, T, p, q, theta):
        return [], []
    return extend(G, S, T, p, q, theta)


def plant(G, p, q, theta):
    """Return a result dict, or None when the degree pool is too small.

    The dict contains S, T, extra edges, planted value, baseline value, and
    too_easy. The planted graph is `G.with_edges(extra)`.
    """
    chosen = choose_planted_sets(G, theta)
    if chosen is None:
        return None
    S, T = chosen
    extra = minimum_added_edges(G, S, T, int(p), int(q))
    planted = G.with_edges(extra) if extra else G
    if not is_valid(planted, S, T, p, q, theta):
        raise RuntimeError("planted pair failed the checker")
    planted_value = value(planted, S, T)
    base_s, base_t = degree_threshold_baseline(planted, p, q, theta)
    base_value = value(planted, base_s, base_t) if base_s and base_t else 0
    ratio = 1.0 if planted_value <= 0 else base_value / planted_value
    too_easy = ratio >= float(config()["too_easy_rho"])
    return {
        "S": list(S),
        "T": list(T),
        "extra_edges": extra,
        "value": planted_value,
        "baseline_S": list(base_s),
        "baseline_T": list(base_t),
        "baseline_value": base_value,
        "too_easy": too_easy,
        "graph": planted,
    }
