# Reductions

Evolve a reduction for the formulation in `projects/<id>/memory.md`. A reduction deletes vertices or edges. It is better when it deletes more, and it is invalid when the best known solution stops being feasible.

Read `@memory.md`, `@structure.md`, `@server.md`, `@solver.md`, and `projects/<id>/testset.md` from `@graphs.md`.

## What to optimize

On each kept graph, take the best known solution from the project solver (CP-SAT). A candidate reduction scores by how many vertices and edges it removes. It scores zero when any vertex of that solution is deleted, or when the solver on the reduced graph can no longer reach that value.

Keep the reduction that removes the most vertices and edges while the best known solution still sits entirely inside the kept subgraph.

## What to write

Write the program under `projects/<id>/reductions/`.

- For the quasi-biclique, a DSL program is allowed: `reduce(G)` in the language of `src/dsl/`, submitted as kind `dsl` (`@server.md`). `peel`, `map`, and `threshold` are the tools. The safe starting program keeps the degree core `peel(ceil(p * theta / q), ceil(p * theta / q))`.
- For any other formulation, write a Python reduction that only uses the graph reads in `@run.md` and obeys the reduction invariant in `memory.md`.

## Scope

Run this on the small ladder only. Do not fit a reduction on a graph above `oracle_vertex_cap`. Applying a finished reduction to a larger graph is a later call, through `@server.md`, and it is not part of the search.

This stage runs at the same time as `@heuristics.md`. Do not wait for the heuristic, and do not import it. You share the test set and the solver, nothing else.
