# Creating a complete solver

Write a CP-SAT solver for the formulation in `projects/<id>/memory.md`. It must run on any graph the formulation allows, not on a single example.

Read `@run.md` for how to load a graph. Read `@structure.md` for the path. Read `@check.md`. Use `plant` and `is_valid` from `projects/<id>/plant.py` and `projects/<id>/checker.py`. Read `@memory.md` so the encoding matches the integer feasibility predicate.

## Where it goes

Default path: `projects/<id>/solvers/solver.py`, with a public `solve`. The project's own `structure.md`, when it exists, overrides that path and the signature.

Project `quasi` is already encoded. The module is `projects/quasi/solvers/cpsat.py`. `solve(G, p, q, theta, work_limit)` returns `(S, T, value, status, work)`. If the plant check in `projects/quasi/run.md` passes, stop and do not rewrite the file.

## Test

Plant a large solution in a small hand-built graph with the project's `plant`. Run CP-SAT. The status on that graph must be optimal, and the value must be at least the planted value. A feasible return that drops the planted structure is a failed test. Put that test in `test_solver.py`.

Reply with fenced python blocks. The first line inside each fence is `# file: solvers/solver.py` or `# file: test_solver.py`.

One search worker. Seed from `problem.seed()`. `work_limit` is `max_deterministic_time`.

## Encoding

Build the model from the feasibility section and the objective section of `memory.md`.

- Boolean variables for the solution object.
- Linear inequalities that match the integer feasibility predicate. No floating point.
- Link any edge indicator so a feasible objective equals the objective on that solution, not only at the optimum. For the quasi-biclique that link is `z >= x + y - 1`, written in `projects/quasi/structure.md`.
- If the graph is smaller than the formulation's minimum solution, return the empty solution and do not search.

Do not edit `config.yaml` or `rungs.yaml`.
