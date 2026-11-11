Repo: lollipop
Project id: quasi
Project directory: projects/quasi
Iteration cap N: 40

Problem:
# Gamma-quasi-biclique

Let \(G = (U, V, E)\) be a simple bipartite graph. Identifiers on \(U\) and \(V\) are independent.

The parameters are integers \(p\), \(q\), and \(\theta\) with \(q > 0\), \(p \ge 0\), and \(\theta \ge 0\). Write \(\gamma = p/q\).

A pair \((S, T)\) with \(S \subseteq U\) and \(T \subseteq V\) is feasible when

\[
|S| \ge \theta, \qquad |T| \ge \theta,
\]

and every chosen vertex keeps at least a \(\gamma\) fraction of the opposite side, tested with integers only:

\[
q \cdot |N(u) \cap T| \ge p \cdot |T| \quad \text{for every } u \in S,
\]
\[
q \cdot |N(v) \cap S| \ge p \cdot |S| \quad \text{for every } v \in T.
\]

The objective is the number of edges inside the pair:

\[
\text{maximize } |E(S, T)| = |\{(u, v) \in E : u \in S,\ v \in T\}|.
\]

An empty pair has value 0. `src/checker.py` is the membership test used for scoring. The CP-SAT encoding of this formulation is `solvers/cpsat.py`, laid out in `structure.md`.

## Planted solution

`plant(G, p, q, theta)` in `src/plant.py` hides a feasible pair. It takes the `theta` highest-degree vertices on each side among those whose degree already exceeds the opposite planted size, then adds the fewest missing edges inside that pair that pass the checker. The call returns `None` when that pool is smaller than `theta`. `too_easy` is true when the degree-threshold baseline recovers at least 99% of the planted value. Those instances are not scored.

## Reduction invariant

A reduction returns boolean masks `(keepU, keepV)`. Every vertex of a best-known feasible pair stays kept, and the solver on the kept subgraph can still reach that pair's value.

## Heuristic return value

`search(G, p, q, theta)` returns `(S, T)`, ids from `U` and `V`. The pair has to pass `checker.is_valid`. The score is the fraction of the reference edge count those sets recover. An empty pair scores 0. An infeasible pair scores 0.

Edit files under projects/quasi/. Leave prompts/ unchanged. config.yaml and rungs.yaml are read-only.

# Creating a complete solver

Write a CP-SAT solver for the formulation in `projects/<id>/memory.md`. It must run on any graph the formulation allows, not on a single example.

Read `@run.md` for how to load a graph, plant a solution, and call the solver. Read `@structure.md` for the path. Read `@planter.md` for the plant you test against. Read `@memory.md` so the encoding matches the integer feasibility predicate, not a floating-point gloss.

## Where it goes

Default path: `projects/<id>/solvers/solver.py`, with a public `solve`. The project's own `structure.md`, when it exists, overrides that path and the signature.

Project `quasi` is already encoded. The module is `projects/quasi/solvers/cpsat.py`. `solve(G, p, q, theta, work_limit)` returns `(S, T, value, status, work)`. If the plant check in `projects/quasi/run.md` passes, stop and do not rewrite the file.

## Test

Plant a large solution in a small hand-built graph (`@run.md`). Run CP-SAT. The status on that graph must be optimal, and the value must be at least the planted value. A feasible return that drops the planted structure is a failed test. Fix the model and run the test again.

One search worker. Seed from `problem.seed()`. `work_limit` is `max_deterministic_time`.

## Encoding

Build the model from the feasibility section and the objective section of `memory.md`.

- Boolean variables for the solution object.
- Linear inequalities that match the integer feasibility predicate. No floating point.
- Link any edge indicator so a feasible objective equals the objective on that solution, not only at the optimum. For the quasi-biclique that link is `z >= x + y - 1`, written in `projects/quasi/structure.md`.
- If the graph is smaller than the formulation's minimum solution, return the empty solution and do not search.

Do not edit `config.yaml` or `rungs.yaml`.
