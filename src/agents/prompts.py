"""Load a stage prompt and refuse a @ reference that has no file."""

from __future__ import annotations

import re
from pathlib import Path

from problem import ROOT

PROMPTS = ROOT / "prompts"

# Stage name -> file in prompts/. merging.md is the file the drawing calls merges.
STAGE_FILES = {
    "define": "define.md",
    "check": "check.md",
    "solver": "solver.md",
    "graphs": "graphs.md",
    "reductions": "reductions.md",
    "heuristics": "heuristics.md",
    "frontier": "frontier.md",
    "merging": "merging.md",
}

# define, then checker/plant/run, then the solver, then the ladder,
# then reductions beside heuristics, then the frontier, then merges.
WAVES = (
    ("define",),
    ("check",),
    ("solver",),
    ("graphs",),
    ("reductions", "heuristics"),
    ("frontier",),
    ("merging",),
)

_AT = re.compile(r"@([A-Za-z0-9_.-]+\.md)")


def referenced_names(text: str) -> list[str]:
    return _AT.findall(text)


def missing_references(text: str, prompts_dir: Path | None = None) -> list[str]:
    folder = Path(prompts_dir) if prompts_dir is not None else PROMPTS
    missing = []
    for name in referenced_names(text):
        if not (folder / name).is_file():
            missing.append(name)
    return missing


def load_stage(stage: str, prompts_dir: Path | None = None) -> str:
    if stage not in STAGE_FILES:
        known = ", ".join(STAGE_FILES)
        raise KeyError(f"unknown stage {stage!r}; known stages: {known}")
    folder = Path(prompts_dir) if prompts_dir is not None else PROMPTS
    path = folder / STAGE_FILES[stage]
    text = path.read_text()
    missing = missing_references(text, folder)
    if missing:
        names = ", ".join(missing)
        raise FileNotFoundError(f"{path.name} references missing files: {names}")
    return text


def render(stage: str, project: str, problem: str, *, iterations: int, prompts_dir: Path | None = None) -> str:
    folder = Path(prompts_dir) if prompts_dir is not None else PROMPTS
    body = load_stage(stage, folder)
    header = (
        f"Repo: lollipop\n"
        f"Project id: {project}\n"
        f"Project directory: projects/{project}\n"
        f"Iteration cap N: {iterations}\n"
        f"\n"
        f"Problem:\n{problem.strip()}\n"
        f"\n"
        f"Write files under projects/{project}/. "
        f"Leave prompts/ unchanged. "
        f"config.yaml and rungs.yaml are read-only. "
        f"Do not write sandbox.py.\n"
        f"\n"
    )
    attached = []
    seen = set()
    for name in referenced_names(body):
        if name in seen:
            continue
        seen.add(name)
        attached.append(f"\n\n# prompts/{name}\n\n{(folder / name).read_text()}")
    return header + body + "".join(attached)
