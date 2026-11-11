# Degree-core greedy search for a gamma-quasi-biclique.
# bar = ceil(p * theta / q). Keep vertices of degree at least bar, drop the
# worst membership deficit until the pair is valid, then add the vertex that
# increases |E(S, T)| the most without breaking the integer membership test.
# Ties: smaller id, and U before V when the ids are equal.


def pair_ok(S, T, hit_u, hit_v, p, q, theta):
    if len(S) < theta or len(T) < theta:
        return False
    need_u = p * len(T)
    need_v = p * len(S)
    for u in S:
        if q * hit_u[u] < need_u:
            return False
    for v in T:
        if q * hit_v[v] < need_v:
            return False
    return True


def add_u(G, S, hit_v, u):
    S.add(u)
    for v in G.neighbors_u(u):
        hit_v[v] = hit_v[v] + 1


def add_v(G, T, hit_u, v):
    T.add(v)
    for u in G.neighbors_v(v):
        hit_u[u] = hit_u[u] + 1


def rem_u(G, S, hit_v, u):
    S.remove(u)
    for v in G.neighbors_u(u):
        hit_v[v] = hit_v[v] - 1


def rem_v(G, T, hit_u, v):
    T.remove(v)
    for u in G.neighbors_v(v):
        hit_u[u] = hit_u[u] - 1


def worst(G, S, T, hit_u, hit_v, p, q):
    best = None
    best_key = None
    need_u = p * len(T)
    for u in S:
        hits = hit_u[u]
        if q * hits >= need_u:
            continue
        key = (need_u - q * hits, -G.degree_u(u), -u, 0)
        if best_key is None or key > best_key:
            best_key = key
            best = ("U", u)
    need_v = p * len(S)
    for v in T:
        hits = hit_v[v]
        if q * hits >= need_v:
            continue
        key = (need_v - q * hits, -G.degree_v(v), -v, -1)
        if best_key is None or key > best_key:
            best_key = key
            best = ("V", v)
    return best


def can_add_u(G, S, T, hit_u, hit_v, p, q, theta, u):
    if u in S or len(T) < theta or len(S) + 1 < theta:
        return False
    if q * hit_u[u] < p * len(T):
        return False
    nbrs = G.neighbors_u(u)
    need = p * (len(S) + 1)
    for v in T:
        extra = 1 if v in nbrs else 0
        if q * (hit_v[v] + extra) < need:
            return False
    return True


def can_add_v(G, S, T, hit_u, hit_v, p, q, theta, v):
    if v in T or len(S) < theta or len(T) + 1 < theta:
        return False
    if q * hit_v[v] < p * len(S):
        return False
    nbrs = G.neighbors_v(v)
    need = p * (len(T) + 1)
    for u in S:
        extra = 1 if u in nbrs else 0
        if q * (hit_u[u] + extra) < need:
            return False
    return True


def best_add(G, S, T, hit_u, hit_v, p, q, theta):
    best = None
    best_key = None
    for u in G.u_ids:
        if not can_add_u(G, S, T, hit_u, hit_v, p, q, theta, u):
            continue
        key = (hit_u[u], -u, 0)
        if best_key is None or key > best_key:
            best_key = key
            best = ("U", u)
    for v in G.v_ids:
        if not can_add_v(G, S, T, hit_u, hit_v, p, q, theta, v):
            continue
        key = (hit_v[v], -v, -1)
        if best_key is None or key > best_key:
            best_key = key
            best = ("V", v)
    return best


def search(G, p, q, theta):
    hit_u = {}
    hit_v = {}
    for u in G.u_ids:
        hit_u[u] = 0
    for v in G.v_ids:
        hit_v[v] = 0
    S = set()
    T = set()
    bar = (p * theta + q - 1) // q
    for u in G.u_ids:
        if G.degree_u(u) >= bar:
            add_u(G, S, hit_v, u)
    for v in G.v_ids:
        if G.degree_v(v) >= bar:
            add_v(G, T, hit_u, v)
    drops = 0
    limit = G.n_u + G.n_v + 1
    while drops < limit and len(S) >= theta and len(T) >= theta and not pair_ok(S, T, hit_u, hit_v, p, q, theta):
        pick = worst(G, S, T, hit_u, hit_v, p, q)
        if pick is None:
            break
        side, vid = pick
        if side == "U":
            rem_u(G, S, hit_v, vid)
        else:
            rem_v(G, T, hit_u, vid)
        drops = drops + 1
    if not pair_ok(S, T, hit_u, hit_v, p, q, theta):
        return [], []
    added = 0
    while added < limit:
        pick = best_add(G, S, T, hit_u, hit_v, p, q, theta)
        if pick is None:
            break
        side, vid = pick
        if side == "U":
            add_u(G, S, hit_v, vid)
        else:
            add_v(G, T, hit_u, vid)
        added = added + 1
    return sorted(S), sorted(T)
