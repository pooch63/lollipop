"""Oracle agrees with subset enumeration and with an independent biclique check."""

import random

from checker import is_valid, value
from graphs import BipartiteGraph
from projects.quasi.solvers import FEASIBLE, NONE, OPTIMAL, solve
from problem import cells, seed


def _bits_from_graph(G):
    u_ids = G.u_ids
    v_ids = G.v_ids
    v_index = {v: j for j, v in enumerate(v_ids)}
    adj = []
    for u in u_ids:
        mask = 0
        for v in G.neighbors_u(u):
            mask |= 1 << v_index[v]
        adj.append(mask)
    return adj, len(u_ids), len(v_ids)


def brute_value(G, p, q, theta):
    """Maximum |E(S,T)| over valid pairs, or None if none exist.

    Uses bitsets. Does not call the oracle. Validity is the same integer test
    as the checker, reimplemented here so a shared bug cannot hide.
    """
    adj, n_u, n_v = _bits_from_graph(G)
    # V -> U bitsets
    adj_v = [0] * n_v
    for u, mask in enumerate(adj):
        bit = mask
        while bit:
            j = (bit & -bit).bit_length() - 1
            adj_v[j] |= 1 << u
            bit ^= 1 << j

    best = None
    for smask in range(1 << n_u):
        s_size = smask.bit_count()
        if s_size < theta:
            continue
        for tmask in range(1 << n_v):
            t_size = tmask.bit_count()
            if t_size < theta:
                continue
            edges = 0
            ok = True
            bit = smask
            while bit:
                u = (bit & -bit).bit_length() - 1
                bit ^= 1 << u
                inter = (adj[u] & tmask).bit_count()
                edges += inter
                if q * inter < p * t_size:
                    ok = False
                    break
            if not ok:
                continue
            bit = tmask
            while bit:
                j = (bit & -bit).bit_length() - 1
                bit ^= 1 << j
                inter = (adj_v[j] & smask).bit_count()
                if q * inter < p * s_size:
                    ok = False
                    break
            if ok and (best is None or edges > best):
                best = edges
    return best


def max_edge_biclique(G, theta):
    """Independent exact check for gamma = 1: maximum |S|*|T| over bicliques.

    A pair is a biclique when every u in S is adjacent to every v in T.
    That is T contained in the intersection of N(u) for u in S. Edges equal
    |S|*|T| only in that case, so the maximum takes the full intersection.
    """
    adj, n_u, n_v = _bits_from_graph(G)
    full_v = (1 << n_v) - 1
    best = None
    for smask in range(1 << n_u):
        s_size = smask.bit_count()
        if s_size < theta:
            continue
        common = full_v
        bit = smask
        while bit:
            u = (bit & -bit).bit_length() - 1
            bit ^= 1 << u
            common &= adj[u]
        t_size = common.bit_count()
        if t_size < theta:
            continue
        edges = s_size * t_size
        if best is None or edges > best:
            best = edges
    return best


def _random_graph(rng, n_cap=8):
    n_u = rng.randint(1, n_cap)
    n_v = rng.randint(1, n_cap)
    # Density varies so both sparse and dense graphs show up.
    density = rng.choice([0.2, 0.5, 0.8])
    edges = []
    for u in range(n_u):
        for j in range(n_v):
            if rng.random() < density:
                edges.append((u, n_u + j))
    return BipartiteGraph.from_edges(edges, range(n_u), range(n_u, n_u + n_v))


def test_brute_matches_oracle_on_random_graphs():
    rng = random.Random(seed())
    graphs = [_random_graph(rng) for _ in range(200)]
    assert len(graphs) >= 200
    mismatches = 0
    for G in graphs:
        for p, q, theta in cells():
            S, T, val, status, _work = solve(G, p, q, theta, work_limit=5.0)
            brute = brute_value(G, p, q, theta)
            if brute is None:
                assert status == NONE, (G.m, p, q, theta, status, val)
                assert val == 0
            else:
                assert status == OPTIMAL, (status, val, brute, p, q, theta)
                assert val == brute
                assert is_valid(G, S, T, p, q, theta)
                assert value(G, S, T) == val
            if status in (OPTIMAL, FEASIBLE):
                assert is_valid(G, S, T, p, q, theta)
                assert value(G, S, T) == val
            else:
                mismatches += 0
    # Touch mismatches so a future edit cannot leave the name unused.
    assert mismatches == 0


def test_gamma_one_matches_independent_biclique():
    rng = random.Random(seed())
    for _ in range(40):
        G = _random_graph(rng, n_cap=7)
        for theta in (2, 3, 4, 5):
            biclique = max_edge_biclique(G, theta)
            S, T, val, status, _work = solve(G, 1, 1, theta, work_limit=5.0)
            if biclique is None:
                assert status == NONE
            else:
                assert status == OPTIMAL
                assert val == biclique
                # The independent check does not call is_valid; the returned
                # pair still has to be a genuine biclique.
                assert is_valid(G, S, T, 1, 1, theta)


def test_hand_quasi_example():
    # Two U, three V. u0 misses v4, u1 misses nothing of {2,3} and misses v4.
    # Full sets are a 1/2-quasi-biclique (see checker tests) with 5 edges? 
    # edges below have 4 edges inside [0,1]x[2,3] plus nothing to 4.
    edges = [(0, 2), (0, 3), (1, 2), (1, 3)]
    G = BipartiteGraph.from_edges(edges, [0, 1], [2, 3, 4])
    S, T, val, status, _work = solve(G, 1, 1, 2, work_limit=2.0)
    assert status == OPTIMAL
    assert val == 4
    assert set(S) == {0, 1}
    assert set(T) == {2, 3}
