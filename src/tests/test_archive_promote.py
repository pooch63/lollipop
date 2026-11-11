"""Pareto export, promotion rankings, and the OpenEvolve config schema."""

import json

from openevolve.config import Config
from openevolve.utils.code_utils import parse_full_rewrite

from archive_export import export_tier, pareto_front
from evolve import mock_llm
from problem import SRC
from promote import cell_mean_rho, top_k, walk_rungs
from report import render_report


def _prog(name, rho, alpha, rows=None):
    return {
        "source": f"def reduce(G):\n    return peel({name}, {name})\n",
        "rho": rho,
        "alpha_hat": alpha,
        "program_hash": name,
        "pseudocode": f"1. peel({name}, {name})",
        "per_rung": rows or [],
        "rows": rows or [],
    }


def test_pareto_drops_a_dominated_program(tmp_path):
    programs = [
        _prog("a", 0.9, 1.0),
        _prog("b", 0.9, 2.0),  # same rho, worse alpha
        _prog("c", 0.7, 0.4),  # worse rho, better alpha: stays
    ]
    front = pareto_front(programs)
    hashes = {p["program_hash"] for p in front}
    assert hashes == {"a", "c"}
    exported = export_tier("L", programs, "H1", "run-1", root=tmp_path)
    assert exported["best"]["program_hash"] == "a"
    assert (tmp_path / "archive" / "L" / "programs.json").exists()
    pool = json.loads((tmp_path / "archive" / "L" / "programs.json").read_text())
    assert len(pool) == 3


def test_promotion_censors_and_reports_tau():
    programs = [
        {"program_hash": "A", "source": "a"},
        {"program_hash": "B", "source": "b"},
        {"program_hash": "C", "source": "c"},
    ]
    table = {
        ("A", "r1"): {"rho": 0.9},
        ("A", "r2"): {"rho": 0.3},
        ("A", "r3"): {"error": "timeout"},
        ("B", "r1"): {"rho": 0.2},
        ("B", "r2"): {"rho": 0.8},
        ("B", "r3"): {"rho": 0.6},
        ("C", "r1"): {"error": "invalid"},
    }

    def evaluate(prog, rung):
        return table[(prog["program_hash"], rung)]

    walk = walk_rungs(programs, ["r1", "r2", "r3"], evaluate)
    assert walk["survivors"] == ["B"]
    assert {item["program_hash"] for item in walk["censored"]} == {"A", "C"}
    assert walk["censored"][0]["reason"] in ("timeout", "invalid", "kill")
    first = walk["kendall"][0]
    assert first["n_shared"] == 2
    assert first["tau"] == -1.0
    second = walk["kendall"][1]
    assert second["n_shared"] == 1
    assert second["tau"] is None
    assert "fewer than 2" in second["note"]


def test_top_k_uses_the_cell_mean():
    programs = [
        _prog("low", 0.1, 1.0, rows=[{"p": 9, "q": 10, "theta": 3, "rho": 0.2}]),
        _prog("high", 0.1, 1.0, rows=[{"p": 9, "q": 10, "theta": 3, "rho": 0.8}]),
    ]
    picked = top_k(programs, lambda p: cell_mean_rho(p, 9, 10, 3), 1)
    assert picked[0]["program_hash"] == "high"


def test_openevolve_yaml_matches_the_installed_schema():
    cfg = Config.from_yaml(SRC / "evolve" / "openevolve.yaml")
    assert cfg.max_iterations == 3
    assert cfg.diff_based_evolution is False
    assert cfg.database.feature_dimensions == ["rho", "alpha_hat"]
    assert cfg.database.feature_bins == {"rho": 5, "alpha_hat": 6}
    assert cfg.database.island_initial_programs == []
    assert cfg.evaluator.cascade_evaluation is True
    assert cfg.evaluator.cascade_thresholds == [0.5]
    assert cfg.evaluator.parallel_evaluations == 1


def test_mock_reply_is_a_full_rewrite(tmp_path, monkeypatch):
    monkeypatch.setattr(mock_llm, "COUNTER", tmp_path / "calls.txt")
    source = parse_full_rewrite(mock_llm.next_response(), language="python")
    assert source.startswith("import socket")
    assert "def reduce" in source


def test_smoke_refuses_when_the_gate_does_not_pass():
    from evolve.smoke import evolution_allowed
    assert evolution_allowed({"passed": False, "abort": True}) is False
    assert evolution_allowed({"passed": True}) is True


def test_report_names_missing_sections(tmp_path):
    text = render_report(tmp_path)
    assert "Identity-control gate has not been run" in text
    assert "no archived program" in text
    assert "Promotion has not been run" in text
    assert "Hypothesis store has not been created" in text
    assert "Ledger has not been created" in text
