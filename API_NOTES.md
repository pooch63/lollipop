# GraphLogic API notes

The library that stores bipartite graphs and loads KONECT data is **GraphLogic.jl**
at `/home/kiyaanpillai/Documents/graph-logic`. It is a Julia package, not a Python
package. No separate Python graph library was found on this machine. The harness
does not reimplement download, id indexing, or the on-disk layout. It reads the
indexed CSVs GraphLogic already produced.

Local data roots used by that library:

- `/home/kiyaanpillai/Documents/epsilon-core/data`
- `/home/kiyaanpillai/Documents/aco-mkdb/data`

A saved copy of the KONECT network catalog is `Networks.html` in this repo.

## Bipartite graph class

Phase 1 is a mutable graph. Phase 2 freezes it into CSR arrays.

```julia
struct BipartiteGraph{T}
    adjU::Dict{Int, Set{Int}}          # u => neighbor set in V
    adjV::Dict{Int, Set{Int}}          # v => neighbor set in U
    edge_data::Dict{Tuple{Int,Int}, T} # (u, v) => metadata
end
```

`T` is `Nothing` for plain KONECT edges. Construct with `BipartiteGraph{Nothing}()`.

Mutation (exported): `add_u!`, `add_v!`, `add_edge!`, `rem_u!`, `rem_v!`,
`rem_edge!`, plus structural variants `rem_edge_structural!`, `rem_u_structural!`,
`rem_v_structural!`, `rem_node!`, `rem_node_structural!`.

Queries on the mutable graph:

| Function | Meaning |
|---|---|
| `neighbors_u(g, u)` | `Set{Int}` of V-neighbors |
| `neighbors_v(g, v)` | `Set{Int}` of U-neighbors |
| `degree_u(g, u)`, `degree_v(g, v)` | set lengths |
| `has_edge(g, u, v)` | edge existence |
| `get_neighbors(g, is_u, id)`, `get_degree(g, is_u, id)` | side-dispatch |

`freeze(g)` builds `FrozenBipartite`. U and V keep **independent** integer ids
(indexed KONECT files use `1..n_U` and `1..n_V`, so the same integer can name
both a U vertex and a V vertex). Frozen queries take the original id:

| Function | Meaning |
|---|---|
| `neighbors_u(fg, u_id)` | `Vector{Int}` of V ids, empty if missing |
| `neighbors_v(fg, v_id)` | `Vector{Int}` of U ids, empty if missing |
| `degree_u(fg, u_id)`, `degree_v(fg, v_id)` | `0` if missing |
| `is_neighbor(fg, is_u, node_id, other_id)` | adjacency test |
| `induce_frozen` / `SubGraph` | vertex-induced views |

`load_bipartite_graph(path)` reads a CSV and returns `(BipartiteGraph{Nothing}, edge_count)`.

## Load a KONECT graph by name

Dataset keys look like `"konect/bitcoin"` or `"konect-small/edit-zuwiktionary"`.

```julia
using GraphLogic

fg = load_dataset("konect-small/euroroad")          # download + index if missing
fg = load_dataset("konect/bitcoin"; download=false) # local file only
path = ensure_dataset!("konect/matter"; data_root="data")
g, n_edges = load_bipartite_graph(path)
```

`load_dataset` calls `ensure_dataset!`, which resolves
`data/<provider>/<dataset>/indexed_interactions.csv`, and if that file is
missing runs the provider (`konect` / `konect-small`): download the KONECT
archive, convert the `out.*` edgelist to `interactions.csv`, and index raw ids
to `1..n` independently on each side. `process_with_provider("konect", "bitcoin"; download=true)`
is the lower-level entry.

Python equivalent used by this harness (read-only, no download):

```python
from graphs import load_konect
G = load_konect("konect-small/edit-zuwiktionary")
```

## List available local graphs

```julia
discover_indexed_graphs(; data_root="data")
# Vector of (key, path, edges), unsorted. Skips .dataignore and raw/.

order_graphs_by_edges(; data_root="data", prefix="konect,konect-small")
# same entries, sorted by edge-row count ascending.
# prefix is slash-bounded: "konect" does not match "konect-small".
```

An entry exists for every directory under `data_root` that contains
`indexed_interactions.csv`. `edges` is `countlines(path) - 1` (CSV rows, so
multi-edges are counted once per row).

Python:

```python
from graphs import list_local_graphs
list_local_graphs(bipartite_only=True)
```

Bipartiteness is read from the KONECT `meta.*` file GraphLogic stores under
`raw/`: a comma in `entity-names` means two parts (`user, article`).

## Adjacency access

CSV columns are `u,v` with a header. Extra columns are ignored by
`load_bipartite_graph`. Neighbor lists on the frozen graph are sorted.

Python `BipartiteGraph` mirrors the frozen query surface and collapses duplicate
`(u, v)` rows to a single undirected bipartite edge, because the quasi-biclique
problem uses an adjacency indicator `A_uv`.

```python
G.n_u, G.n_v, G.m
G.u_ids, G.v_ids                 # sorted original ids
G.neighbors_u(u), G.neighbors_v(v)
G.degree_u(u), G.degree_v(v)
G.has_edge(u, v)
G.induced(keep_u, keep_v)        # vertex-induced, original ids preserved
```

`neighbors_*` returns a sorted tuple. Missing ids yield an empty tuple and
degree 0, matching `FrozenBipartite`.
