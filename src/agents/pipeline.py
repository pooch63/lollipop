"""Call the stage agents in the order the pipeline drawing fixes.

Wave order: define, check, solver, graphs, then reductions beside heuristics,
then frontier, then merging. A failed wave stops the pipeline.

Each call uses the OpenAI API. The key is OPENAI_API_KEY, from the
environment or from .env, via evolve.spend.openai_api_key.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from agents.files import missing_check_files, run_tests, write_files
from agents.prompts import STAGE_FILES, WAVES, render
from problem import ROOT, SRC

MODEL = "gpt-5-mini"
SPEND_PATH = SRC / "agents" / "spend.json"
_SYSTEM = (
    "You write files for one graph project. "
    "When the prompt asks for code, reply with fenced blocks whose first line is "
    "`# file: relative/path`. Paths are relative to the project directory. "
    "Do not write sandbox.py. Do not start a subprocess. "
    "Candidates run through agents.sandbox.run, which already exists."
)

_ID = __import__("re").compile(r"^[a-z][a-z0-9_-]{0,40}$")
STUB_MARK = "Status: empty"


@dataclass
class LaunchResult:
    stage: str
    project: str
    status: str
    text: str
    prompt_path: str | None = None
    retryable: bool = False

    def ok(self) -> bool:
        return self.status in ("finished", "dry_run")


def check_project_id(project: str) -> str:
    if not _ID.fullmatch(project):
        raise ValueError(
            "project id must be a lowercase letter, then letters, digits, '_' or '-'"
        )
    return project


def project_dir(project: str, root: Path | None = None) -> Path:
    check_project_id(project)
    return (Path(root) if root is not None else ROOT) / "projects" / project


def ensure_project(project: str, root: Path | None = None) -> Path:
    """Create the directories a stage writes into. Never overwrite memory.md."""
    folder = project_dir(project, root)
    for name in ("solvers", "reductions", "heuristics", "merges", "launches"):
        (folder / name).mkdir(parents=True, exist_ok=True)
    init = folder / "__init__.py"
    if not init.exists():
        init.write_text("")
    memory = folder / "memory.md"
    if not memory.exists():
        memory.write_text(
            f"# Formulation\n\nStatus: empty. Fill every section in prompts/memory.md.\n"
            f"Project: {project}\n"
        )
    return folder


def problem_text(project: str, problem: str | None, root: Path | None = None) -> str:
    if problem and problem.strip() and STUB_MARK not in problem:
        return problem.strip()
    memory = project_dir(project, root) / "memory.md"
    if memory.is_file():
        text = memory.read_text().strip()
        if text and STUB_MARK not in text:
            return text
    raise ValueError("pass a problem statement, or fill projects/<id>/memory.md first")


def dry_launch(stage: str, project: str, problem: str, *, iterations: int, root: Path | None = None) -> LaunchResult:
    prompt = render(stage, project, problem, iterations=iterations)
    folder = ensure_project(project, root)
    path = folder / "launches" / f"{stage}.md"
    path.write_text(prompt)
    return LaunchResult(
        stage=stage,
        project=project,
        status="dry_run",
        text=prompt,
        prompt_path=str(path),
    )


def _openai_key(api_key: str | None) -> str:
    if api_key and api_key.strip():
        return api_key.strip()
    from evolve.spend import openai_api_key

    return openai_api_key()


def openai_launch(prompt: str, *, model: str, api_key: str) -> str:
    """One chat completion. Returns the assistant text."""
    from openai import OpenAI

    from evolve.spend import _add

    client = OpenAI(api_key=api_key)
    lower = model.lower()
    reasoning = lower.startswith(("gpt-5", "o1", "o3", "o4"))
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
    }
    if reasoning:
        kwargs["max_completion_tokens"] = 8000
        kwargs["reasoning_effort"] = "low"
    else:
        kwargs["max_tokens"] = 8000
        kwargs["temperature"] = 0.2
    response = client.chat.completions.create(**kwargs)
    usage = getattr(response, "usage", None)
    _add(
        {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        },
        model,
        SPEND_PATH,
    )
    return response.choices[0].message.content or ""


def _apply(stage: str, folder: Path, text: str, root: Path | None) -> LaunchResult:
    try:
        written = write_files(folder, text)
    except ValueError as exc:
        return LaunchResult(stage=stage, project=folder.name, status="error", text=str(exc))
    if stage == "check":
        missing = missing_check_files(folder)
        if missing:
            return LaunchResult(
                stage=stage,
                project=folder.name,
                status="error",
                text="missing " + ", ".join(missing),
            )
    code, tail = run_tests(written, root)
    if code != 0:
        return LaunchResult(stage=stage, project=folder.name, status="error", text=tail)
    return LaunchResult(stage=stage, project=folder.name, status="finished", text=text)


def launch_stage(
    stage: str,
    project: str,
    problem: str,
    *,
    iterations: int = 40,
    model: str = MODEL,
    dry_run: bool = False,
    root: Path | None = None,
    api_key: str | None = None,
) -> LaunchResult:
    if stage not in STAGE_FILES:
        raise KeyError(stage)
    check_project_id(project)
    folder = ensure_project(project, root)
    if dry_run:
        return dry_launch(stage, project, problem, iterations=iterations, root=root)
    try:
        key = _openai_key(api_key)
    except RuntimeError as exc:
        raise RuntimeError(str(exc) + "; pass --dry-run to write the prompt only") from exc
    prompt = render(stage, project, problem, iterations=iterations)
    path = folder / "launches" / f"{stage}.md"
    path.write_text(prompt)
    try:
        text = openai_launch(prompt, model=model, api_key=key)
    except Exception as exc:
        return LaunchResult(
            stage=stage,
            project=project,
            status="error",
            text=f"{type(exc).__name__}: {exc}",
            prompt_path=str(path),
        )
    result = _apply(stage, folder, text, root)
    result.prompt_path = str(path)
    (folder / "launches" / f"{stage}.reply.md").write_text(text)
    return result


def _waves_from(start: str | None, only: str | None) -> tuple[tuple[str, ...], ...]:
    if only is not None:
        if only not in STAGE_FILES:
            raise KeyError(only)
        return ((only,),)
    if start is None:
        return WAVES
    if start not in STAGE_FILES:
        raise KeyError(start)
    for index, wave in enumerate(WAVES):
        if start in wave:
            return WAVES[index:]
    raise KeyError(start)


def run_pipeline(
    project: str,
    problem: str,
    *,
    iterations: int = 40,
    model: str = MODEL,
    dry_run: bool = False,
    root: Path | None = None,
    api_key: str | None = None,
    start: str | None = None,
    only: str | None = None,
    launch=None,
) -> list[LaunchResult]:
    """Run each wave. Reductions and heuristics share a wave and run together.

    `launch(stage) -> LaunchResult` replaces the Cursor call. Tests pass one.
    """
    check_project_id(project)
    ensure_project(project, root)
    waves = _waves_from(start, only)

    def call(stage: str) -> LaunchResult:
        if launch is not None:
            return launch(stage)
        return launch_stage(
            stage,
            project,
            problem,
            iterations=iterations,
            model=model,
            dry_run=dry_run,
            root=root,
            api_key=api_key,
        )

    results: list[LaunchResult] = []
    for wave in waves:
        if len(wave) == 1:
            result = call(wave[0])
            results.append(result)
            if not result.ok():
                return results
            continue
        with ThreadPoolExecutor(max_workers=len(wave)) as pool:
            wave_results = list(pool.map(call, wave))
        results.extend(wave_results)
        if any(not item.ok() for item in wave_results):
            return results
    return results
