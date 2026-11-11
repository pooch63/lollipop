"""Exact gamma-quasi-biclique oracle (OR-Tools CP-SAT).

Maximise |E(S, T)| subject to the integer quasi-biclique inequalities and
|S|, |T| >= theta. Single-threaded, fixed seed. work_limit is
max_deterministic_time. See DECISIONS.md for the z linking constraint.
"""

from __future__ import annotations

from ortools.sat.python import cp_model

from problem import seed

OPTIMAL = "OPTIMAL"
FEASIBLE = "FEASIBLE"
NONE = "NONE"


def solve(G, p, q, theta, work_limit):
    """Return (S, T, value, status, work).

    S and T are sorted vertex ids. status is OPTIMAL, FEASIBLE, or NONE.
    work is the deterministic time the solver reported.
    """
    p = int(p)
    q = int(q)
    theta = int(theta)
    if q <= 0 or p < 0 or theta < 0:
        raise ValueError("require p >= 0, q > 0, theta >= 0")
    if work_limit < 0:
        raise ValueError("work_limit must be >= 0")

    u_ids = G.u_ids
    v_ids = G.v_ids
    n_u = len(u_ids)
    n_v = len(v_ids)
    if n_u < theta or n_v < theta:
        return [], [], 0, NONE, 0.0

    u_index = {u: i for i, u in enumerate(u_ids)}
    v_index = {v: j for j, v in enumerate(v_ids)}
    # adj bitsets are unnecessary; use membership sets for constraint build.
    nbr_u = [set(G.neighbors_u(u)) for u in u_ids]
    nbr_v = [set(G.neighbors_v(v)) for v in v_ids]

    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x{i}") for i in range(n_u)]
    y = [model.new_bool_var(f"y{j}") for j in range(n_v)]
    z_vars = []
    for i, u in enumerate(u_ids):
        for v in G.neighbors_u(u):
            j = v_index.get(v)
            if j is None:
                continue
            z = model.new_bool_var(f"z{i}_{j}")
            model.add(z <= x[i])
            model.add(z <= y[j])
            # Force z to equal the edge inside (S, T), even on non-optimal feasible points.
            model.add(z >= x[i] + y[j] - 1)
            z_vars.append(z)

    # For each u: sum_v (q*A_uv - p)*y_v >= -p*|V|*(1 - x_u)
    # rewritten as L + p*|V|*(1 - x_u) >= 0.
    for i, u in enumerate(u_ids):
        nbrs = nbr_u[i]
        terms = []
        for j, v in enumerate(v_ids):
            coef = (q - p) if v in nbrs else -p
            if coef != 0:
                terms.append(coef * y[j])
        terms.append((p * n_v) * (1 - x[i]))
        model.add(sum(terms) >= 0)

    for j, v in enumerate(v_ids):
        nbrs = nbr_v[j]
        terms = []
        for i, u in enumerate(u_ids):
            coef = (q - p) if u in nbrs else -p
            if coef != 0:
                terms.append(coef * x[i])
        terms.append((p * n_u) * (1 - y[j]))
        model.add(sum(terms) >= 0)

    model.add(sum(x) >= theta)
    model.add(sum(y) >= theta)
    model.maximize(sum(z_vars) if z_vars else 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_deterministic_time = float(work_limit)
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = int(seed())
    solver.parameters.log_search_progress = False

    status_code = solver.solve(model)
    # OR-Tools 9.15 exposes this as a float attribute, not a method.
    work = float(solver.deterministic_time)

    if status_code == cp_model.OPTIMAL:
        status = OPTIMAL
    elif status_code == cp_model.FEASIBLE:
        status = FEASIBLE
    else:
        return [], [], 0, NONE, work

    S = [u_ids[i] for i in range(n_u) if solver.value(x[i]) == 1]
    T = [v_ids[j] for j in range(n_v) if solver.value(y[j]) == 1]
    val = int(round(solver.objective_value))
    return S, T, val, status, work
