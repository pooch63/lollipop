"""Promotion is a script: no LLM. Top-K archive programs, held-out rungs, increasing m.

A program stops on that (gamma, theta) track at its first sandbox timeout, kill-cap
hit, or invalid result. Kendall tau is computed only over programs that produced
a rho on both of a consecutive pair of rungs. Censored programs are listed.
"""

from __future__ import annotations

import json
from pathlib import Path

from scipy.stats import kendalltau

from problem import ROOT


def top_k(programs: list[dict], score, k: int) -> list[dict]:
    ranked = sorted(programs, key=lambda p: (-float(score(p)), p["program_hash"]))
    return ranked[:k]


def cell_mean_rho(program: dict, p: int, q: int, theta: int) -> float:
    rows = [
        r for r in program.get("per_rung", [])
        if r.get("p") == p and r.get("q") == q and r.get("theta") == theta and r.get("rho") is not None
    ]
    if not rows:
        return 0.0
    return sum(r["rho"] for r in rows) / len(rows)


def walk_rungs(programs: list[dict], rung_names: list[str], evaluate_fn) -> dict:
    """evaluate_fn(program, rung_name) -> {rho} or {error: timeout|kill|invalid}."""
    alive = list(programs)
    per_rung = []
    censored = []
    for rung in rung_names:
        ranking = []
        still = []
        for prog in alive:
            row = evaluate_fn(prog, rung)
            reason = row.get("error")
            if reason in ("timeout", "kill", "invalid") or row.get("censored"):
                censored.append({
                    "program_hash": prog["program_hash"],
                    "rung": rung,
                    "reason": reason or row.get("reason") or "invalid",
                })
                continue
            ranking.append({"program_hash": prog["program_hash"], "rho": float(row["rho"])})
            still.append(prog)
        ranking.sort(key=lambda item: (-item["rho"], item["program_hash"]))
        per_rung.append({"rung": rung, "ranking": ranking})
        alive = still
    return {
        "per_rung": per_rung,
        "kendall": _kendall(per_rung),
        "censored": censored,
        "survivors": [p["program_hash"] for p in alive],
    }


def _kendall(per_rung: list[dict]) -> list[dict]:
    out = []
    for left, right in zip(per_rung, per_rung[1:]):
        right_rho = {item["program_hash"]: item["rho"] for item in right["ranking"]}
        shared = [item for item in left["ranking"] if item["program_hash"] in right_rho]
        entry = {
            "left": left["rung"],
            "right": right["rung"],
            "n_shared": len(shared),
            "tau": None,
            "pvalue": None,
            "note": None,
        }
        if len(shared) < 2:
            entry["note"] = "fewer than 2 programs survived both rungs; tau is undefined"
            out.append(entry)
            continue
        xs = [item["rho"] for item in shared]
        ys = [right_rho[item["program_hash"]] for item in shared]
        if len(set(xs)) == 1 and len(set(ys)) == 1:
            entry["tau"] = 1.0
            entry["note"] = "all shared programs tied; tau reported as 1"
            out.append(entry)
            continue
        result = kendalltau(xs, ys)
        entry["tau"] = None if result.correlation != result.correlation else float(result.correlation)
        entry["pvalue"] = None if result.pvalue != result.pvalue else float(result.pvalue)
        out.append(entry)
    return out


def load_pool(tier: str, root: Path | None = None) -> list[dict]:
    root = root or ROOT
    path = root / "archive" / tier / "programs.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def save_promotion(payload: dict, root: Path | None = None) -> Path:
    root = root or ROOT
    path = root / "promotion_results.json"
    path.write_text(json.dumps(payload, indent=2))
    return path
