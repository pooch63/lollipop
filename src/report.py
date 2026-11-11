"""Print the seven sections of the harness report from files on disk."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from problem import ROOT


def _load(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _section(title: str) -> str:
    return f"\n== {title}\n"


def render_report(root: Path | None = None) -> str:
    root = Path(root) if root is not None else ROOT
    parts = []

    parts.append(_section("identity and baseline controls"))
    gate = _load(root / "rungs" / "identity_gate.json")
    if gate is None:
        parts.append("Identity-control gate has not been run.\n")
    elif "sweep" in gate:
        parts.append(gate.get("table", "") + "\n")
        parts.append(f"passed: {gate['passed']} ({gate['reason']})\n")
        parts.append(f"chosen lambda: {gate['lambda']}\n")
        planted = gate.get("planted") or {}
        if planted:
            parts.append(
                f"planted raw rho > 1: {planted['n_raw_above_one']}/{planted['n_planted']} "
                f"({planted['fraction_raw_above_one']:.3f}) at lambda {planted['lambda']}\n"
            )
    else:
        parts.append(
            f"abort: {gate['abort']} ({gate['reason']})\n"
            f"identity mean rho: {gate['identity_rho']:.4f}\n"
            f"baseline mean rho: {gate['baseline_rho']:.4f}\n"
            f"identity alpha: {gate['identity_alpha']}\n"
            f"baseline alpha: {gate['baseline_alpha']}\n"
            f"threshold: {gate['threshold']}  lambda: {gate['lambda']}\n"
        )

    parts.append(_section("best-rho program and Pareto front"))
    for tier in ("L", "N", "Q", "search"):
        best = _load(root / "archive" / tier / "best_rho.json")
        front = _load(root / "archive" / tier / "pareto.json")
        parts.append(f"[{tier}]\n")
        if not best or best.get("programs") == [] or "source" not in best:
            parts.append("  no archived program\n")
            continue
        parts.append(
            f"  best rho={best['rho']:.4f} alpha={best['alpha_hat']:.4f} "
            f"hash={best['program_hash']} hypothesis={best.get('hypothesis_id')} "
            f"run={best.get('run_id')}\n"
        )
        parts.append("  pseudocode:\n")
        for line in str(best.get("pseudocode", "")).splitlines():
            parts.append(f"    {line}\n")
        members = (front or {}).get("front") or []
        parts.append(f"  Pareto front ({len(members)}):\n")
        for member in members:
            parts.append(
                f"    rho={member['rho']:.4f} alpha={member['alpha_hat']:.4f} "
                f"hash={member['program_hash']}\n"
            )

    parts.append(_section("rho and alpha by tier"))
    for tier in ("L", "N", "Q", "search"):
        best = _load(root / "archive" / tier / "best_rho.json")
        if not best or "rho" not in best:
            parts.append(f"{tier}: no run\n")
            continue
        parts.append(f"{tier}: best rho={best['rho']:.4f} alpha_hat={best['alpha_hat']:.4f}\n")

    parts.append(_section("matched reduction controls"))
    parts.append(matched_controls_text(root))

    parts.append(_section("hypotheses"))
    db = root / "hypotheses.sqlite"
    if not db.exists():
        parts.append("Hypothesis store has not been created.\n")
    else:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, tier, status, claim FROM hypotheses ORDER BY id"
        ).fetchall()
        if not rows:
            parts.append("No hypotheses seeded.\n")
        for row in rows:
            parts.append(f"{row['id']} [{row['tier']}] {row['status']}: {row['claim']}\n")
        conn.close()

    parts.append(_section("Kendall tau across held-out rungs"))
    promo = _load(root / "promotion_results.json")
    if promo is None:
        parts.append("Promotion has not been run.\n")
    else:
        for track in promo.get("tracks", []):
            parts.append(
                f"{track['tier']} gamma={track['gamma']} theta={track['theta']} "
                f"survivors={track['walk']['survivors']}\n"
            )
            for pair in track["walk"]["kendall"]:
                parts.append(
                    f"  {pair['left']} -> {pair['right']}: tau={pair['tau']} "
                    f"n_shared={pair['n_shared']} {pair.get('note') or ''}\n"
                )
            for item in track["walk"]["censored"]:
                parts.append(
                    f"  censored {item['program_hash']} at {item['rung']}: {item['reason']}\n"
                )

    parts.append(_section("planted instances marked too easy"))
    refs = _load(root / "rungs" / "references.json")
    if refs is None:
        parts.append("Reference cache has not been built.\n")
    else:
        easy = [
            (key, rec.get("reason"))
            for key, rec in refs.items()
            if rec.get("kind") == "excluded"
        ]
        if not easy:
            parts.append("None.\n")
        for key, reason in sorted(easy):
            parts.append(f"{key}: {reason}\n")

    parts.append(_section("budget spent by role"))
    ledger = root / "budget.sqlite"
    if not ledger.exists():
        parts.append("Ledger has not been created.\n")
    else:
        conn = sqlite3.connect(ledger)
        spent = conn.execute(
            "SELECT role, COALESCE(SUM(actual), 0) FROM reservations "
            "WHERE status='committed' GROUP BY role"
        ).fetchall()
        refused = conn.execute(
            "SELECT role, COUNT(*) FROM reservations WHERE status='refused' GROUP BY role"
        ).fetchall()
        if not spent:
            parts.append("No committed reservations.\n")
        for role, total in spent:
            parts.append(f"{role}: {float(total):.3f}s committed\n")
        for role, count in refused:
            parts.append(f"{role}: {int(count)} refused reservations\n")
        conn.close()
    return "".join(parts)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def score_matched_controls(programs: list[dict], root: Path | None = None) -> list[dict]:
    """Score a random reducer and a degree-top reducer at each program's reduction.

    Both controls are evaluated on the same dev-grid cells the program was
    scored on. Rho uses the evaluator's planted clip.
    """
    from collections import defaultdict

    from controls import control_rng, degree_keep, random_keep
    from evaluator import (
        _graph_for_cell,
        _load as load_rung_graph,
        dev_rungs,
        lift_value,
        raw_rho,
        work_budget,
    )
    from make_rungs import load_rungs

    root = Path(root) if root is not None else ROOT
    refs = _load(root / "rungs" / "references.json") or {}
    rungs = {rung["name"]: rung for rung in dev_rungs(load_rungs(root / "rungs.yaml"))}
    graphs = {}
    degree_cache = {}
    rho_cache = {}
    out = []
    for index, program in enumerate(programs, start=1):
        print(f"controls {index}/{len(programs)} {program.get('program_hash')}", flush=True)
        rows = program.get("per_rung") or []
        own, rand_rhos, deg_rhos = [], [], []
        for row in rows:
            if row.get("reduction") is None or row.get("kind") == "excluded":
                continue
            key = f"{row['rung']}|{row['p']}/{row['q']}|{row['theta']}"
            rec = refs.get(key)
            rung = rungs.get(row["rung"])
            if rec is None or rung is None:
                continue
            if row["rung"] not in graphs:
                graphs[row["rung"]] = load_rung_graph(rung)
            G = _graph_for_cell(graphs[row["rung"]], rec)
            reduction = float(row["reduction"])
            degree_key = (row["rung"], row["p"], row["q"], row["theta"], round(reduction, 5))
            if degree_key not in degree_cache:
                degree_cache[degree_key] = degree_keep(G, reduction)
            keeps = (
                ("random", random_keep(G, reduction, control_rng(
                    program.get("program_hash", ""), row["rung"], row["p"], row["q"], row["theta"]
                ))),
                ("degree", degree_cache[degree_key]),
            )
            for label, keep in keeps:
                cache_key = (label, row["rung"], row["p"], row["q"], row["theta"], tuple(keep[0]), tuple(keep[1]))
                if cache_key in rho_cache:
                    rho = rho_cache[cache_key]
                else:
                    final, _status, _work, _m = lift_value(
                        G, keep[0], keep[1], rec["p"], rec["q"], rec["theta"], work_budget(rec)
                    )
                    raw = 0.0 if final is None else raw_rho(final, rec.get("reference"))
                    rho = min(raw, 1.0) if rec.get("kind") == "planted" else raw
                    rho_cache[cache_key] = rho
                (rand_rhos if label == "random" else deg_rhos).append(rho)
            if row.get("rho") is not None:
                own.append(float(row["rho"]))
        out.append({
            "program_hash": program.get("program_hash"),
            "hypothesis_id": program.get("hypothesis_id"),
            "n_cells": len(rand_rhos),
            "program_rho": _mean(own),
            "random_rho": _mean(rand_rhos),
            "degree_rho": _mean(deg_rhos),
        })
    return out


def matched_controls_text(root: Path) -> str:
    pool_path = root / "archive" / "L" / "programs.json"
    cache_path = root / "archive" / "L" / "matched_controls.json"
    if not pool_path.exists():
        return "No evolved programs to match.\n"
    if cache_path.exists():
        scored = _load(cache_path)
    else:
        programs = _load(pool_path) or []
        if not programs:
            return "No evolved programs to match.\n"
        print(f"scoring matched controls for {len(programs)} programs", flush=True)
        scored = score_matched_controls(programs, root)
        cache_path.write_text(json.dumps(scored, indent=2))
    if not scored:
        return "No evolved programs to match.\n"
    lines = []
    by_h = defaultdict_groups(scored)
    for hid, group in by_h:
        lines.append(
            f"{hid}: n={len(group)} program={_mean([g['program_rho'] for g in group]):.4f} "
            f"random={_mean([g['random_rho'] for g in group]):.4f} "
            f"degree={_mean([g['degree_rho'] for g in group]):.4f}\n"
        )
    best = max(scored, key=lambda item: item["program_rho"])
    lines.append(
        f"best {best['program_hash']} ({best['hypothesis_id']}): "
        f"program={best['program_rho']:.4f} random={best['random_rho']:.4f} "
        f"degree={best['degree_rho']:.4f} over {best['n_cells']} cells\n"
    )
    return "".join(lines)


def defaultdict_groups(scored: list[dict]):
    order = []
    buckets = {}
    for item in scored:
        hid = item.get("hypothesis_id") or "?"
        if hid not in buckets:
            order.append(hid)
            buckets[hid] = []
        buckets[hid].append(item)
    return [(hid, buckets[hid]) for hid in order]


def main() -> None:
    print(render_report())


if __name__ == "__main__":
    main()
