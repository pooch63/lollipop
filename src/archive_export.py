"""Two archive views per tier: best mean rho, and the Pareto front of (rho up, alpha down).

OpenEvolve bins the raw metrics itself. This module reads the programs that
finished a run and writes the two views the report prints.
"""

from __future__ import annotations

import json
from pathlib import Path

from dsl.render import render
from evaluator import program_hash
from problem import ROOT


def pareto_front(programs: list[dict]) -> list[dict]:
    """Keep programs no other program weakly beats on both axes.

    Higher rho is better. Lower alpha_hat is better. A tie on both stays.
    """
    front = []
    for prog in programs:
        rho = prog["rho"]
        alpha = prog["alpha_hat"]
        beaten = False
        for other in programs:
            if other is prog:
                continue
            if other["rho"] >= rho and other["alpha_hat"] <= alpha and (
                other["rho"] > rho or other["alpha_hat"] < alpha
            ):
                beaten = True
                break
        if not beaten:
            front.append(prog)
    front.sort(key=lambda p: (-p["rho"], p["alpha_hat"], p["program_hash"]))
    return front


def _entry(prog, tier, hypothesis_id, run_id) -> dict:
    source = prog["source"]
    try:
        pseudocode = prog.get("pseudocode") or render(source, tier)
    except Exception as exc:
        pseudocode = f"(unrenderable: {exc})"
    return {
        "tier": tier,
        "hypothesis_id": prog.get("hypothesis_id") or hypothesis_id,
        "run_id": prog.get("run_id") or run_id,
        "program_hash": prog.get("program_hash") or program_hash(source),
        "source": source,
        "pseudocode": pseudocode,
        "rho": prog["rho"],
        "alpha_hat": prog["alpha_hat"],
        "class_violation": bool(prog.get("class_violation", False)),
        "per_rung": prog.get("rows") or prog.get("per_rung") or [],
    }


def export_tier(tier: str, programs: list[dict], hypothesis_id: str, run_id: str, root: Path | None = None) -> dict:
    """Write archive/{tier}/best_rho.json and pareto.json. Returns the two views."""
    root = Path(root) if root is not None else ROOT
    dest = root / "archive" / tier
    dest.mkdir(parents=True, exist_ok=True)
    if not programs:
        payload = {"tier": tier, "hypothesis_id": hypothesis_id, "run_id": run_id, "programs": []}
        (dest / "best_rho.json").write_text(json.dumps(payload, indent=2))
        (dest / "pareto.json").write_text(json.dumps(payload, indent=2))
        return {"best": None, "pareto": []}
    ranked = sorted(programs, key=lambda p: (-p["rho"], p["alpha_hat"], p.get("program_hash", "")))
    best = _entry(ranked[0], tier, hypothesis_id, run_id)
    front = [_entry(p, tier, hypothesis_id, run_id) for p in pareto_front(ranked)]
    pool = [_entry(p, tier, hypothesis_id, run_id) for p in ranked]
    (dest / "best_rho.json").write_text(json.dumps(best, indent=2))
    (dest / "pareto.json").write_text(json.dumps({"tier": tier, "run_id": run_id, "front": front}, indent=2))
    (dest / "programs.json").write_text(json.dumps(pool, indent=2))
    return {"best": best, "pareto": front}


def programs_from_database(database) -> list[dict]:
    """Pull source and metrics out of an OpenEvolve ProgramDatabase."""
    out = []
    for program in database.programs.values():
        metrics = program.metrics or {}
        if "rho" not in metrics:
            continue
        artifacts = {}
        if hasattr(database, "get_artifacts"):
            artifacts = database.get_artifacts(program.id) or {}
        rows = []
        raw_rows = artifacts.get("rows")
        if isinstance(raw_rows, str):
            rows = json.loads(raw_rows)
        out.append({
            "source": program.code,
            "rho": float(metrics["rho"]),
            "alpha_hat": float(metrics.get("alpha_hat", 0.0)),
            "class_violation": bool(metrics.get("class_violation", 0)),
            "program_hash": artifacts.get("program_hash"),
            "pseudocode": artifacts.get("pseudocode"),
            "rows": rows,
        })
    return out
