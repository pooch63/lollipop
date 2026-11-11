"""The pipeline prompts resolve, and the runner calls stages in wave order."""

from pathlib import Path

from graphs import BipartiteGraph
from agents.features import density, hop_ball, hop_rank, order
from agents.pipeline import LaunchResult, ensure_project, run_pipeline
from agents.prompts import PROMPTS, STAGE_FILES, WAVES, missing_references, render
from agents.server import accept


def test_every_prompt_reference_exists():
    for path in sorted(PROMPTS.glob("*.md")):
        missing = missing_references(path.read_text(), PROMPTS)
        assert missing == [], f"{path.name} missing {missing}"


def test_stage_files_are_the_pipeline():
    assert [stage for wave in WAVES for stage in wave] == [
        "define",
        "solver",
        "graphs",
        "reductions",
        "heuristics",
        "frontier",
        "merging",
    ]
    assert WAVES[3] == ("reductions", "heuristics")
    for stage, name in STAGE_FILES.items():
        assert (PROMPTS / name).is_file(), stage


def test_render_names_the_project_and_refuses_a_missing_file(tmp_path):
    text = render("solver", "quasi", "gamma quasi biclique", iterations=3)
    assert "Project id: quasi" in text
    assert "Iteration cap N: 3" in text
    assert "gamma quasi biclique" in text
    (tmp_path / "solver.md").write_text("Read @missing.md now.\n")
    assert missing_references((tmp_path / "solver.md").read_text(), tmp_path) == ["missing.md"]


def test_pipeline_runs_reductions_and_heuristics_together(tmp_path):
    seen = []

    def launch(stage):
        seen.append(stage)
        status = "error" if stage == "frontier" else "finished"
        return LaunchResult(stage=stage, project="demo", status=status, text="")

    results = run_pipeline("demo", "a dense subgraph", root=tmp_path, launch=launch)
    assert seen[:3] == ["define", "solver", "graphs"]
    assert set(seen[3:5]) == {"reductions", "heuristics"}
    assert seen[5:] == ["frontier"]
    assert results[-1].status == "error"
    assert (tmp_path / "projects" / "demo" / "memory.md").is_file()


def test_ensure_project_does_not_clobber_memory(tmp_path):
    folder = ensure_project("demo", tmp_path)
    (folder / "memory.md").write_text("# Kept\n")
    ensure_project("demo", tmp_path)
    assert (folder / "memory.md").read_text() == "# Kept\n"


def test_accept_writes_a_heuristic(tmp_path):
    path = accept("demo", "heuristic", "def search(G, p, q, theta):\n    return [], []\n", root=tmp_path)
    assert path == tmp_path / "projects" / "demo" / "heuristics" / "candidate.py"
    assert path.read_text().startswith("def search")


def test_hop_ball_stops_at_three():
    # U 0 — 10 — U 1 — 11
    G = BipartiteGraph.from_edges([(0, 10), (1, 10), (1, 11)], [0, 1], [10, 11])
    assert order(G) == 4
    assert density(G) == 3 / 4
    assert hop_ball(G, 0, "U", 1) == [10]
    assert hop_ball(G, 0, "U", 2) == [1, 10]
    assert hop_ball(G, 0, "U", 3) == [1, 10, 11]
    assert hop_rank(G, "U", 1) == [(2, 1), (1, 0)]
    try:
        hop_ball(G, 0, "U", 4)
    except ValueError:
        pass
    else:
        raise AssertionError("hop 4 should be refused")
