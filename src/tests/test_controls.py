"""Matched-reduction controls, the evolver read-only check, and the spend cap."""

import json
import os
import random

from controls import control_rng, degree_keep, random_keep
from evolve.protect import assert_evolver_readonly
from evolve.spend import SpendCapReached, _add, spent
from graphs import BipartiteGraph


def graph():
    # Three edges. Degrees: u0=2, v3=2, u1=1, v2=1.
    return BipartiteGraph.from_edges([(0, 2), (0, 3), (1, 3)], [0, 1], [2, 3])


def test_degree_prefix_keeps_the_closest_edge_count():
    G = graph()
    keep_u, keep_v = degree_keep(G, 0.5)
    # Target is 1.5 edges. The first closest prefix has 1 edge: u0 plus v3.
    assert keep_u == [0]
    assert keep_v == [3]


def test_control_rng_is_deterministic():
    G = graph()
    first = random_keep(G, 0.5, control_rng("abc", "dev", 9, 10, 3))
    second = random_keep(G, 0.5, control_rng("abc", "dev", 9, 10, 3))
    assert first == second


def test_zero_reduction_keeps_nothing_and_random_is_seeded():
    G = graph()
    assert degree_keep(G, 0.0) == ([], [])
    first = random_keep(G, 1.0, random.Random(0))
    second = random_keep(G, 1.0, random.Random(0))
    assert first == second
    assert len(first[0]) + len(first[1]) == 4


def test_evolver_refuses_a_writable_protocol_file(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("lambda: 0.75\n")
    try:
        assert_evolver_readonly([path])
        refused = False
    except SystemExit as exc:
        refused = "writable" in str(exc)
    assert refused


def test_evolver_accepts_the_frozen_files():
    assert_evolver_readonly()


def test_dotenv_fills_a_missing_api_key(tmp_path, monkeypatch):
    from evolve.spend import load_project_env, openai_api_key

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    path = tmp_path / ".env"
    path.write_text("OPENAI_API_KEY=from-file\n")
    load_project_env(path)
    assert openai_api_key() == "from-file"
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")
    path.write_text("OPENAI_API_KEY=from-file-again\n")
    load_project_env(path)
    assert os.environ["OPENAI_API_KEY"] == "from-env"


def test_spend_ledger_prices_gpt5_mini_and_stops_at_the_cap(tmp_path):
    path = tmp_path / "spend.json"
    total = _add({"prompt_tokens": 1_000_000, "completion_tokens": 500_000}, "gpt-5-mini", path)
    assert abs(total - 1.25) < 1e-9
    assert abs(spent(path) - 1.25) < 1e-9
    path.write_text(json.dumps({"dollars": 4.0, "prompt_tokens": 0, "completion_tokens": 0, "calls": 1}))
    from evolve.spend import CappedLLM
    try:
        CappedLLM(None, cap=4.0, path=path)._refuse_if_spent()
        refused = False
    except SpendCapReached:
        refused = True
    assert refused
