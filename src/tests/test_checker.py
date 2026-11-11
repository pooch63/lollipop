"""Checker: integer membership, no floats, basic biclique and quasi cases."""

from graphs import BipartiteGraph
from checker import is_valid, value


def K(n_u, n_v):
    edges = [(u, n_u + v) for u in range(n_u) for v in range(n_v)]
    return BipartiteGraph.from_edges(edges, range(n_u), range(n_u, n_u + n_v))


def test_complete_biclique_gamma_one():
    G = K(3, 4)
    S, T = G.u_ids, G.v_ids
    assert is_valid(G, S, T, 1, 1, 2)
    assert value(G, S, T) == 12
    # Dropping below theta fails.
    assert not is_valid(G, S[:1], T, 1, 1, 2)


def test_missing_edge_fails_biclique_but_passes_seven_tenths():
    # K_{3,3} minus one edge. gamma=1 fails; gamma=7/10, theta=2 passes
    # because each vertex still has at least ceil(0.7 * 3) = 3? 
    # q=10, p=7, |T|=3: need 10*inter >= 21 so inter >= 3. The deficient
    # vertex has inter 2, so the full sets fail. A 3x2 subset can pass.
    edges = [(u, 3 + v) for u in range(3) for v in range(3) if not (u == 0 and v == 0)]
    G = BipartiteGraph.from_edges(edges, range(3), range(3, 6))
    assert not is_valid(G, [0, 1, 2], [3, 4, 5], 1, 1, 2)
    # |T|=2, gamma=7/10: need 10*inter >= 14 so inter >= 2. Both sides of a
    # complete K_{2,2} pass. Vertices 1,2 and V 3,4 form K_{2,2}.
    S, T = [1, 2], [3, 4]
    assert is_valid(G, S, T, 7, 10, 2)
    assert value(G, S, T) == 4


def test_quasi_not_biclique():
    # Each u connects to 2 of 3 v's; each v connects to 2 of 2 u's? 
    # U={0,1}, V={2,3,4}. Edges: all except (0,4) and (1,4).
    # |T|=3, p=1, q=2: need inter >= 2 (2*inter >= 3). u0 has 2, u1 has 2.
    # |S|=2: each v needs 2*inter >= 2 so inter >= 1. v4 has 0, so fail.
    # |T|={2,3}: both u have both neighbors. v's have both u's. gamma 1/2 and 1.
    edges = [(0, 2), (0, 3), (1, 2), (1, 3), (0, 4)]
    G = BipartiteGraph.from_edges(edges, [0, 1], [2, 3, 4])
    S, T = [0, 1], [2, 3, 4]
    # gamma = 1/2: u0 meets 3, u1 meets 2 (need >= 2); v4 meets 1 (need >= 1).
    assert is_valid(G, S, T, 1, 2, 2)
    assert not is_valid(G, S, T, 1, 1, 2)  # missing (1, 4)
    assert value(G, S, T) == 5


def test_duplicates_in_S_do_not_inflate():
    G = K(2, 2)
    assert value(G, [0, 0, 1], [2, 3]) == 4
    assert is_valid(G, [0, 0, 1], [2, 3], 1, 1, 2)


def test_rejects_non_int_parameters():
    G = K(2, 2)
    try:
        is_valid(G, [0, 1], [2, 3], 0.9, 1, 2)
        raised = False
    except TypeError:
        raised = True
    assert raised


def test_integer_boundary():
    # |T|=10, p=9, q=10: need 10*inter >= 90 so inter >= 9.
    # A vertex with 8 neighbors fails; with 9 passes.
    u_ids = [0]
    v_ids = list(range(1, 11))
    edges = [(0, v) for v in v_ids[:8]]
    G = BipartiteGraph.from_edges(edges, u_ids, v_ids)
    # theta=1 so a singleton S is allowed. Add a second u that is complete
    # so the V side can satisfy |S|=2.
    edges2 = edges + [(1, v) for v in v_ids]
    G2 = BipartiteGraph.from_edges(edges2, [0, 1], v_ids)
    assert not is_valid(G2, [0, 1], v_ids, 9, 10, 1)
    edges3 = [(0, v) for v in v_ids[:9]] + [(1, v) for v in v_ids]
    G3 = BipartiteGraph.from_edges(edges3, [0, 1], v_ids)
    # u0 has 9, u1 has 10. V vertices 1..9 have both u's; v=10 has only u1.
    # |S|=2, p=9,q=10: need 10*inter >= 18 so inter >= 2. v=10 has 1. Fail.
    assert not is_valid(G3, [0, 1], v_ids, 9, 10, 1)
    T = v_ids[:9]
    assert is_valid(G3, [0, 1], T, 9, 10, 1)
    assert value(G3, [0, 1], T) == 9 + 9
