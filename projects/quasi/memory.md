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
