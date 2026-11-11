# Loading a graph, planting, and running CP-SAT

Run Python with `PYTHONPATH` set to both `src` and the repo root (so `projects` imports). `problem.child_env()` builds that environment.

`config.yaml` and `rungs.yaml` are read-only. Read `oracle_work_limit`, `planted_proof_cap`, `oracle_vertex_cap`, and `max_comfortable_edges` from config. Do not change them.

## List and load

Local graphs are the GraphLogic indexed CSVs named in `config.yaml` `data_roots`. This repo does not download.

```python
from graphs import list_local_graphs, load_konect

rows = list_local_graphs(bipartite_only=True)  # smallest edges_rows first
G = load_konect("konect-small/edit-zuwiktionary")
```

Each row has `key`, `path`, `edges_rows`, `bipartite`, `category`, `entity_names`.

On a `BipartiteGraph`: `n_u`, `n_v`, `m`, `u_ids`, `v_ids`, `neighbors_u(u)`, `neighbors_v(v)`, `degree_u(u)`, `degree_v(v)`, `has_edge(u, v)`, `induced(keep_u, keep_v)`, `with_edges(extra)`, `from_edges(...)`.

`agents.features` computes order, density, and neighborhoods out to 3 hops. See `@server.md`.

## Plant

Follow `@planter.md`. For project `quasi` the call is `plant` from `src/plant.py`, and a full snippet is in `projects/quasi/run.md`.

A hand-built graph is the solver's test, before any KONECT climb:

```python
from graphs import BipartiteGraph
from plant import plant

edges = [(u, 10 + v) for u in range(6) for v in range(6)]
small = BipartiteGraph.from_edges(edges, range(6), range(10, 16))
planted = plant(small, 9, 10, 3)
```

## Solve

Import `solve` from the project solver named in `@structure.md`. For `quasi`:

```python
from checker import is_valid, value
from projects.quasi.solvers import OPTIMAL, solve

graph = planted["graph"]
S, T, found, status, work = solve(graph, 9, 10, 3, work_limit=10.0)
assert status == OPTIMAL
assert is_valid(graph, S, T, 9, 10, 3)
assert found >= planted["value"]
```

`work_limit` is CP-SAT `max_deterministic_time`. `work` is the deterministic time the solver reported. `S` and `T` come back sorted.

For any other project, call the `solve` you wrote under `projects/<id>/solvers/` and assert the same kind of fact: the status is optimal on the small planted graph, and the value is at least the planted value.
