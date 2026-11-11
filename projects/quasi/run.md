# Planting a solution and running CP-SAT

Graphs come from the local GraphLogic index.

```python
from checker import is_valid, value
from graphs import BipartiteGraph, load_konect
from plant import plant
from projects.quasi.solvers import OPTIMAL, solve

G = load_konect("konect-small/edit-zuwiktionary")
```

`plant(G, p, q, theta)` picks \(S^\star\) and \(T^\star\) as the \(\theta\) highest-degree vertices on each side among those whose degree already exceeds the opposite planted size. It then adds the fewest missing edges inside \(S^\star \times T^\star\) that make the pair pass the checker. The call returns `None` when that degree pool is smaller than \(\theta\).

The planted graph is `result["graph"]`. `result["value"]` is \(|E(S^\star, T^\star)|\) after those edges are added. `result["too_easy"]` is true when the degree-threshold baseline already recovers at least 99% of that value.

A hand-built graph uses the same call:

```python
edges = [(u, 10 + v) for u in range(6) for v in range(6)]
small = BipartiteGraph.from_edges(edges, range(6), range(10, 16))
planted = plant(small, 9, 10, 3)
```

`solve` is the CP-SAT model in `structure.md`. `work_limit` is `max_deterministic_time`.

```python
graph = planted["graph"]
S, T, found, status, work = solve(graph, 9, 10, 3, work_limit=10.0)
assert status == OPTIMAL
assert is_valid(graph, S, T, 9, 10, 3)
assert value(graph, S, T) == found
assert found >= planted["value"]
```

The planted pair is feasible, so an optimal solve on a small graph is at least `planted["value"]`. `S` and `T` come back sorted.
