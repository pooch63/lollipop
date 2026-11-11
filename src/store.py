"""Hypothesis and result tables. Status is written only by adjudicate.py."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from problem import config

SEED = [
    (
        "H1",
        "L",
        "dev",
        "Vertices with low (deg + nbr_sum(deg)) can be dropped above the safe core "
        "threshold at rho >= {h1_rho} with reduction <= {h1_reduction}.",
        {"all_of": [
            {"metric": "rho", "comparator": ">=", "value": "h1_rho", "rungs": "dev", "grid_cells": "all"},
            {"metric": "reduction", "comparator": "<=", "value": "h1_reduction", "rungs": "dev", "grid_cells": "all"},
        ]},
    ),
    (
        "H2",
        "L",
        "dev",
        "Minhash bucket collisions identify near-twin vertices; keeping one representative "
        "per bucket preserves rho >= {h2_rho}.",
        {"metric": "rho", "comparator": ">=", "value": "h2_rho", "rungs": "dev", "grid_cells": "all"},
    ),
    (
        "H3",
        "N",
        "dev",
        "Ranking vertices by degree and keeping the top fraction beats the baseline core "
        "on rho at equal reduction.",
        {"metric": "rho_minus_baseline", "comparator": ">", "value": 0, "rungs": "dev", "grid_cells": "all",
         "control": "reduction_within_0.05_of_baseline"},
    ),
    (
        "H4",
        "Q",
        "dev",
        "Jaccard overlap with the highest-degree vertices outperforms degree-only scoring "
        "on rho at the same reduction.",
        {"metric": "rho_minus_degree", "comparator": ">", "value": 0, "rungs": "dev", "grid_cells": "all",
         "control": "reduction_within_0.05"},
    ),
    (
        "H5",
        "Q",
        "dev",
        "A two-hop count score dominates every L-tier program on the Pareto front at "
        "alpha_hat within {h5_alpha_factor}x of the best L program.",
        {"metric": "pareto_dominates_L", "comparator": "==", "value": 1, "rungs": "dev", "grid_cells": "all",
         "alpha_factor": "h5_alpha_factor"},
    ),
]


def connect(path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS hypotheses (
            id TEXT PRIMARY KEY,
            claim TEXT NOT NULL,
            tier TEXT NOT NULL,
            rung_scope TEXT NOT NULL,
            prediction_json TEXT NOT NULL,
            status TEXT NOT NULL,
            run_ids TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY,
            run_id TEXT NOT NULL,
            hypothesis_id TEXT,
            program_hash TEXT NOT NULL,
            rung TEXT NOT NULL,
            gamma TEXT NOT NULL,
            theta INTEGER NOT NULL,
            metrics_json TEXT NOT NULL
        );
        """
    )
    conn.commit()
    return conn


def _resolve_prediction(spec, thresholds: dict):
    if isinstance(spec, dict) and "all_of" in spec:
        return {"all_of": [_resolve_prediction(item, thresholds) for item in spec["all_of"]]}
    out = dict(spec)
    value = out.get("value")
    if isinstance(value, str) and value in thresholds:
        out["value"] = thresholds[value]
    factor = out.get("alpha_factor")
    if isinstance(factor, str) and factor in thresholds:
        out["alpha_factor"] = thresholds[factor]
    return out


def seed_hypotheses(conn: sqlite3.Connection) -> None:
    """Insert H1-H5 if they are absent. Does not change a status that was adjudicated."""
    thresholds = config()["hypotheses"]
    for hid, tier, scope, claim_t, pred in SEED:
        claim = claim_t.format(**thresholds)
        prediction = _resolve_prediction(pred, thresholds)
        row = conn.execute("SELECT status FROM hypotheses WHERE id=?", (hid,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO hypotheses(id, claim, tier, rung_scope, prediction_json, status, run_ids) "
                "VALUES(?, ?, ?, ?, ?, 'untested', '')",
                (hid, claim, tier, scope, json.dumps(prediction)),
            )
        else:
            # Refresh the claim text from config, but never the status.
            conn.execute(
                "UPDATE hypotheses SET claim=?, prediction_json=?, tier=?, rung_scope=? WHERE id=?",
                (claim, json.dumps(prediction), tier, scope, hid),
            )
    conn.commit()


SEARCH_SEED = (
    "HS1",
    "search",
    "dev",
    "A degree-core greedy search, evolved as the procedure that returns (S, T), "
    "reaches mean rho >= 0.5 on the dev grid.",
    {"metric": "rho", "comparator": ">=", "value": 0.5, "rungs": "dev", "grid_cells": "all"},
)


def seed_search_hypotheses(conn: sqlite3.Connection) -> None:
    """Insert HS1 if it is absent. Does not change a status that was adjudicated."""
    hid, tier, scope, claim, pred = SEARCH_SEED
    row = conn.execute("SELECT status FROM hypotheses WHERE id=?", (hid,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO hypotheses(id, claim, tier, rung_scope, prediction_json, status, run_ids) "
            "VALUES(?, ?, ?, ?, ?, 'untested', '')",
            (hid, claim, tier, scope, json.dumps(pred)),
        )
    else:
        conn.execute(
            "UPDATE hypotheses SET claim=?, prediction_json=?, tier=?, rung_scope=? WHERE id=?",
            (claim, json.dumps(pred), tier, scope, hid),
        )
    conn.commit()


def query_hypotheses(conn, statuses=("refuted", "supported")):
    """What a proposer must read before writing a new claim."""
    marks = ",".join("?" for _ in statuses)
    rows = conn.execute(
        f"SELECT id, claim, tier, status, prediction_json FROM hypotheses WHERE status IN ({marks}) ORDER BY id",
        tuple(statuses),
    ).fetchall()
    return [dict(row) for row in rows]


def add_run(conn, hypothesis_id: str, run_id: str) -> None:
    row = conn.execute("SELECT run_ids FROM hypotheses WHERE id=?", (hypothesis_id,)).fetchone()
    if row is None:
        raise KeyError(hypothesis_id)
    ids = [x for x in row["run_ids"].split(",") if x]
    if run_id not in ids:
        ids.append(run_id)
    conn.execute("UPDATE hypotheses SET run_ids=? WHERE id=?", (",".join(ids), hypothesis_id))
    conn.commit()


def log_result(conn, run_id, hypothesis_id, program_hash, rung, gamma, theta, metrics: dict) -> None:
    conn.execute(
        "INSERT INTO results(run_id, hypothesis_id, program_hash, rung, gamma, theta, metrics_json) "
        "VALUES(?, ?, ?, ?, ?, ?, ?)",
        (run_id, hypothesis_id, program_hash, rung, gamma, int(theta), json.dumps(metrics)),
    )
    conn.commit()


def now() -> float:
    return time.time()
