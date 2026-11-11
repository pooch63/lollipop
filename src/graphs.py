"""Read GraphLogic indexed bipartite graphs. Do not reimplement storage.

See API_NOTES.md. Adjacency is the simple graph: duplicate CSV rows collapse.
"""

from __future__ import annotations

import csv
import math
import os
from collections import defaultdict

from problem import data_roots


class BipartiteGraph:
    """U and V ids are independent, matching GraphLogic FrozenBipartite."""

    def __init__(self, adj_u: dict[int, tuple[int, ...]], adj_v: dict[int, tuple[int, ...]], name: str | None = None):
        self.adj_u = adj_u
        self.adj_v = adj_v
        self.name = name
        self._m = sum(len(vs) for vs in adj_u.values())

    @property
    def n_u(self) -> int:
        return len(self.adj_u)

    @property
    def n_v(self) -> int:
        return len(self.adj_v)

    @property
    def m(self) -> int:
        return self._m

    @property
    def u_ids(self) -> list[int]:
        return sorted(self.adj_u)

    @property
    def v_ids(self) -> list[int]:
        return sorted(self.adj_v)

    def neighbors_u(self, u: int) -> tuple[int, ...]:
        return self.adj_u.get(u, ())

    def neighbors_v(self, v: int) -> tuple[int, ...]:
        return self.adj_v.get(v, ())

    def degree_u(self, u: int) -> int:
        return len(self.neighbors_u(u))

    def degree_v(self, v: int) -> int:
        return len(self.neighbors_v(v))

    def has_edge(self, u: int, v: int) -> bool:
        # Neighbor tuples are sorted.
        nbrs = self.adj_u.get(u)
        if not nbrs:
            return False
        lo, hi = 0, len(nbrs) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if nbrs[mid] == v:
                return True
            if nbrs[mid] < v:
                lo = mid + 1
            else:
                hi = mid - 1
        return False

    def induced(self, keep_u, keep_v, name: str | None = None) -> "BipartiteGraph":
        """Vertex-induced subgraph. Original ids are preserved, including isolates."""
        ku = set(keep_u)
        kv = set(keep_v)
        adj_u: dict[int, tuple[int, ...]] = {}
        adj_v: dict[int, tuple[int, ...]] = {v: () for v in kv}
        for u in ku:
            kept = tuple(v for v in self.neighbors_u(u) if v in kv)
            adj_u[u] = kept
            for v in kept:
                adj_v[v] = adj_v[v] + (u,)
        adj_v = {v: tuple(sorted(us)) for v, us in adj_v.items()}
        return BipartiteGraph(adj_u, adj_v, name=name or self.name)

    def with_edges(self, extra: list[tuple[int, int]], name: str | None = None) -> "BipartiteGraph":
        """Copy that also contains extra (u, v) edges. Endpoints must already exist."""
        adj_u = {u: set(vs) for u, vs in self.adj_u.items()}
        adj_v = {v: set(us) for v, us in self.adj_v.items()}
        for u, v in extra:
            if u not in adj_u or v not in adj_v:
                raise KeyError(f"endpoint not in graph: {(u, v)}")
            adj_u[u].add(v)
            adj_v[v].add(u)
        return BipartiteGraph(
            {u: tuple(sorted(vs)) for u, vs in adj_u.items()},
            {v: tuple(sorted(us)) for v, us in adj_v.items()},
            name=name or self.name,
        )

    @staticmethod
    def from_edges(edges, u_ids=None, v_ids=None, name: str | None = None) -> "BipartiteGraph":
        buckets_u: dict[int, set[int]] = defaultdict(set)
        buckets_v: dict[int, set[int]] = defaultdict(set)
        if u_ids is not None:
            for u in u_ids:
                buckets_u[int(u)]
        if v_ids is not None:
            for v in v_ids:
                buckets_v[int(v)]
        for u, v in edges:
            u, v = int(u), int(v)
            buckets_u[u].add(v)
            buckets_v[v].add(u)
        return BipartiteGraph(
            {u: tuple(sorted(vs)) for u, vs in buckets_u.items()},
            {v: tuple(sorted(us)) for v, us in buckets_v.items()},
            name=name,
        )

    def dump_edges(self) -> list[tuple[int, int]]:
        out = []
        for u in self.u_ids:
            for v in self.neighbors_u(u):
                out.append((u, v))
        return out


def load_indexed_csv(path: str, name: str | None = None) -> BipartiteGraph:
    buckets_u: dict[int, set[int]] = defaultdict(set)
    buckets_v: dict[int, set[int]] = defaultdict(set)
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            u, v = int(row["u"]), int(row["v"])
            buckets_u[u].add(v)
            buckets_v[v].add(u)
    return BipartiteGraph(
        {u: tuple(sorted(vs)) for u, vs in buckets_u.items()},
        {v: tuple(sorted(us)) for v, us in buckets_v.items()},
        name=name,
    )


def _ignored(key: str) -> bool:
    parts = key.split("/")
    return "raw" in parts or "mappings" in parts


def list_local_graphs(roots: list[str] | None = None, prefix: tuple[str, ...] = ("konect", "konect-small"), bipartite_only: bool = False) -> list[dict]:
    """Discover GraphLogic indexed graphs. Edge count is simple edges, not CSV rows.

    `edges_rows` is the GraphLogic count (CSV rows minus header) so it can be
    compared with `order_graphs_by_edges`.
    """
    roots = roots if roots is not None else data_roots()
    found: dict[str, dict] = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            if "indexed_interactions.csv" not in files:
                continue
            rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
            if rel == "." or _ignored(rel):
                continue
            if prefix and not any(rel == p or rel.startswith(p + "/") for p in prefix):
                continue
            if rel in found:
                continue
            path = os.path.join(dirpath, "indexed_interactions.csv")
            rows = _count_rows(path)
            meta = _read_meta(dirpath)
            bip = _is_bipartite(meta)
            found[rel] = {
                "key": rel,
                "path": path,
                "edges_rows": rows,
                "bipartite": bip,
                "category": meta.get("category", ""),
                "entity_names": meta.get("entity-names", ""),
                "root": root,
            }
    rows_out = list(found.values())
    if bipartite_only:
        rows_out = [r for r in rows_out if r["bipartite"]]
    rows_out.sort(key=lambda r: (r["edges_rows"], r["key"]))
    return rows_out


def _count_rows(path: str) -> int:
    n = 0
    with open(path, "rb") as f:
        for _ in f:
            n += 1
    return max(0, n - 1)


def _read_meta(dataset_dir: str) -> dict[str, str]:
    raw = os.path.join(dataset_dir, "raw")
    if not os.path.isdir(raw):
        return {}
    for dirpath, _dirs, files in os.walk(raw):
        for name in files:
            if name.startswith("meta."):
                fields: dict[str, str] = {}
                with open(os.path.join(dirpath, name), errors="replace") as f:
                    for line in f:
                        if ":" in line:
                            k, v = line.split(":", 1)
                            fields[k.strip()] = v.strip()
                return fields
    return {}


def _is_bipartite(meta: dict[str, str]) -> bool:
    names = meta.get("entity-names", "")
    return "," in names


def load_konect(name: str, roots: list[str] | None = None) -> BipartiteGraph:
    """Load a local KONECT graph by GraphLogic dataset key. Does not download."""
    roots = roots if roots is not None else data_roots()
    rel = name.replace("\\", "/").strip("/")
    for root in roots:
        path = os.path.join(root, *rel.split("/"), "indexed_interactions.csv")
        if os.path.isfile(path):
            return load_indexed_csv(path, name=rel)
    raise FileNotFoundError(f"no indexed graph for {name!r} under {roots}")


def half_magnitude(m: int) -> float:
    """Bucket label floor(2*log10(m))/2. m >= 1."""
    if m < 1:
        return 0.0
    return math.floor(2.0 * math.log10(m)) / 2.0
