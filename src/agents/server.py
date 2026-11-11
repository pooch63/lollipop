"""Store a program the pipeline will run.

Heuristic and reduction candidates go through agents.sandbox. The quasi
DSL reductions still go through src/dsl, which is that language's runner.
"""

from __future__ import annotations

from pathlib import Path

from agents.pipeline import ensure_project, project_dir

_KINDS = {
    "dsl": "reductions",
    "reduction": "reductions",
    "heuristic": "heuristics",
}


def accept(project: str, kind: str, source: str, name: str = "candidate.py", root=None) -> Path:
    """Write `source` under the project directory for `kind`.

    `kind` is `dsl`, `reduction`, or `heuristic`. The name has to be a single
    file name, not a path.
    """
    if kind not in _KINDS:
        known = ", ".join(sorted(_KINDS))
        raise ValueError(f"kind must be one of {known}")
    if not name or "/" in name or name.startswith("."):
        raise ValueError("name must be a single file name")
    ensure_project(project, root)
    dest = project_dir(project, root) / _KINDS[kind] / name
    dest.write_text(source)
    return dest


def run_submitted(project: str, kind: str, source: str, G, **params):
    """Execute a submitted program.

    `dsl` is the quasi reduction language and needs integer `p`, `q`, `theta`.
    `reduction` and `heuristic` call `agents.sandbox.run`. The candidate
    defines `reduce(G, params)` or `search(G, params)`.
    """
    if kind == "dsl":
        from dsl.sandbox import run

        return run(
            source,
            G,
            int(params["p"]),
            int(params["q"]),
            int(params["theta"]),
            params.get("tier", "L"),
        )
    if kind in ("reduction", "heuristic"):
        from agents.sandbox import run

        entry = "reduce" if kind == "reduction" else "search"
        return run(source, G, entry=entry, params=params)
    raise ValueError(f"kind must be dsl, reduction, or heuristic, got {kind!r}")
