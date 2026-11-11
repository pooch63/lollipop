"""Planted quasi-bicliques pass the checker; the degree baseline flags easy ones."""

from checker import is_valid, value
from graphs import BipartiteGraph
from plant import degree_threshold_baseline, minimum_added_edges, plant


def test_minimum_edges_match_the_lower_bound_and_are_necessary():
    # No edges yet. gamma = 1, |S| = |T| = 2 needs the full K_{2,2} (4 edges).
    G = BipartiteGraph.from_edges([], [0, 1, 2], [3, 4, 5])
    extra = minimum_added_edges(G, [0, 1], [3, 4], 1, 1)
    assert len(extra) == 4
    planted = G.with_edges(extra)
    assert is_valid(planted, [0, 1], [3, 4], 1, 1, 2)
    for edge in extra:
        rest = [e for e in extra if e != edge]
        broken = G.with_edges(rest)
        assert not is_valid(broken, [0, 1], [3, 4], 1, 1, 2)


def test_half_density_uses_two_edges():
    # p/q = 1/2, each of 2+2 vertices needs one neighbor. A matching suffices.
    G = BipartiteGraph.from_edges([], [0, 1], [2, 3])
    extra = minimum_added_edges(G, [0, 1], [2, 3], 1, 2)
    assert len(extra) == 2
    assert is_valid(G.with_edges(extra), [0, 1], [2, 3], 1, 2, 2)


def test_complete_biclique_is_too_easy():
    edges = [(u, 4 + v) for u in range(4) for v in range(4)]
    G = BipartiteGraph.from_edges(edges, range(4), range(4, 8), name="K44")
    result = plant(G, 1, 1, 2)
    assert result is not None
    assert result["extra_edges"] == []
    assert result["too_easy"] is True
    assert result["baseline_value"] >= result["value"]
    assert is_valid(result["graph"], result["S"], result["T"], 1, 1, 2)


def test_baseline_finds_the_biclique_and_extend_keeps_it_valid():
    edges = [(u, 3 + v) for u in range(3) for v in range(3)]
    G = BipartiteGraph.from_edges(edges, range(3), range(3, 6))
    S, T = degree_threshold_baseline(G, 1, 1, 2)
    assert is_valid(G, S, T, 1, 1, 2)
    assert value(G, S, T) == 9


def test_heap_baseline_matches_a_full_scan():
    import random
    rng = random.Random(0)
    edges = [(u, 12 + v) for u in range(12) for v in range(12) if rng.random() < 0.35]
    G = BipartiteGraph.from_edges(edges, range(12), range(12, 24))
    got = degree_threshold_baseline(G, 7, 10, 2)
    # Independent scan of the same drop rule, on this small graph only.
    t = 2  # ceil(7*2/10) = 2
    S = {u for u in G.u_ids if G.degree_u(u) >= t}
    T = {v for v in G.v_ids if G.degree_v(v) >= t}
    from checker import is_valid
    from extend import extend
    while S and T and not is_valid(G, S, T, 7, 10, 2):
        if len(S) < 2 or len(T) < 2:
            S, T = set(), set()
            break
        pick = None
        pick_key = None
        for u in S:
            inter = sum(1 for v in G.neighbors_u(u) if v in T)
            deficit = 7 * len(T) - 10 * inter
            if deficit <= 0:
                continue
            key = (deficit, -G.degree_u(u), -u, 0)
            if pick_key is None or key > pick_key:
                pick_key, pick = key, ("U", u)
        for v in T:
            inter = sum(1 for u in G.neighbors_v(v) if u in S)
            deficit = 7 * len(S) - 10 * inter
            if deficit <= 0:
                continue
            key = (deficit, -G.degree_v(v), -v, -1)
            if pick_key is None or key > pick_key:
                pick_key, pick = key, ("V", v)
        if pick is None:
            break
        if pick[0] == "U":
            S.remove(pick[1])
        else:
            T.remove(pick[1])
    if S and T and is_valid(G, S, T, 7, 10, 2):
        expect = extend(G, S, T, 7, 10, 2)
    else:
        expect = ([], [])
    assert got == expect


def test_sparse_matching_is_not_a_free_biclique():
    # Degree 1 everywhere. theta = 2 requires deg > 2 to plant, so this is unplantable.
    edges = [(0, 2), (1, 3)]
    G = BipartiteGraph.from_edges(edges, range(2), range(2, 4))
    assert plant(G, 1, 1, 2) is None
    assert degree_threshold_baseline(G, 1, 1, 2) == ([], [])
