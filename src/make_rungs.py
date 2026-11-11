"""Build the dev / held-out rung ladder and write rungs.yaml.

Dev rungs are BFS balls (vertex-induced, never edge-sampled) of three
bipartite KONECT graphs. Held-out rungs are other full bipartite graphs,
one per half order of magnitude of m. Graphs the dev balls were cut from
are not reused as held-out rungs.
"""

from __future__ import annotations

import json
import os
from collections import deque

import yaml

from graphs import half_magnitude, list_local_graphs, load_indexed_csv, load_konect
from projects.quasi.solvers import OPTIMAL, solve
from plant import plant
from problem import ROOT, config, seed

RUNG_DIR = ROOT / "rungs"
GRAPH_DIR = RUNG_DIR / "graphs"
PLANT_DIR = RUNG_DIR / "planted"
YAML_PATH = ROOT / "rungs.yaml"


def _pick_seed(G, target: int):
    """Highest-degree vertex that still leaves room for a second BFS hop.

    A prefix of the global hub's neighborhood is a star. Stars contain no
    K_{2,2}, and every grid cell needs one. The seed is therefore the
    maximum-degree vertex whose degree is at least 2 and strictly less than
    45% of `target` (ties: smaller id, U before V). If no such vertex exists,
    fall back to the global maximum degree.
    """
    cap = max(3, int(target * 0.45))
    best = None
    best_key = None
    for u in G.u_ids:
        d = G.degree_u(u)
        if 2 <= d < cap:
            key = (d, -u, 0)
            if best_key is None or key > best_key:
                best_key = key
                best = ("U", u)
    for v in G.v_ids:
        d = G.degree_v(v)
        if 2 <= d < cap:
            key = (d, -v, -1)
            if best_key is None or key > best_key:
                best_key = key
                best = ("V", v)
    if best is not None:
        return best
    for u in G.u_ids:
        key = (G.degree_u(u), -u, 0)
        if best_key is None or key > best_key:
            best_key = key
            best = ("U", u)
    for v in G.v_ids:
        key = (G.degree_v(v), -v, -1)
        if best_key is None or key > best_key:
            best_key = key
            best = ("V", v)
    return best


def _has_k22(G) -> bool:
    nbrs = [set(G.neighbors_u(u)) for u in G.u_ids]
    for i in range(len(nbrs)):
        for j in range(i + 1, len(nbrs)):
            if len(nbrs[i] & nbrs[j]) >= 2:
                return True
    return False


def bfs_ball(G, target: int, name: str):
    """Vertex-induced subgraph on the first `target` vertices of a BFS.

    Neighbor expansion follows sorted ids, so the ball is deterministic.
    See `_pick_seed` for why the seed is not always the global hub.
    """
    if target < 1:
        raise ValueError("target must be positive")
    best = _pick_seed(G, target)
    if best is None:
        raise RuntimeError(f"{name}: empty graph")

    seen = {best}
    order = [best]
    queue = deque([best])
    while queue and len(order) < target:
        side, vid = queue.popleft()
        if side == "U":
            nbrs = [("V", v) for v in G.neighbors_u(vid)]
        else:
            nbrs = [("U", u) for u in G.neighbors_v(vid)]
        for nb in nbrs:
            if nb in seen:
                continue
            seen.add(nb)
            order.append(nb)
            queue.append(nb)
            if len(order) >= target:
                break
    if len(order) < target:
        raise RuntimeError(f"{name}: BFS reached {len(order)} < {target}")
    keep_u = [vid for side, vid in order if side == "U"]
    keep_v = [vid for side, vid in order if side == "V"]
    induced = G.induced(keep_u, keep_v, name=name)
    if induced.n_u + induced.n_v != target:
        raise RuntimeError(f"{name}: induced order {induced.n_u + induced.n_v}")
    return induced, {"seed_side": best[0], "seed_id": best[1]}


def select_held_out(records, dev_sources, max_edges, min_edges=1000):
    """One bipartite graph per half-magnitude bucket, smallest m in the bucket."""
    chosen = {}
    for rec in sorted(records, key=lambda r: (r["m"], r["key"])):
        if not rec.get("bipartite", True):
            continue
        if rec["key"] in dev_sources:
            continue
        if rec["m"] < min_edges or rec["m"] > max_edges:
            continue
        bucket = half_magnitude(rec["m"])
        if bucket not in chosen:
            chosen[bucket] = rec
    return [chosen[b] for b in sorted(chosen)]


def save_graph(G, path):
    path = str(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {"name": G.name, "u": G.u_ids, "v": G.v_ids, "edges": G.dump_edges()}
    with open(path, "w") as f:
        json.dump(payload, f)
    return path


def load_graph(path, name=None):
    path = str(path)
    if path.endswith(".json"):
        with open(path) as f:
            payload = json.load(f)
        from graphs import BipartiteGraph
        return BipartiteGraph.from_edges(payload["edges"], payload["u"], payload["v"], name=name or payload.get("name"))
    return load_indexed_csv(path, name=name)


def _simple_stats(path):
    """Unique endpoints and simple-edge count. One pass, no adjacency lists."""
    import csv
    us = set()
    vs = set()
    edges = set()
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            u, v = int(row["u"]), int(row["v"])
            us.add(u)
            vs.add(v)
            edges.add((u, v))
    return len(us), len(vs), len(edges)


def _family_of(key, entity_names):
    low = key.lower()
    if "matter" in low or "author" in entity_names.replace(" ", ""):
        return "author-paper"
    if "wiktionary" in low:
        return "wiktionary"
    if "wikiquote" in low:
        return "wikiquote"
    if "wikibooks" in low:
        return "wikibooks"
    if "wikinews" in low:
        return "wikinews"
    if "wikisource" in low:
        return "wikisource"
    if "wiki" in low:
        return "wiki"
    return "other"


def build_catalog(probe=True):
    cfg = config()
    dev_sources = cfg["dev_sources"]
    dev_keys = {row["key"] for row in dev_sources}
    sizes = [int(s) for s in cfg["dev_sizes"]]
    cap = int(cfg["oracle_vertex_cap"])
    work_limit = float(cfg["oracle_work_limit"])
    max_edges = int(cfg["max_comfortable_edges"])

    rungs = []
    for src in dev_sources:
        print(f"loading dev source {src['key']}", flush=True)
        G = load_konect(src["key"])
        for n in sizes:
            name = f"dev-{src['family']}-n{n}"
            induced, info = bfs_ball(G, n, name)
            if not _has_k22(induced):
                raise RuntimeError(f"{name} contains no K2,2; the BFS seed left a star")
            status = False
            probe_work = None
            if probe and induced.n_u + induced.n_v <= cap:
                print(f"  probe {name} n={n} m={induced.m}", flush=True)
                _S, _T, _val, st, probe_work = solve(induced, 9, 10, 3, work_limit)
                status = st == OPTIMAL
            path = save_graph(induced, GRAPH_DIR / f"{name}.json")
            rungs.append({
                "name": name,
                "source": src["key"],
                "family": src["family"],
                "n_u": induced.n_u,
                "n_v": induced.n_v,
                "m": induced.m,
                "split": "dev",
                "exact_status": bool(status),
                "probe_cell": [9, 10, 3],
                "probe_work": probe_work,
                "graph": os.path.relpath(path, ROOT),
                "seed_side": info["seed_side"],
                "seed_id": info["seed_id"],
            })

    print("scanning local bipartite graphs", flush=True)
    listed = list_local_graphs(bipartite_only=True)
    records = []
    for row in listed:
        if row["edges_rows"] > max_edges * 3:
            # Multi-edges cannot pull 3x-over files under the comfortable cap.
            continue
        n_u, n_v, m = _simple_stats(row["path"])
        records.append({
            "key": row["key"],
            "path": row["path"],
            "m": m,
            "n_u": n_u,
            "n_v": n_v,
            "bipartite": True,
            "family": _family_of(row["key"], row.get("entity_names", "")),
        })
    held = select_held_out(records, dev_keys, max_edges)
    for rec in held:
        n = rec["n_u"] + rec["n_v"]
        status = False
        if probe and n <= cap:
            G = load_indexed_csv(rec["path"], name=rec["key"])
            _S, _T, _val, st, _w = solve(G, 9, 10, 3, work_limit)
            status = st == OPTIMAL
        rungs.append({
            "name": rec["key"],
            "source": rec["key"],
            "family": rec["family"],
            "n_u": rec["n_u"],
            "n_v": rec["n_v"],
            "m": rec["m"],
            "split": "held-out",
            "exact_status": bool(status),
            "probe_cell": [9, 10, 3],
            "graph": rec["path"],
        })

    rungs.sort(key=lambda r: (r["m"], r["name"]))
    for i in range(1, len(rungs)):
        if rungs[i]["m"] < rungs[i - 1]["m"]:
            raise RuntimeError("rungs are not ordered by m")
    return rungs


def plant_unsolved(rungs):
    """Plant every (rung, grid cell) the probe did not prove. Writes JSON."""
    from problem import cells
    os.makedirs(PLANT_DIR, exist_ok=True)
    cache = {}
    for rung in rungs:
        if rung["exact_status"]:
            rung["planted"] = []
            continue
        print(f"planting {rung['name']}", flush=True)
        if rung["graph"] not in cache:
            cache[rung["graph"]] = load_graph(ROOT / rung["graph"] if not os.path.isabs(rung["graph"]) else rung["graph"], name=rung["name"])
        G = cache[rung["graph"]]
        rows = []
        for p, q, theta in cells():
            print(f"  cell p={p} q={q} theta={theta}", flush=True)
            result = plant(G, p, q, theta)
            tag = f"{rung['name'].replace('/', '_')}__p{p}_q{q}_t{theta}.json"
            path = PLANT_DIR / tag
            if result is None:
                payload = {"rung": rung["name"], "p": p, "q": q, "theta": theta, "unplantable": True, "too_easy": True}
            else:
                payload = {
                    "rung": rung["name"],
                    "p": p,
                    "q": q,
                    "theta": theta,
                    "unplantable": False,
                    "S": result["S"],
                    "T": result["T"],
                    "extra_edges": result["extra_edges"],
                    "value": result["value"],
                    "baseline_value": result["baseline_value"],
                    "too_easy": result["too_easy"],
                }
            with open(path, "w") as f:
                json.dump(payload, f)
            rows.append({
                "p": p,
                "q": q,
                "theta": theta,
                "path": os.path.relpath(path, ROOT),
                "value": payload.get("value"),
                "too_easy": payload["too_easy"],
                "unplantable": payload["unplantable"],
            })
        rung["planted"] = rows
        # Drop the graph if it is large; the next rung may share it.
    return rungs


def write_yaml(rungs, path=YAML_PATH):
    os.makedirs(RUNG_DIR, exist_ok=True)
    with open(path, "w") as f:
        f.write("# Generated by make_rungs.py. Review before any evolution run.\n")
        f.write(f"# seed: {seed()}\n")
        yaml.safe_dump({"rungs": rungs}, f, sort_keys=False)
    return path


def load_rungs(path=YAML_PATH):
    with open(path) as f:
        # The file starts with comments; safe_load handles them.
        data = yaml.safe_load(f)
    return data["rungs"]


def main():
    rungs = build_catalog(probe=True)
    rungs = plant_unsolved(rungs)
    path = write_yaml(rungs)
    dev = [r for r in rungs if r["split"] == "dev"]
    held = [r for r in rungs if r["split"] == "held-out"]
    print(f"wrote {path}: {len(dev)} dev, {len(held)} held-out", flush=True)
    for r in rungs:
        flag = "OPT" if r["exact_status"] else "plant"
        print(f"  {r['m']:8d}  {r['split']:8s}  {flag:5s}  {r['name']}", flush=True)


if __name__ == "__main__":
    main()
