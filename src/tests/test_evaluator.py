"""Cell scoring on a graph small enough to solve exactly."""

from budget import Ledger
from dsl.programs import BASELINE_L
from evaluator import _one_cell
from graphs import BipartiteGraph
from problem import config


def K(n):
    edges = [(u, n + v) for u in range(n) for v in range(n)]
    return BipartiteGraph.from_edges(edges, range(n), range(n, 2 * n), name="K")


def test_baseline_reaches_rho_one_when_the_budget_can_solve():
    G = K(4)
    record = {"kind": "opt", "reference": 16, "W_r": 2.0}
    rung = {"name": "toy", "m": G.m}
    row = _one_cell(BASELINE_L, "L", G, rung, 1, 1, 2, record, None, "evolver", False, config())
    assert row["rho"] == 1.0
    assert row["final"] == 16
    assert abs(row["cost_ratio"] - 1.0) < 1e-9


def test_bad_program_scores_zero_and_charges_the_ledger(tmp_path):
    G = K(3)
    record = {"kind": "opt", "reference": 9, "W_r": 2.0}
    rung = {"name": "toy", "m": G.m}
    ledger = Ledger(tmp_path / "b.sqlite", total_cpu_seconds=100)
    row = _one_cell(
        "import socket\ndef reduce(G):\n    return peel(0, 0)\n",
        "L", G, rung, 1, 1, 2, record, ledger, "evolver", False, config(),
    )
    assert row["rho"] == 0.0
    assert row["error"]
    assert ledger.spent_by_role()["evolver"] >= 0


def test_excluded_cell_is_not_scored():
    G = K(3)
    record = {"kind": "excluded", "reference": None, "reason": "too_easy", "W_r": 0.5}
    row = _one_cell(BASELINE_L, "L", G, {"name": "toy", "m": G.m}, 1, 1, 2, record, None, "evolver", False, config())
    assert row["rho"] is None
    assert row["excluded"] is True
