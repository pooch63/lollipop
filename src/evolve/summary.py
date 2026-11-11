"""Summarize the L-tier smoke log. The seed baseline is not an evolved program."""

from __future__ import annotations

import json
from collections import Counter

from dsl.programs import BASELINE_L
from evaluator import program_hash
from evolve.spend import SPEND_PATH
from problem import ROOT, SRC

LOG_PATH = SRC / "evolve" / "smoke_evals.jsonl"
SUMMARY_PATH = SRC / "evolve" / "smoke_summary.json"
CORE_LAMBDA = 0.75


def _core_mean() -> float | None:
    path = ROOT / "rungs" / "identity_gate.json"
    if not path.exists():
        return None
    gate = json.loads(path.read_text())
    for row in gate.get("sweep") or []:
        if abs(float(row["lambda"]) - CORE_LAMBDA) < 1e-9:
            return float(row["core"])
    return None


def _best_stage(records: list[dict]) -> dict:
    stages = {rec["stage"]: rec for rec in records}
    return stages.get("stage2") or stages.get("stage1") or records[-1]


def write_summary() -> str:
    seed = program_hash(BASELINE_L)
    grouped: dict[tuple, list] = {}
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            key = (rec.get("hypothesis_id"), rec.get("program_hash"))
            grouped.setdefault(key, []).append(rec)
    evolved = []
    seed_scores = []
    for (hid, digest), records in grouped.items():
        chosen = _best_stage(records)
        stage1 = next((rec for rec in records if rec["stage"] == "stage1"), chosen)
        item = {
            "hypothesis_id": hid,
            "program_hash": digest,
            "combined_score": chosen.get("combined_score"),
            "alpha_hat": chosen.get("alpha_hat"),
            "class_violation": bool(chosen.get("class_violation")),
            "lint_rejected": bool(stage1.get("lint_rejected")),
            "stage": chosen.get("stage"),
        }
        if digest == seed:
            seed_scores.append(item)
        else:
            evolved.append(item)
    n = len(evolved)
    lint_n = sum(1 for item in evolved if item["lint_rejected"])
    scores = [float(item["combined_score"]) for item in evolved if item["combined_score"] is not None]
    bins = Counter()
    for score in scores:
        if score <= 0:
            bins["0"] += 1
        elif score < 0.2:
            bins["(0, 0.2)"] += 1
        elif score < 0.5:
            bins["[0.2, 0.5)"] += 1
        elif score < 0.716:
            bins["[0.5, 0.716)"] += 1
        elif score <= 1:
            bins["[0.716, 1]"] += 1
        else:
            bins[">1"] += 1
    best = max(evolved, key=lambda item: float(item["combined_score"] or 0), default=None)
    top = sorted(evolved, key=lambda item: (-float(item["combined_score"] or 0), item["program_hash"]))[:5]
    violations = [item["program_hash"] for item in evolved if item["class_violation"]]
    spend = json.loads(SPEND_PATH.read_text()) if SPEND_PATH.exists() else {"dollars": 0.0, "calls": 0}
    core = _core_mean()
    summary = {
        "evolved_programs": n,
        "lint_rejected": lint_n,
        "lint_rejection_rate": (lint_n / n) if n else None,
        "score_bins": dict(bins),
        "best_combined_score": None if best is None else best["combined_score"],
        "core_mean_rho": core,
        "best_minus_core": None if best is None or core is None else best["combined_score"] - core,
        "top": [
            {
                "hypothesis_id": item["hypothesis_id"],
                "program_hash": item["program_hash"],
                "combined_score": item["combined_score"],
                "alpha_hat": item["alpha_hat"],
                "class_violation": item["class_violation"],
            }
            for item in top
        ],
        "class_violations": violations,
        "seed_score": None if not seed_scores else seed_scores[0]["combined_score"],
        "spend": spend,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
    lines = [
        f"evolved programs: {n}",
        f"linter rejection rate: {summary['lint_rejection_rate']}",
        f"score bins: {summary['score_bins']}",
        f"best combined_score: {summary['best_combined_score']} vs core {core}",
        "top programs:",
    ]
    for item in top:
        lines.append(
            f"  {item['hypothesis_id']} {item['program_hash']} "
            f"score={item['combined_score']} alpha={item['alpha_hat']} "
            f"class_violation={item['class_violation']}"
        )
    lines.append(f"class violations: {violations or 'none'}")
    lines.append(
        f"spend: ${float(spend.get('dollars', 0)):.4f} "
        f"calls={spend.get('calls', 0)} "
        f"prompt_tokens={spend.get('prompt_tokens', 0)} "
        f"completion_tokens={spend.get('completion_tokens', 0)}"
    )
    return "\n".join(lines) + "\n"
