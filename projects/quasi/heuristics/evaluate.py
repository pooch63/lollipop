"""Score a search program by the quasi-biclique it returns.

The solver is not called. Rho is the checker edge count divided by the same
reference the reduction evaluator uses. A nonempty pair that fails the
checker scores 0. An empty pair scores as value 0.
"""

from __future__ import annotations

import time
from pathlib import Path

from checker import is_valid, value
from dsl.errors import ProgramError
from evaluator import (
    _class_violation,
    _graph_for_cell,
    dev_rungs,
    ensure_references,
    program_hash,
    raw_rho,
    stage1_spec,
)
from projects.quasi.heuristics.runtime import execute
from projects.quasi.heuristics.sandbox import run as sandbox_run
from problem import ROOT, cells, config

INITIAL_PATH = Path(__file__).resolve().parent / "initial_search.py"


def initial_source() -> str:
    return INITIAL_PATH.read_text()


def score_one(source: str, G, p: int, q: int, theta: int, reference, *, kind: str = "opt", use_sandbox: bool = True, wall_seconds: float | None = None, step_limit: int | None = None) -> dict:
    """Score `source` on one graph. `reference` is the unreduced optimum or plant."""
    denom = G.n_u + G.n_v + G.m
    try:
        if use_sandbox:
            out = sandbox_run(
                source, G, p, q, theta,
                wall_seconds=wall_seconds, step_limit=step_limit,
            )
            if not out["ok"]:
                return _fail(out.get("error") or "search failed")
            S, T, steps = out["S"], out["T"], int(out.get("steps") or 0)
        else:
            S, T, steps = execute(source, G, p, q, theta, step_limit_value=step_limit)
    except ProgramError as exc:
        return _fail(str(exc))
    except Exception as exc:
        return _fail(f"{type(exc).__name__}: {exc}")
    row = _score_pair(G, S, T, p, q, theta, reference, kind, steps, denom)
    return row


def _fail(error: str) -> dict:
    return {
        "rho": 0.0, "rho_raw": 0.0, "final": None, "steps": 0,
        "cost_ratio": None, "error": error,
    }


def _score_pair(G, S, T, p, q, theta, reference, kind, steps, denom) -> dict:
    cost_ratio = (steps / denom) if denom else None
    base = {"steps": steps, "cost_ratio": cost_ratio, "error": None}
    if not S and not T:
        rho_raw = raw_rho(0, reference)
        rho = min(rho_raw, 1.0) if kind == "planted" else rho_raw
        base.update({"rho": rho, "rho_raw": rho_raw, "final": 0})
        return base
    u_ids = set(G.u_ids)
    v_ids = set(G.v_ids)
    if any(u not in u_ids for u in S) or any(v not in v_ids for v in T):
        base.update({"rho": 0.0, "rho_raw": 0.0, "final": None, "error": "unknown vertex"})
        return base
    try:
        ok = is_valid(G, S, T, p, q, theta)
    except Exception as exc:
        base.update({"rho": 0.0, "rho_raw": 0.0, "final": None, "error": f"{type(exc).__name__}: {exc}"})
        return base
    if not ok:
        base.update({"rho": 0.0, "rho_raw": 0.0, "final": None, "error": "checker rejected the pair"})
        return base
    final = value(G, S, T)
    rho_raw = raw_rho(final, reference)
    rho = min(rho_raw, 1.0) if kind == "planted" else rho_raw
    base.update({"rho": rho, "rho_raw": rho_raw, "final": final})
    return base


def evaluate_search(source: str, rungs, refs, *, role_ledger=None, role: str = "evolver", use_sandbox: bool = True, only=None):
    """Mean rho over the requested cells. Excluded cells are recorded and not averaged."""
    cfg = config()
    per_rows = []
    rhos = []
    graphs = {}
    for rung in rungs:
        for p, q, theta in cells():
            if only is not None and (rung["name"], p, q, theta) not in only:
                continue
            key = f"{rung['name']}|{p}/{q}|{theta}"
            record = refs[key]
            if rung["name"] not in graphs:
                graphs[rung["name"]] = _load_rung(rung)
            G = _graph_for_cell(graphs[rung["name"]], record)
            row = _one_cell(
                source, G, rung, p, q, theta, record, role_ledger, role, use_sandbox, cfg,
            )
            per_rows.append(row)
            print(
                f"  {rung['name']} {p}/{q} t={theta} rho={row.get('rho')} kind={record['kind']}",
                flush=True,
            )
            if record["kind"] != "excluded" and row.get("rho") is not None:
                rhos.append(row["rho"])
    combined = sum(rhos) / len(rhos) if rhos else 0.0
    cost_ratios = [row["cost_ratio"] for row in per_rows if row.get("cost_ratio") is not None]
    alpha = max(cost_ratios) if cost_ratios else 0.0
    flagged, slope, pvalue = _class_violation(per_rows, float(cfg["kappa"]))
    return {
        "combined_score": combined,
        "rho": combined,
        "alpha_hat": alpha,
        "class_violation": flagged,
        "slope": slope,
        "slope_pvalue": pvalue,
        "n_scored": len(rhos),
        "program_hash": program_hash(source),
        "pseudocode": source,
        "rows": per_rows,
    }


def _load_rung(entry):
    from pathlib import Path

    from make_rungs import load_graph

    path = entry["graph"]
    if not Path(path).is_absolute():
        path = ROOT / path
    return load_graph(path, name=entry["name"])


def _one_cell(source, G, rung, p, q, theta, record, ledger, role, use_sandbox, cfg):
    base = {
        "rung": rung["name"], "m": G.m, "p": p, "q": q, "theta": theta,
        "kind": record["kind"], "reference": record.get("reference"),
    }
    if record["kind"] == "excluded":
        base.update({"rho": None, "excluded": True, "reason": record.get("reason"), "cost_ratio": None})
        return base
    cpu = float(cfg["cpu_seconds_per_eval"])
    rid = None
    started = time.perf_counter()
    if ledger is not None:
        try:
            rid = ledger.reserve(role, cpu)
        except Exception as exc:
            base.update({"rho": 0.0, "error": str(exc), "cost_ratio": None})
            return base
    try:
        scored = score_one(
            source, G, p, q, theta, record.get("reference"),
            kind=record["kind"], use_sandbox=use_sandbox,
        )
        base.update(scored)
        return base
    finally:
        if rid is not None:
            ledger.commit(rid, actual_seconds=time.perf_counter() - started)


def stage1_rungs_and_cells(rungs=None):
    rungs = dev_rungs(rungs)
    only = stage1_spec(rungs)
    small = [rung for rung in rungs if rung["name"] in {name for name, *_rest in only}]
    return small, only


def prepare_dev(rungs=None):
    rungs = dev_rungs(rungs)
    return rungs, ensure_references(rungs)
