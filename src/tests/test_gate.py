"""Proven-cell gate rule, solver budgets, and the oracle reducer."""

from evaluator import (
    choose_lambda,
    clip01,
    gate_passes,
    lift_value,
    raw_rho,
    work_budget,
)
from graphs import BipartiteGraph
from projects.quasi.solvers import solve
from problem import config


def K(n):
    edges = [(u, n + v) for u in range(n) for v in range(n)]
    return BipartiteGraph.from_edges(edges, range(n), range(n, 2 * n), name="K")


def test_gate_passes_only_inside_the_window():
    cfg = config()
    assert gate_passes(0.5, 0.6, 1.0, 0.7, cfg)
    assert gate_passes(0.2, 0.2, 0.95, 0.5, cfg)
    assert not gate_passes(0.19, 0.5, 1.0, 1.0, cfg)
    assert not gate_passes(0.91, 1.0, 1.0, 1.0, cfg)
    assert not gate_passes(0.5, 0.4, 1.0, 1.0, cfg)
    assert not gate_passes(0.5, 0.6, 0.94, 1.0, cfg)
    assert not gate_passes(0.5, 0.6, 1.0, 0.49, cfg)


def test_choose_lambda_prefers_identity_near_one_half():
    rows = [
        {"lambda": 0.2, "identity": 0.3, "pass": True},
        {"lambda": 0.5, "identity": 0.55, "pass": True},
        {"lambda": 1.0, "identity": 0.5, "pass": False},
    ]
    assert choose_lambda(rows)["lambda"] == 0.5
    tied = [
        {"lambda": 0.3, "identity": 0.4, "pass": True},
        {"lambda": 0.1, "identity": 0.6, "pass": True},
    ]
    assert choose_lambda(tied)["lambda"] == 0.1
    assert choose_lambda([{"lambda": 0.05, "identity": 0.0, "pass": False}]) is None


def test_budgets_scale_with_lambda_and_rho_clips():
    proven = {"kind": "opt", "proof_work": 2.0}
    assert abs(work_budget(proven, 0.25) - 0.5) < 1e-12
    planted = {"kind": "planted", "unreduced_work": 8.0}
    assert abs(work_budget(planted, 0.25) - 2.0) < 1e-12
    assert clip01(1.4) == 1.0
    assert clip01(-0.2) == 0.0
    assert raw_rho(12, 4) == 3.0


def test_oracle_reducer_recovers_the_proven_optimum():
    G = K(4)
    S, T, val, status, _work = solve(G, 1, 1, 2, 2.0)
    assert status == "OPTIMAL"
    assert val == 16
    final, lift_status, _work, _m = lift_value(G, S, T, 1, 1, 2, 2.0)
    assert lift_status == "OPTIMAL"
    assert final == 16
    assert clip01(raw_rho(final, val)) == 1.0
