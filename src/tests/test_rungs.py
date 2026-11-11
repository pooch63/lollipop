"""BFS balls and held-out bucket selection."""

from graphs import BipartiteGraph, half_magnitude
from make_rungs import bfs_ball, select_held_out


def test_bfs_ball_is_vertex_induced_and_exact_size():
    # A path U0-V0-U1-V1-U2-V2-... so BFS from the highest degree (all deg <= 2)
    # is deterministic. Make U0 the unique max degree.
    edges = [(0, 10), (0, 11), (0, 12), (1, 10), (2, 11), (3, 12), (4, 13), (5, 13)]
    u_ids = list(range(6))
    v_ids = list(range(10, 14))
    G = BipartiteGraph.from_edges(edges, u_ids, v_ids)
    induced, info = bfs_ball(G, 6, "toy")
    assert induced.n_u + induced.n_v == 6
    # u=0 has degree 3, which is outside the "leave room" band (cap 3).
    # The highest in-band degree is 2, on V, smallest id 10.
    assert info["seed_side"] == "V" and info["seed_id"] == 10
    # Every edge of the induced subgraph exists in G, and every G edge
    # inside the vertex set is kept (vertex-induced, not edge-sampled).
    keep_u, keep_v = set(induced.u_ids), set(induced.v_ids)
    for u, v in induced.dump_edges():
        assert G.has_edge(u, v)
    for u, v in G.dump_edges():
        if u in keep_u and v in keep_v:
            assert induced.has_edge(u, v)


def test_bfs_order_follows_sorted_neighbors():
    # Star from u=0 to v=1,2,3 then each v touches a private u.
    edges = [(0, 1), (0, 2), (0, 3), (4, 1), (5, 2), (6, 3)]
    G = BipartiteGraph.from_edges(edges, [0, 4, 5, 6], [1, 2, 3])
    induced, info = bfs_ball(G, 5, "star")
    # v=1 has degree 2, inside the band; u=0 has degree 3, which is the cap.
    assert info == {"seed_side": "V", "seed_id": 1}
    assert set(induced.u_ids) == {0, 4}
    assert set(induced.v_ids) == {1, 2, 3}


def test_seed_leaves_room_so_the_ball_is_not_a_star():
    # Hub u=0 touches 30 leaves. u=1 touches two of those leaves and has
    # degree 2, which is inside the band for target 20 (cap = 9). The ball
    # must include u=1 and therefore a K_{2,2} is possible; it must not be
    # the pure star around u=0.
    edges = [(0, v) for v in range(100, 130)]
    edges += [(1, 100), (1, 101), (2, 102), (2, 103)]
    G = BipartiteGraph.from_edges(edges, range(3), range(100, 130))
    induced, info = bfs_ball(G, 20, "dense")
    assert info == {"seed_side": "U", "seed_id": 1}
    assert 0 in induced.u_ids and 1 in induced.u_ids
    assert induced.has_edge(0, 100) and induced.has_edge(1, 100) and induced.has_edge(1, 101)


def test_held_out_one_per_bucket_excludes_dev_sources():
    records = [
        {"key": "a", "m": 1200, "bipartite": True},
        {"key": "b", "m": 1800, "bipartite": True},   # same 10^3.0 bucket as a? 
        {"key": "dev", "m": 1500, "bipartite": True},
        {"key": "c", "m": 20000, "bipartite": True},
        {"key": "d", "m": 25000, "bipartite": True},
        {"key": "huge", "m": 10_000_000, "bipartite": True},
        {"key": "uni", "m": 5000, "bipartite": False},
        {"key": "tiny", "m": 50, "bipartite": True},
    ]
    # Confirm a and b share a bucket so the test is actually checking "one".
    assert half_magnitude(1200) == half_magnitude(1800)
    assert half_magnitude(20000) == half_magnitude(25000)
    picked = select_held_out(records, dev_sources={"dev"}, max_edges=3_000_000)
    keys = [r["key"] for r in picked]
    assert keys == ["a", "c"]
    assert all(keys[i] == sorted(keys, key=lambda k: next(r["m"] for r in records if r["key"] == k))[i] for i in range(len(keys)))
    ms = [r["m"] for r in picked]
    assert ms == sorted(ms)
