"""Set hypothesis status from logged metrics. No LLM calls this."""

from __future__ import annotations

import json

COMPARATORS = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
}


def _check(metric_value, comparator, target) -> bool:
    fn = COMPARATORS[comparator]
    return bool(fn(metric_value, target))


def _constraints(prediction: dict) -> list[dict]:
    if "all_of" in prediction:
        return list(prediction["all_of"])
    return [prediction]


def adjudicate(conn) -> dict[str, str]:
    """Compare each hypothesis to its logged results and set status.

    supported: every logged cell satisfies every constraint, and at least one cell exists
    refuted: some logged cell violates a constraint
    inconclusive: results exist but a required control (equal reduction, Pareto) is missing
    untested: no results for that hypothesis
    """
    out = {}
    rows = conn.execute("SELECT * FROM hypotheses").fetchall()
    for row in rows:
        hid = row["id"]
        run_ids = [x for x in (row["run_ids"] or "").split(",") if x]
        if run_ids:
            marks = ",".join("?" for _ in run_ids)
            results = conn.execute(
                f"SELECT metrics_json FROM results WHERE hypothesis_id=? OR run_id IN ({marks})",
                (hid, *run_ids),
            ).fetchall()
        else:
            results = conn.execute(
                "SELECT metrics_json FROM results WHERE hypothesis_id=?", (hid,)
            ).fetchall()
        if not results:
            status = "untested"
        else:
            prediction = json.loads(row["prediction_json"])
            status = _judge(prediction, [json.loads(r["metrics_json"]) for r in results])
        conn.execute("UPDATE hypotheses SET status=? WHERE id=?", (status, hid))
        out[hid] = status
    conn.commit()
    return out


def _judge(prediction: dict, metrics_list: list[dict]) -> str:
    constraints = _constraints(prediction)
    saw_control_gap = False
    saw_value = False
    for metrics in metrics_list:
        for constraint in constraints:
            metric = constraint["metric"]
            if metric not in metrics or metrics[metric] is None:
                # Missing control fields (equal-reduction comparisons) are inconclusive,
                # not a refutation.
                if constraint.get("control"):
                    saw_control_gap = True
                    continue
                saw_control_gap = True
                continue
            saw_value = True
            if not _check(metrics[metric], constraint["comparator"], constraint["value"]):
                return "refuted"
    if not saw_value:
        return "inconclusive"
    if saw_control_gap:
        return "inconclusive"
    return "supported"
