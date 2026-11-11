"""Ledger refusals and hypothesis adjudication."""

from pathlib import Path

from adjudicate import adjudicate
from budget import BudgetRefused, Ledger
from store import connect, log_result, query_hypotheses, seed_hypotheses


def test_reserve_commit_and_refuse(tmp_path):
    ledger = Ledger(tmp_path / "budget.sqlite", total_cpu_seconds=10)
    rid = ledger.reserve("evolver", 4)
    ledger.commit(rid, actual_seconds=3)
    assert ledger.spent_by_role()["evolver"] == 3
    assert ledger.remaining() == 7
    try:
        ledger.reserve("promoter", 8)
        raised = False
    except BudgetRefused:
        raised = True
    assert raised
    assert ledger.refused_by_role()["promoter"] == 1
    # A refusal does not spend the pool.
    rid2 = ledger.reserve("evolver", 7)
    ledger.commit(rid2, actual_seconds=7)
    assert ledger.remaining() == 0


def test_adjudicate_supports_and_refutes(tmp_path):
    conn = connect(tmp_path / "hyp.sqlite")
    seed_hypotheses(conn)
    assert query_hypotheses(conn) == []
    # H2 claims rho >= 0.9. One good cell supports it.
    log_result(conn, "run-a", "H2", "abc", "r1", "9/10", 3, {"rho": 0.95})
    status = adjudicate(conn)
    assert status["H2"] == "supported"
    assert status["H1"] == "untested"
    supported = query_hypotheses(conn, statuses=("supported",))
    assert supported[0]["id"] == "H2"
    # A later bad cell refutes it.
    log_result(conn, "run-a", "H2", "abc", "r2", "9/10", 3, {"rho": 0.2})
    assert adjudicate(conn)["H2"] == "refuted"
    # H3 needs rho_minus_baseline. Logging only rho is inconclusive.
    log_result(conn, "run-b", "H3", "def", "r1", "1/1", 2, {"rho": 1.0})
    assert adjudicate(conn)["H3"] == "inconclusive"


def test_seed_does_not_reset_status(tmp_path):
    conn = connect(tmp_path / "hyp.sqlite")
    seed_hypotheses(conn)
    log_result(conn, "run-a", "H2", "abc", "r1", "9/10", 3, {"rho": 0.99})
    adjudicate(conn)
    seed_hypotheses(conn)
    row = conn.execute("SELECT status FROM hypotheses WHERE id='H2'").fetchone()
    assert row["status"] == "supported"
    assert Path(tmp_path / "hyp.sqlite").exists()
