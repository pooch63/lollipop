# Planting a solution

A planted solution is a known feasible structure hidden in a small graph. Scoring asks how much of it a program brings back. The first filter on every test graph is a planted solution. CP-SAT comes after that, once a solver exists.

Read the formulation in the project's `memory.md` before planting. The hidden structure has to be feasible for that formulation, not for some other problem.

## Rules that every project follows

1. Build the plant on a small graph. A hand-built graph is enough to test a solver. A KONECT graph is for the ladder in `@graphs.md`.
2. The planted object must pass the formulation's feasibility predicate with no floating point.
3. Record the planted value. That value is the reference a heuristic is scored against when the exact optimum is not known.
4. If a trivial baseline already recovers at least 99% of the planted value, mark the instance `too_easy` and drop it from scoring. The drawing's rule is: keep a threshold, and do not train on an instance the obvious algorithm already solves.
5. The seed is `problem.seed()` from `config.yaml`. Do not draw an unseeded seed.

## Project quasi

`src/plant.py` is this procedure for the gamma-quasi-biclique.

`plant(G, p, q, theta)` returns `None` when fewer than `theta` vertices on a side have degree above the opposite planted size. Otherwise it returns a dict:

- `S`, `T`: the planted vertex ids
- `extra_edges`: the edges added inside `S x T`
- `graph`: `G` plus those edges
- `value`: `|E(S, T)|` on that graph
- `too_easy`: true when the degree-threshold baseline recovers at least `too_easy_rho` (0.99) of `value`

The call is written out in `projects/quasi/run.md`. Use that file when the project id is `quasi`. For any other id, implement the five rules above for the formulation in that project's `memory.md`, and document the call in `projects/<id>/run.md`.
