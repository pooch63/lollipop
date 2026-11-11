"""The evolved search returns (S, T). Scoring does not call the solver."""

import random

from dsl.errors import LintError, ProgramError
from dsl.sandbox import launcher
from graphs import BipartiteGraph
from projects.quasi.heuristics.evaluate import initial_source, score_one
from projects.quasi.heuristics.lint import lint
from projects.quasi.heuristics.runtime import execute
from projects.quasi.heuristics.sandbox import run
from plant import degree_threshold_baseline
from store import connect, seed_hypotheses, seed_search_hypotheses


def _complete():
    edges = [(u, 3 + v) for u in range(3) for v in range(3)]
    return BipartiteGraph.from_edges(edges, range(3), range(3, 6))


def _rejects(source: str) -> bool:
    try:
        lint(source)
    except LintError:
        return True
    return False


def test_linter_accepts_loops_and_rejects_escapes():
    allowed = (
        "def search(G, p, q, theta):\n"
        "    best = None\n"
        "    for u in G.u_ids:\n"
        "        if best is None or G.degree_u(u) > G.degree_u(best):\n"
        "            best = u\n"
        "    S = []\n"
        "    while len(S) < theta and best is not None:\n"
        "        S.append(best)\n"
        "        break\n"
        "    return S, []\n"
    )
    lint(allowed)
    assert _rejects("import os\ndef search(G, p, q, theta):\n    return [], []\n")
    assert _rejects("def search(G, p, q, theta):\n    return open('x')\n")
    assert _rejects("def search(G, p, q, theta):\n    return eval('[]'), []\n")
    assert _rejects("def search(G, p, q, theta):\n    return getattr(G, 'm')\n")
    assert _rejects("def search(G, p, q, theta):\n    return G.__class__\n")
    assert _rejects("class Box:\n    pass\ndef search(G, p, q, theta):\n    return [], []\n")
    assert _rejects(
        "def search(G, p, q, theta):\n"
        "    try:\n"
        "        return [], []\n"
        "    except Exception:\n"
        "        return [], []\n"
    )


def test_seed_matches_the_degree_baseline_and_lints():
    source = initial_source()
    lint(source)
    graphs = [_complete()]
    rng = random.Random(0)
    for n in range(4, 8):
        u_ids = list(range(n))
        v_ids = list(range(100, 100 + n))
        edges = [(u, v) for u in u_ids for v in v_ids if rng.random() < 0.45]
        graphs.append(BipartiteGraph.from_edges(edges, u_ids, v_ids))
    cells = [(1, 1, 2), (9, 10, 3), (7, 10, 2), (8, 10, 4)]
    for G in graphs:
        for p, q, theta in cells:
            got = execute(source, G, p, q, theta)
            assert (got[0], got[1]) == degree_threshold_baseline(G, p, q, theta)


def test_score_uses_the_returned_pair_and_not_the_solver(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("solver was called")

    monkeypatch.setattr("projects.quasi.solvers.cpsat.solve", boom)
    G = _complete()
    scored = score_one(initial_source(), G, 1, 1, 2, 9, use_sandbox=False)
    assert scored["error"] is None
    assert scored["final"] == 9
    assert scored["rho"] == 1.0
    planted = score_one(initial_source(), G, 1, 1, 2, 1, kind="planted", use_sandbox=False)
    assert planted["rho"] == 1.0
    assert planted["rho_raw"] == 9.0
    empty = "def search(G, p, q, theta):\n    return [], []\n"
    assert score_one(empty, G, 1, 1, 2, 9, use_sandbox=False)["rho"] == 0.0
    bad = "def search(G, p, q, theta):\n    return [G.u_ids[0]], [G.v_ids[0]]\n"
    rejected = score_one(bad, G, 1, 1, 2, 9, use_sandbox=False)
    assert rejected["rho"] == 0.0
    assert rejected["error"] == "checker rejected the pair"


def test_step_limit_stops_a_scan():
    source = "def search(G, p, q, theta):\n    while True:\n        G.m\n    return [], []\n"
    try:
        execute(source, _complete(), 1, 1, 2, step_limit_value=20)
    except ProgramError as exc:
        assert "step limit" in str(exc)
    else:
        raise AssertionError("step limit was not enforced")


def test_sandbox_runs_the_seed_and_blocks_escape():
    G = _complete()
    out = run(initial_source(), G, 1, 1, 2)
    assert out["ok"] is True
    assert out["S"] == [0, 1, 2]
    assert out["T"] == [3, 4, 5]
    blocked = run("import socket\ndef search(G, p, q, theta):\n    return [], []\n", G, 1, 1, 2)
    assert blocked["ok"] is False
    assert blocked["error"].startswith("lint:")
    escape = run(
        "def search(G, p, q, theta):\n    return open('/etc/passwd'), []\n",
        G, 1, 1, 2, skip_lint=True, wall_seconds=10,
    )
    assert escape["ok"] is False
    assert launcher()[-1] == "dsl.worker"
    assert launcher("projects.quasi.heuristics.worker")[-1] == "projects.quasi.heuristics.worker"


def test_search_hypothesis_does_not_replace_reduction_claims(tmp_path):
    conn = connect(tmp_path / "h.sqlite")
    seed_hypotheses(conn)
    seed_search_hypotheses(conn)
    ids = [row["id"] for row in conn.execute("SELECT id FROM hypotheses ORDER BY id")]
    assert ids == ["H1", "H2", "H3", "H4", "H5", "HS1"]
    assert conn.execute("SELECT tier FROM hypotheses WHERE id='HS1'").fetchone()["tier"] == "search"
    assert conn.execute("SELECT tier FROM hypotheses WHERE id='H1'").fetchone()["tier"] == "L"


def test_openevolve_heuristic_config_loads():
    from openevolve.config import Config

    from projects.quasi.heuristics.evaluate import INITIAL_PATH
    from projects.quasi.heuristics.oe import evaluate_stage1, evaluate_stage2

    cfg = Config.from_yaml(INITIAL_PATH.parent / "openevolve.yaml")
    assert cfg.diff_based_evolution is False
    assert cfg.evaluator.cascade_evaluation is True
    assert callable(evaluate_stage1) and callable(evaluate_stage2)
