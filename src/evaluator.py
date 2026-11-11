"""Evaluate one reduction program on the dev ladder.

Cascade stage 1 is the two smallest dev rungs at gamma=9/10, theta=3.
Stage 2 is the full dev grid. combined_score is mean rho over scored cells.
A cell whose planted instance is too easy is left out of that mean.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

from checker import is_valid, value
from dsl.programs import BASELINE_L
from dsl.render import render
from dsl.runtime import execute, f_tier, masks_to_ids
from dsl.sandbox import run as sandbox_run
from extend import extend
from make_rungs import load_graph, load_rungs
from projects.quasi.solvers import FEASIBLE, NONE, OPTIMAL, solve
from plant import plant
from problem import ROOT, cells, config, write_lambda

REF_PATH = ROOT / "rungs" / "references.json"


def program_hash(source: str) -> str:
    return hashlib.sha256(source.encode()).hexdigest()[:16]


def dev_rungs(rungs=None):
    rungs = rungs if rungs is not None else load_rungs()
    return sorted((r for r in rungs if r["split"] == "dev"), key=lambda r: (r["m"], r["name"]))


def _load(entry):
    path = entry["graph"]
    if not Path(path).is_absolute():
        path = ROOT / path
    return load_graph(path, name=entry["name"])


def _cell_key(rung, p, q, theta) -> str:
    return f"{rung['name']}|{p}/{q}|{theta}"


def ensure_references(rungs=None, force: bool = False) -> dict:
    """Prove OPT or plant a lower bound for every dev cell. Cached on disk."""
    cfg = config()
    rungs = dev_rungs(rungs)
    cache = {}
    if REF_PATH.exists() and not force:
        cache = json.loads(REF_PATH.read_text())
    limit = float(cfg["oracle_work_limit"])
    changed = False
    for rung in rungs:
        G = None
        for p, q, theta in cells():
            key = _cell_key(rung, p, q, theta)
            # The proof does not depend on lambda. W_r is applied later.
            if key in cache and cache[key].get("limit") == limit:
                continue
            if G is None:
                print(f"reference {rung['name']}", flush=True)
                G = _load(rung)
            S, T, val, status, work = solve(G, p, q, theta, limit)
            if status == OPTIMAL:
                record = {
                    "kind": "opt", "reference": val, "proof_work": work,
                    "opt_S": S, "opt_T": T, "too_easy": False,
                }
            elif status == NONE and work <= 1e-6:
                # CP-SAT closed the model without searching: there is no solution.
                record = {
                    "kind": "opt", "reference": 0, "proof_work": work,
                    "opt_S": [], "opt_T": [], "too_easy": False,
                }
            else:
                planted = plant(G, p, q, theta)
                if planted is None or planted["too_easy"]:
                    record = {
                        "kind": "excluded", "reference": None, "proof_work": work,
                        "too_easy": True,
                        "reason": "unplantable" if planted is None else "too_easy",
                        "planted_value": None if planted is None else planted["value"],
                    }
                else:
                    record = {
                        "kind": "planted", "reference": planted["value"], "proof_work": work,
                        "too_easy": False,
                        "extra_edges": planted["extra_edges"],
                        "planted_S": planted["S"], "planted_T": planted["T"],
                    }
            record.update({"limit": limit, "status": status, "p": p, "q": q, "theta": theta, "rung": rung["name"]})
            cache[key] = record
            changed = True
            REF_PATH.parent.mkdir(parents=True, exist_ok=True)
            REF_PATH.write_text(json.dumps(cache))
            print(f"  {p}/{q} t={theta} {record['kind']} ref={record['reference']}", flush=True)
    if changed:
        REF_PATH.parent.mkdir(parents=True, exist_ok=True)
        REF_PATH.write_text(json.dumps(cache))
    return cache


WR_FLOOR = 1e-4


def work_budget(record, lam=None) -> float:
    """Deterministic solver budget for one cell at this lambda.

    Proven cells use the proof time. Planted cells use the long-cap time
    measured on the unreduced planted graph. Records that only carry a
    precomputed W_r (unit tests) keep that budget.
    """
    if lam is None:
        lam = float(config()["lambda"])
    lam = float(lam)
    if record.get("kind") == "opt" and "proof_work" in record:
        return max(lam * float(record["proof_work"]), WR_FLOOR)
    if record.get("kind") == "planted" and record.get("unreduced_work") is not None:
        return max(lam * float(record["unreduced_work"]), WR_FLOOR)
    return float(record["W_r"])


def clip01(rho: float) -> float:
    if rho < 0.0:
        return 0.0
    if rho > 1.0:
        return 1.0
    return float(rho)


def raw_rho(final: float, reference) -> float:
    if reference is None:
        return 0.0
    if reference == 0:
        return 1.0 if final == 0 else 0.0
    return final / reference


def _graph_for_cell(G, record):
    """Planted cells are scored on the graph with the extra edges."""
    if record["kind"] == "planted" and record.get("extra_edges"):
        return G.with_edges([tuple(e) for e in record["extra_edges"]])
    return G


def evaluate_source(source: str, tier: str, rungs, refs, *, role_ledger=None, role="evolver", use_sandbox=True, only=None):
    """Score `source` on the requested cells.

    only: optional list of (rung, p, q, theta). Default is every cell in refs
    for these rungs, skipping excluded ones for the mean but recording them.
    """
    cfg = config()
    per_rows = []
    rhos = []
    graphs = {}
    for rung in rungs:
        for p, q, theta in cells():
            if only is not None and (rung["name"], p, q, theta) not in only:
                continue
            key = _cell_key(rung, p, q, theta)
            record = refs[key]
            if rung["name"] not in graphs:
                graphs[rung["name"]] = _load(rung)
            G = _graph_for_cell(graphs[rung["name"]], record)
            row = _one_cell(source, tier, G, rung, p, q, theta, record, role_ledger, role, use_sandbox, cfg)
            per_rows.append(row)
            print(
                f"  {rung['name']} {p}/{q} t={theta} rho={row.get('rho')} "
                f"kind={record['kind']}",
                flush=True,
            )
            if record["kind"] != "excluded" and row.get("rho") is not None:
                rhos.append(row["rho"])
    combined = sum(rhos) / len(rhos) if rhos else 0.0
    cost_ratios = [r["cost_ratio"] for r in per_rows if r.get("cost_ratio") is not None]
    alpha = max(cost_ratios) if cost_ratios else None
    flagged, slope, pvalue = _class_violation(per_rows, float(cfg["kappa"]))
    return {
        "combined_score": combined,
        "rho": combined,
        "alpha_hat": alpha if alpha is not None else 0.0,
        "class_violation": flagged,
        "slope": slope,
        "slope_pvalue": pvalue,
        "n_scored": len(rhos),
        "program_hash": program_hash(source),
        "pseudocode": _safe_render(source, tier),
        "rows": per_rows,
    }


def _safe_render(source, tier):
    try:
        return render(source, tier)
    except Exception as exc:
        return f"(unrenderable: {exc})"


def _one_cell(source, tier, G, rung, p, q, theta, record, ledger, role, use_sandbox, cfg):
    base = {
        "rung": rung["name"], "m": G.m, "p": p, "q": q, "theta": theta,
        "kind": record["kind"], "reference": record.get("reference"),
    }
    if record["kind"] == "excluded":
        base.update({"rho": None, "excluded": True, "reason": record.get("reason")})
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
        return _run_cell(source, tier, G, p, q, theta, record, base, use_sandbox)
    except Exception as exc:
        base.update({"rho": 0.0, "error": f"{type(exc).__name__}: {exc}", "cost_ratio": None})
        return base
    finally:
        if rid is not None:
            ledger.commit(rid, actual_seconds=time.perf_counter() - started)


def _run_cell(source, tier, G, p, q, theta, record, base, use_sandbox):
    if use_sandbox:
        out = sandbox_run(source, G, p, q, theta, tier)
    else:
        try:
            keep_u, keep_v, cost = execute(source, G, p, q, theta, tier)
            out = {"ok": True, "keep_u": keep_u, "keep_v": keep_v, "cost": cost, "error": None}
        except Exception as exc:
            out = {"ok": False, "cost": 0, "error": str(exc)}
    if not out["ok"]:
        base.update({"rho": 0.0, "error": out["error"], "cost_ratio": None, "reduction": None})
        return base
    keep_u, keep_v = masks_to_ids(G, out["keep_u"], out["keep_v"])
    budget = work_budget(record)
    final, status, work, reduced_m = lift_value(G, keep_u, keep_v, p, q, theta, budget)
    if final is None:
        base.update({"rho": 0.0, "rho_raw": 0.0, "error": "lifted solution failed checker", "cost_ratio": None})
        return base
    rho_raw = raw_rho(final, record.get("reference"))
    rho = min(rho_raw, 1.0) if record.get("kind") == "planted" else rho_raw
    denom = f_tier(G, tier)
    cost_ratio = (out["cost"] / denom) if denom else None
    reduction = (reduced_m / G.m) if G.m else 0.0
    work_ratio = (work / budget) if budget else None
    base.update({
        "rho": rho, "rho_raw": rho_raw, "final": final, "reduction": reduction,
        "cost": out["cost"], "cost_ratio": cost_ratio,
        "solver_status": status, "solver_work": work, "solver_work_ratio": work_ratio,
        "reduced_m": reduced_m, "W_r": budget,
    })
    return base


def lift_value(G, keep_u, keep_v, p, q, theta, budget):
    """Solve the induced subgraph and extend on G.

    Returns (final value, status, work, reduced edge count). final is None
    when the lifted pair fails the checker.
    """
    reduced = G if _keeps_all(G, keep_u, keep_v) else G.induced(keep_u, keep_v)
    solved_S, solved_T, _val, status, work = solve(reduced, p, q, theta, budget)
    if status in (OPTIMAL, FEASIBLE) and solved_S and solved_T:
        S2, T2 = extend(G, solved_S, solved_T, p, q, theta)
        if not is_valid(G, S2, T2, p, q, theta):
            return None, status, work, reduced.m
        return value(G, S2, T2), status, work, reduced.m
    return 0, status, work, reduced.m


def _keeps_all(G, keep_u, keep_v) -> bool:
    return len(keep_u) == G.n_u and len(keep_v) == G.n_v


def _class_violation(rows, kappa: float):
    pts = [(r["m"], r["cost_ratio"]) for r in rows if r.get("cost_ratio") is not None and r["m"] > 1]
    if len(pts) < 3:
        return False, None, None
    xs = [math.log(m) for m, _c in pts]
    ys = [c for _m, c in pts]
    if len(set(xs)) < 2:
        return False, None, None
    from scipy.stats import linregress
    fit = linregress(xs, ys)
    flag = bool(fit.slope > 0 and fit.pvalue < kappa)
    return flag, float(fit.slope), float(fit.pvalue)


def stage1_spec(rungs):
    ordered = dev_rungs(rungs)
    names = [r["name"] for r in ordered[:2]]
    return {(name, 9, 10, 3) for name in names}


def default_ledger():
    from budget import Ledger
    total = float(config()["total_cpu_seconds"])
    return Ledger(ROOT / "budget.sqlite", total)


def gate_passes(identity: float, core: float, oracle: float, nonzero: float, cfg=None) -> bool:
    """Proven-cell rule. Rho values are already clipped to [0, 1]."""
    cfg = cfg if cfg is not None else config()
    return (
        float(cfg["identity_rho_low"]) <= identity <= float(cfg["identity_rho_high"])
        and nonzero >= float(cfg["identity_nonzero_fraction"])
        and core >= identity
        and oracle >= float(cfg["oracle_reducer_rho"])
    )


def choose_lambda(rows: list[dict]):
    """Passing lambda closest to identity mean 0.5. Ties keep the smaller lambda."""
    passing = [row for row in rows if row["pass"]]
    if not passing:
        return None
    return min(passing, key=lambda row: (abs(row["identity"] - 0.5), row["lambda"]))


def _save_refs(cache: dict) -> None:
    REF_PATH.parent.mkdir(parents=True, exist_ok=True)
    REF_PATH.write_text(json.dumps(cache))


def backfill_optima(refs, rungs) -> None:
    """Store the proven (S, T) on cache records that predate the oracle reducer."""
    by_name = {rung["name"]: rung for rung in rungs}
    pending: dict[str, list] = {}
    for rec in refs.values():
        if rec.get("kind") == "opt" and "opt_S" not in rec:
            pending.setdefault(rec["rung"], []).append(rec)
    if not pending:
        return
    limit = float(config()["oracle_work_limit"])
    for name, records in pending.items():
        print(f"optima {name} ({len(records)} cells)", flush=True)
        G = _load(by_name[name])
        for rec in records:
            S, T, val, status, work = solve(G, rec["p"], rec["q"], rec["theta"], limit)
            if status != OPTIMAL:
                raise RuntimeError(f"{name} {rec['p']}/{rec['q']} t={rec['theta']} was cached as proven but re-solved as {status}")
            rec["opt_S"] = S
            rec["opt_T"] = T
            rec["reference"] = val
            rec["proof_work"] = work
    _save_refs(refs)


def backfill_planted_work(refs, rungs) -> None:
    """Time CP-SAT on each unreduced planted graph under the long fixed cap."""
    by_name = {rung["name"]: rung for rung in rungs}
    pending: dict[str, list] = {}
    for rec in refs.values():
        if rec.get("kind") == "planted" and rec.get("unreduced_work") is None:
            pending.setdefault(rec["rung"], []).append(rec)
    if not pending:
        return
    cap = float(config()["planted_proof_cap"])
    graphs = {}
    for name, records in pending.items():
        print(f"planted work {name} ({len(records)} cells, cap {cap})", flush=True)
        if name not in graphs:
            graphs[name] = _load(by_name[name])
        G = graphs[name]
        for rec in records:
            planted = _graph_for_cell(G, rec)
            _S, _T, _val, status, work = solve(planted, rec["p"], rec["q"], rec["theta"], cap)
            rec["unreduced_work"] = work
            rec["unreduced_status"] = status
            print(f"  {rec['p']}/{rec['q']} t={rec['theta']} {status} work={work:.4f}", flush=True)
            _save_refs(refs)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _prepare_proven(rungs, refs) -> list[dict]:
    """One entry per proven cell, with the three reductions already built."""
    prepared = []
    for rung in rungs:
        records = [
            rec for rec in refs.values()
            if rec.get("rung") == rung["name"] and rec.get("kind") == "opt"
        ]
        if not records:
            continue
        G = _load(rung)
        print(f"reductions {rung['name']}", flush=True)
        for rec in records:
            p, q, theta = rec["p"], rec["q"], rec["theta"]
            core_u, core_v, _cost = execute(BASELINE_L, G, p, q, theta, "L")
            core_ids = masks_to_ids(G, core_u, core_v)
            prepared.append({
                "rung": rung["name"],
                "G": G,
                "record": rec,
                "identity": (list(G.u_ids), list(G.v_ids)),
                "core": core_ids,
                "oracle": (list(rec["opt_S"]), list(rec["opt_T"])),
            })
    return prepared


def _control_rho(item, which: str, lam: float) -> float:
    G = item["G"]
    rec = item["record"]
    keep_u, keep_v = item[which]
    final, _status, _work, _m = lift_value(
        G, keep_u, keep_v, rec["p"], rec["q"], rec["theta"], work_budget(rec, lam)
    )
    if final is None:
        return 0.0
    return clip01(raw_rho(final, rec["reference"]))


def sweep_lambdas(prepared, lambdas) -> list[dict]:
    rows = []
    n = len(prepared)
    for lam in lambdas:
        identity, core, oracle = [], [], []
        for i, item in enumerate(prepared, start=1):
            identity.append(_control_rho(item, "identity", lam))
            core.append(_control_rho(item, "core", lam))
            oracle.append(_control_rho(item, "oracle", lam))
            if i % 25 == 0 or i == n:
                print(f"  lambda {lam} {i}/{n}", flush=True)
        ident_mean = _mean(identity)
        nonzero = sum(1 for rho in identity if rho > 0.0) / n if n else 0.0
        row = {
            "lambda": float(lam),
            "identity": ident_mean,
            "core": _mean(core),
            "oracle": _mean(oracle),
            "nonzero": nonzero,
            "n_proven": n,
        }
        row["pass"] = gate_passes(row["identity"], row["core"], row["oracle"], row["nonzero"])
        rows.append(row)
        print(
            f"lambda {lam:.2f}  identity {row['identity']:.4f}  core {row['core']:.4f}  "
            f"oracle {row['oracle']:.4f}  nonzero {row['nonzero']:.3f}  pass {row['pass']}",
            flush=True,
        )
    return rows


def planted_raw_fraction(rungs, refs, lam: float) -> dict:
    """Identity on planted cells. Scoring clips at 1; this counts raw rho > 1."""
    over = 0
    scored = 0
    graphs = {}
    for rung in rungs:
        for rec in refs.values():
            if rec.get("rung") != rung["name"] or rec.get("kind") != "planted":
                continue
            if rung["name"] not in graphs:
                graphs[rung["name"]] = _load(rung)
            G = _graph_for_cell(graphs[rung["name"]], rec)
            final, _status, _work, _m = lift_value(
                G, list(G.u_ids), list(G.v_ids), rec["p"], rec["q"], rec["theta"],
                work_budget(rec, lam),
            )
            raw = 0.0 if final is None else raw_rho(final, rec["reference"])
            scored += 1
            if raw > 1.0:
                over += 1
            print(f"  planted {rung['name']} {rec['p']}/{rec['q']} t={rec['theta']} raw={raw:.3f}", flush=True)
    return {
        "lambda": float(lam),
        "n_planted": scored,
        "n_raw_above_one": over,
        "fraction_raw_above_one": (over / scored) if scored else 0.0,
    }


def format_sweep(rows: list[dict]) -> str:
    header = f"{'lambda':>8} {'identity':>10} {'core':>10} {'oracle':>10} {'nonzero':>10} pass"
    lines = [header]
    for row in rows:
        lines.append(
            f"{row['lambda']:8.2f} {row['identity']:10.4f} {row['core']:10.4f} "
            f"{row['oracle']:10.4f} {row['nonzero']:10.3f} {'yes' if row['pass'] else 'no'}"
        )
    return "\n".join(lines)


def identity_gate():
    """Sweep lambda on proven cells. Write the chosen lambda. Do not evolve.

    Returns the summary dict. `passed` is false when no lambda meets the rule,
    and in that case config.yaml is not modified.
    """
    cfg = config()
    rungs = dev_rungs()
    refs = ensure_references(rungs)
    backfill_optima(refs, rungs)
    prepared = _prepare_proven(rungs, refs)
    lambdas = [float(v) for v in cfg["lambda_grid"]]
    print(format_sweep([]).splitlines()[0], flush=True)
    rows = sweep_lambdas(prepared, lambdas)
    table = format_sweep(rows)
    print(table, flush=True)
    chosen = choose_lambda(rows)
    planted_stats = None
    if chosen is None:
        passed = False
        reason = "no lambda passed the proven-cell gate"
        selected = None
    else:
        passed = True
        selected = float(chosen["lambda"])
        reason = "chosen lambda minimizes |mean_rho(identity) - 0.5|"
        write_lambda(selected)
        print(f"chosen lambda {selected}", flush=True)
        backfill_planted_work(refs, rungs)
        planted_stats = planted_raw_fraction(rungs, refs, selected)
        print(
            f"planted raw rho > 1: {planted_stats['n_raw_above_one']}/{planted_stats['n_planted']} "
            f"({planted_stats['fraction_raw_above_one']:.3f})",
            flush=True,
        )
    summary = {
        "passed": passed,
        "abort": not passed,
        "reason": reason,
        "lambda": selected,
        "sweep": rows,
        "table": table,
        "n_proven": len(prepared),
        "planted": planted_stats,
    }
    path = ROOT / "rungs" / "identity_gate.json"
    path.write_text(json.dumps(summary))
    print(json.dumps({k: summary[k] for k in ("passed", "reason", "lambda", "planted")}, indent=2), flush=True)
    return summary


if __name__ == "__main__":
    identity_gate()
