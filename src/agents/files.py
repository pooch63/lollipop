"""Pull `# file:` blocks out of an agent reply and run the tests it wrote."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from problem import ROOT, child_env

_FENCE = re.compile(r"```(?:python|markdown|md)?\s*\n# file: ([^\n]+)\n(.*?)```", re.S)

_REQUIRED_CHECK = ("checker.py", "plant.py", "run.py", "test_formulation.py")


def extract_files(text: str) -> list[tuple[str, str]]:
    found = []
    for rel, body in _FENCE.findall(text):
        found.append((rel.strip(), body if body.endswith("\n") else body + "\n"))
    return found


def _safe_relative(rel: str) -> Path:
    path = Path(rel)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"refusing path {rel!r}")
    if path.name == "sandbox.py":
        raise ValueError("sandbox.py is shared; a project does not write one")
    return path


def write_files(project_dir: Path, text: str) -> list[Path]:
    written = []
    for rel, body in extract_files(text):
        path = _safe_relative(rel)
        dest = project_dir / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body)
        written.append(dest)
    return written


def missing_check_files(project_dir: Path) -> list[str]:
    return [name for name in _REQUIRED_CHECK if not (project_dir / name).is_file()]


def run_tests(paths: list[Path], root: Path | None = None) -> tuple[int, str]:
    tests = [p for p in paths if p.name.startswith("test_") and p.suffix == ".py"]
    if not tests:
        return 0, ""
    repo = Path(root) if root is not None else ROOT
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *[str(p) for p in tests], "-q", "--tb=short"],
        cwd=str(repo),
        env=child_env(),
        capture_output=True,
        text=True,
    )
    tail = (proc.stdout + proc.stderr)[-2000:]
    return proc.returncode, tail
