# CP-SAT solver

The solver for this formulation is one module, `solvers/cpsat.py`, imported as `projects.quasi.solvers`.

Public names:

- `solve(G, p, q, theta, work_limit) -> (S, T, value, status, work)`
- `OPTIMAL`, `FEASIBLE`, `NONE`

`S` and `T` are sorted vertex ids. `value` is \(|E(S, T)|\). `status` is one of the three names above. `work` is the solver's deterministic time. `work_limit` is passed straight through as `max_deterministic_time`.

Build the model from `G.u_ids`, `G.v_ids`, and `G.neighbors_u` only.

- A Boolean \(x_u\) for each \(u \in U\), and a Boolean \(y_v\) for each \(v \in V\).
- A Boolean \(z_{uv}\) for each existing edge. Link it with \(z \le x\), \(z \le y\), and \(z \ge x + y - 1\), so a feasible objective equals \(|E(S, T)|\) and not only the optimum.
- Membership, with no floating point. For each \(u\), writing \(A_{uv}\) for the 0/1 adjacency and \(n_V = |V|\):

\[
\sum_v (q A_{uv} - p)\, y_v + p \cdot n_V \cdot (1 - x_u) \ge 0.
\]

The inequality for each \(v\) swaps the sides. Then \(\sum x \ge \theta\) and \(\sum y \ge \theta\). Maximize \(\sum z\).

One search worker. `random_seed` comes from `problem.seed()`. Leave the search log off.

If \(|U| < \theta\) or \(|V| < \theta\), return `([], [], 0, NONE, 0.0)` and do not search. Any status other than optimal or feasible returns `([], [], 0, NONE, work)` with the deterministic time the solver reported.

The reduction harness and this project's search both import `solve` from `projects.quasi.solvers`. A search program is scored by the checker.
