"""OpenEvolve cascade for a search program.

Stage 1 is the two smallest dev rungs at gamma 9/10, theta 3.
Stage 2 is the full dev grid. combined_score is mean rho of the pair the
program returns. The CP-SAT solver is not part of this score.

OE_HYPOTHESIS_ID and OE_RUN_ID are optional. OE_STORE selects the sqlite file.
"""

from __future__ import annotations

import json
import os

from openevolve.evaluation_result import EvaluationResult

from evaluator import default_ledger, program_hash
from projects.quasi.heuristics.evaluate import evaluate_search, prepare_dev, stage1_rungs_and_cells
from problem import config
from store import connect, log_result


def _context():
    return (
        os.environ.get("OE_HYPOTHESIS_ID") or None,
        os.environ.get("OE_RUN_ID", "unspecified"),
    )


def _store_path():
    from problem import ROOT
    return os.environ.get("OE_STORE", str(ROOT / "hypotheses.sqlite"))


def _record(metrics, hypothesis_id, run_id):
    if not hypothesis_id:
        return
    conn = connect(_store_path())
    for row in metrics["rows"]:
        if row.get("rho") is None:
            continue
        log_result(
            conn, run_id, hypothesis_id, metrics["program_hash"],
            row["rung"], f"{row['p']}/{row['q']}", row["theta"],
            {
                "rho": row.get("rho"),
                "cost_ratio": row.get("cost_ratio"),
                "alpha_hat": metrics["alpha_hat"],
                "steps": row.get("steps"),
                "final": row.get("final"),
                "target": "search",
            },
        )


def _result(metrics, stage: str) -> EvaluationResult:
    alpha = metrics["alpha_hat"]
    alpha = 0.0 if alpha is None else float(alpha)
    return EvaluationResult(
        metrics={
            "combined_score": float(metrics["combined_score"]),
            "rho": float(metrics["rho"]),
            "alpha_hat": alpha,
            "class_violation": 1.0 if metrics["class_violation"] else 0.0,
            "n_scored": float(metrics["n_scored"]),
        },
        artifacts={
            "stage": stage,
            "target": "search",
            "program_hash": metrics["program_hash"],
            "pseudocode": metrics["pseudocode"],
            "rows": json.dumps(metrics["rows"]),
        },
    )


def _read(program_path: str) -> str:
    with open(program_path) as handle:
        return handle.read()


def _ledger():
    """The shared CPU ledger, or OE_LEDGER when a run is kept off that file."""
    path = os.environ.get("OE_LEDGER")
    if not path:
        return default_ledger()
    from budget import Ledger
    return Ledger(path, float(config()["total_cpu_seconds"]))


def _guard() -> None:
    if os.environ.get("OE_ROLE") == "evolver":
        from evolve.protect import assert_evolver_readonly
        assert_evolver_readonly()


def _apply_kill(metrics) -> None:
    kill = float(config()["rho_kill_threshold"])
    if metrics["combined_score"] < kill:
        metrics["combined_score"] = 0.0
        metrics["rho"] = 0.0


def evaluate_stage1(program_path: str) -> EvaluationResult:
    _guard()
    hypothesis_id, run_id = _context()
    rungs, refs = prepare_dev()
    small, only = stage1_rungs_and_cells(rungs)
    metrics = evaluate_search(
        _read(program_path), small, refs,
        role_ledger=_ledger(), role="evolver", only=only,
    )
    _apply_kill(metrics)
    _record(metrics, hypothesis_id, run_id)
    return _result(metrics, "stage1")


def evaluate_stage2(program_path: str) -> EvaluationResult:
    _guard()
    hypothesis_id, run_id = _context()
    rungs, refs = prepare_dev()
    metrics = evaluate_search(
        _read(program_path), rungs, refs,
        role_ledger=_ledger(), role="evolver",
    )
    _record(metrics, hypothesis_id, run_id)
    return _result(metrics, "stage2")


def evaluate(program_path: str) -> EvaluationResult:
    return evaluate_stage2(program_path)


def program_id_hash(source: str) -> str:
    return program_hash(source)
