"""OpenEvolve 0.4.1 cascade evaluator.

Stage 1: the two smallest dev rungs at gamma 9/10, theta 3.
Stage 2: the full dev grid. combined_score is mean rho.

Cascade calls are `evaluate_stage1(program_path)` with no extra arguments, so
the tier, hypothesis id, and run id come from the environment:
OE_TIER, OE_HYPOTHESIS_ID, OE_RUN_ID.
"""

from __future__ import annotations

import json
import os

from openevolve.evaluation_result import EvaluationResult

from evaluator import (
    default_ledger,
    dev_rungs,
    ensure_references,
    evaluate_source,
    program_hash,
    stage1_spec,
)
from problem import config
from store import connect, log_result


def _context():
    return (
        os.environ.get("OE_TIER", "L"),
        os.environ.get("OE_HYPOTHESIS_ID") or None,
        os.environ.get("OE_RUN_ID", "unspecified"),
    )


def _store_path():
    from problem import ROOT
    return os.environ.get("OE_STORE", str(ROOT / "hypotheses.sqlite"))


def _record(metrics, tier, hypothesis_id, run_id):
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
                "reduction": row.get("reduction"),
                "cost_ratio": row.get("cost_ratio"),
                "alpha_hat": metrics["alpha_hat"],
                "tier": tier,
            },
        )


def _result(metrics, stage: str) -> EvaluationResult:
    score = float(metrics["combined_score"])
    alpha = metrics["alpha_hat"]
    alpha = 0.0 if alpha is None else float(alpha)
    return EvaluationResult(
        metrics={
            "combined_score": score,
            "rho": float(metrics["rho"]),
            "alpha_hat": alpha,
            "class_violation": 1.0 if metrics["class_violation"] else 0.0,
            "n_scored": float(metrics["n_scored"]),
        },
        artifacts={
            "stage": stage,
            "program_hash": metrics["program_hash"],
            "pseudocode": metrics["pseudocode"],
            "rows": json.dumps(metrics["rows"]),
        },
    )


def _read(program_path: str) -> str:
    with open(program_path) as f:
        return f.read()


def _smoke_log(stage: str, metrics: dict, hypothesis_id, run_id) -> None:
    path = os.environ.get("OE_SMOKE_LOG")
    if not path:
        return
    rows = metrics.get("rows") or []
    attempted = [row for row in rows if row.get("kind") != "excluded"]
    lint_rejected = bool(attempted) and all(
        str(row.get("error") or "").startswith("lint:") for row in attempted
    )
    record = {
        "stage": stage,
        "hypothesis_id": hypothesis_id,
        "run_id": run_id,
        "program_hash": metrics.get("program_hash"),
        "combined_score": metrics.get("combined_score"),
        "alpha_hat": metrics.get("alpha_hat"),
        "class_violation": bool(metrics.get("class_violation")),
        "lint_rejected": lint_rejected,
        "n_scored": metrics.get("n_scored"),
    }
    with open(path, "a") as handle:
        handle.write(json.dumps(record) + "\n")


def _guard() -> None:
    if os.environ.get("OE_ROLE") == "evolver":
        from evolve.protect import assert_evolver_readonly
        assert_evolver_readonly()


def evaluate_stage1(program_path: str) -> EvaluationResult:
    _guard()
    tier, hypothesis_id, run_id = _context()
    rungs = dev_rungs()
    refs = ensure_references(rungs)
    only = stage1_spec(rungs)
    small = [r for r in rungs if r["name"] in {name for name, *_rest in only}]
    metrics = evaluate_source(
        _read(program_path), tier, small, refs,
        role_ledger=default_ledger(), role="evolver", only=only,
    )
    kill = float(config()["rho_kill_threshold"])
    if metrics["combined_score"] < kill:
        metrics["combined_score"] = 0.0
        metrics["rho"] = 0.0
    _record(metrics, tier, hypothesis_id, run_id)
    _smoke_log("stage1", metrics, hypothesis_id, run_id)
    return _result(metrics, "stage1")


def evaluate_stage2(program_path: str) -> EvaluationResult:
    _guard()
    tier, hypothesis_id, run_id = _context()
    rungs = dev_rungs()
    refs = ensure_references(rungs)
    metrics = evaluate_source(
        _read(program_path), tier, rungs, refs,
        role_ledger=default_ledger(), role="evolver",
    )
    _record(metrics, tier, hypothesis_id, run_id)
    _smoke_log("stage2", metrics, hypothesis_id, run_id)
    return _result(metrics, "stage2")


def evaluate(program_path: str) -> EvaluationResult:
    """Direct evaluation is the full dev grid. Cascade uses the stage functions."""
    return evaluate_stage2(program_path)


def program_id_hash(source: str) -> str:
    return program_hash(source)
