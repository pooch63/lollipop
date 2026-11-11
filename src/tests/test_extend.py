"""Greedy extension keeps validity and breaks ties by vertex id."""

from checker import is_valid, value
from extend import _best_addition, extend
from graphs import BipartiteGraph


def test_grows_biclique_to_completion():
    edges = [(u, 3 + v) for u in range(3) for v in range(3)]
    G = BipartiteGraph.from_edges(edges, range(3), range(3, 6))
    S, T = extend(G, [0, 1], [3, 4], 1, 1, 2)
    assert S == [0, 1, 2]
    assert T == [3, 4, 5]
    assert value(G, S, T) == 9
    assert is_valid(G, S, T, 1, 1, 2)


def test_does_not_add_vertex_that_breaks_biclique():
    # K_{2,2} on {0,1}x{3,4}, plus a pendant edge (2,3).
    edges = [(0, 3), (0, 4), (1, 3), (1, 4), (2, 3)]
    G = BipartiteGraph.from_edges(edges, range(3), range(3, 6))
    S, T = extend(G, [0, 1], [3, 4], 1, 1, 2)
    assert S == [0, 1]
    assert T == [3, 4]


def test_prefers_higher_gain_even_with_larger_id():
    # From S={0,1}, T={4,5}: u=3 touches both V (gain 2), u=2 touches one (invalid).
    edges = [(0, 4), (0, 5), (1, 4), (1, 5), (3, 4), (3, 5), (2, 4)]
    G = BipartiteGraph.from_edges(edges, range(4), range(4, 6))
    assert _best_addition(G, {0, 1}, {4, 5}, 1, 1, 2) == ("U", 3)


def test_tie_smaller_id():
    edges = [(0, 4), (0, 5), (1, 4), (1, 5), (2, 4), (2, 5), (3, 4), (3, 5)]
    G = BipartiteGraph.from_edges(edges, range(4), range(4, 6))
    # Both u=2 and u=3 have gain 2. Smaller id wins.
    assert _best_addition(G, {0, 1}, {4, 5}, 1, 1, 2) == ("U", 2)


def test_tie_same_id_prefers_u():
    # U id 5 and V id 5 both have gain 2. U is chosen, and that choice blocks V.
    # Existing biclique {0,1} x {2,3}. U5 covers {2,3}. V5 covers {0,1}. No edge (5,5).
    edges = [
        (0, 2), (0, 3), (1, 2), (1, 3),
        (5, 2), (5, 3),
        (0, 5), (1, 5),
    ]
    G = BipartiteGraph.from_edges(edges, [0, 1, 5], [2, 3, 5])
    assert _best_addition(G, {0, 1}, {2, 3}, 1, 1, 2) == ("U", 5)
    S, T = extend(G, [0, 1], [2, 3], 1, 1, 2)
    assert 5 in S and 5 not in T


def test_invalid_high_gain_loses_to_valid_low_gain():
    # gamma = 1/2, |T|=5, |S|=4. v0 is tight (only u0,u1). u=10 touches the four
    # slack vertices (gain 4) but misses v0, so v0 falls short after |S| grows.
    # u=11 touches v0 and two slack vertices (gain 3) and stays valid.
    u_ids = [0, 1, 2, 3, 10, 11]
    v_ids = [0, 1, 2, 3, 4]
    edges = []
    for u in (0, 1):
        for v in v_ids:
            edges.append((u, v))
    for u in (2, 3):
        for v in (1, 2, 3, 4):
            edges.append((u, v))
    for v in (1, 2, 3, 4):
        edges.append((10, v))
    for v in (0, 1, 2):
        edges.append((11, v))
    G = BipartiteGraph.from_edges(edges, u_ids, v_ids)
    S0, T0 = {0, 1, 2, 3}, {0, 1, 2, 3, 4}
    assert is_valid(G, S0, T0, 1, 2, 2)
    assert _best_addition(G, S0, T0, 1, 2, 2) == ("U", 11)


def test_fast_matches_slow_and_grows_from_undersized():
    import random
    from extend import _best_addition_slow
    edges = [(u, 4 + v) for u in range(4) for v in range(4)]
    G = BipartiteGraph.from_edges(edges, range(4), range(4, 8))
    # |S|=1 is under theta, but one addition completes a biclique.
    S, T = extend(G, [0], [4, 5], 1, 1, 2)
    assert is_valid(G, S, T, 1, 1, 2)
    assert S == [0, 1, 2, 3]
    assert T == [4, 5, 6, 7]
    rng = random.Random(0)
    checked = 0
    for _ in range(30):
        su = set(rng.sample(G.u_ids, 2))
        tv = set(rng.sample(G.v_ids, 2))
        assert is_valid(G, su, tv, 1, 1, 2)
        assert _best_addition(G, su, tv, 1, 1, 2) == _best_addition_slow(G, su, tv, 1, 1, 2)
        checked += 1
    assert checked == 30


def test_empty_stays_empty_and_result_is_maximal():
    edges = [(u, 3 + v) for u in range(3) for v in range(3)]
    G = BipartiteGraph.from_edges(edges, range(3), range(3, 6))
    assert extend(G, [], [], 1, 1, 2) == ([], [])
    S, T = extend(G, [0, 1], [3, 4], 1, 1, 2)
    assert extend(G, S, T, 1, 1, 2) == (S, T)
    # Maximal: no single addition survives the checker.
    for u in G.u_ids:
        if u not in S:
            assert not is_valid(G, set(S) | {u}, set(T), 1, 1, 2)
    for v in G.v_ids:
        if v not in T:
            assert not is_valid(G, set(S), set(T) | {v}, 1, 1, 2)
