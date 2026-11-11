"""Launch pipeline agents.

    PYTHONPATH=src python -m agents list
    PYTHONPATH=src python -m agents render solver --project quasi
    PYTHONPATH=src python -m agents run solver --project quasi --dry-run
    PYTHONPATH=src python -m agents pipeline --project quasi --dry-run
    PYTHONPATH=src python -m agents accept --project quasi --kind heuristic --name cand.py --source-file cand.py

`--dry-run` writes the prompt under projects/<id>/launches/ and does not call
OpenAI. A real launch uses OPENAI_API_KEY from the environment or from .env.
"""

from __future__ import annotations

import argparse
import sys

from agents.pipeline import LaunchResult, launch_stage, problem_text, run_pipeline
from agents.prompts import STAGE_FILES, WAVES
from agents.server import accept


def _print_result(result: LaunchResult) -> int:
    print(f"{result.stage}\t{result.status}\t{result.prompt_path or ''}")
    if result.status == "startup_error":
        print(result.text, file=sys.stderr)
        return 1
    if result.status == "error":
        print(result.text, file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Call the lollipop pipeline agents.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="print stages in wave order")

    def add_common(cmd):
        cmd.add_argument("--project", required=True)
        cmd.add_argument("--problem", default="")
        cmd.add_argument("--problem-file")
        cmd.add_argument("--iterations", type=int, default=40)
        cmd.add_argument("--model", default="gpt-5-mini")
        cmd.add_argument("--dry-run", action="store_true")

    render_cmd = sub.add_parser("render", help="print one stage prompt")
    render_cmd.add_argument("stage", choices=sorted(STAGE_FILES))
    add_common(render_cmd)

    run_cmd = sub.add_parser("run", help="launch one stage")
    run_cmd.add_argument("stage", choices=sorted(STAGE_FILES))
    add_common(run_cmd)

    pipe = sub.add_parser("pipeline", help="launch every wave")
    add_common(pipe)
    pipe.add_argument("--from", dest="start", choices=sorted(STAGE_FILES))
    pipe.add_argument("--only", choices=sorted(STAGE_FILES))

    take = sub.add_parser("accept", help="store a dsl, reduction, or heuristic program")
    take.add_argument("--project", required=True)
    take.add_argument("--kind", required=True, choices=("dsl", "reduction", "heuristic"))
    take.add_argument("--name", default="candidate.py")
    take.add_argument("--source-file", required=True)

    args = parser.parse_args(argv)
    if args.command == "list":
        for wave in WAVES:
            print(" ".join(wave))
        return 0

    if args.command == "accept":
        source = open(args.source_file).read()
        path = accept(args.project, args.kind, source, name=args.name)
        print(path)
        return 0

    problem = args.problem
    if args.problem_file:
        problem = open(args.problem_file).read()
    try:
        problem = problem_text(args.project, problem)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.command == "render":
        result = launch_stage(
            args.stage,
            args.project,
            problem,
            iterations=args.iterations,
            dry_run=True,
        )
        sys.stdout.write(result.text)
        return 0

    if args.command == "run":
        try:
            result = launch_stage(
                args.stage,
                args.project,
                problem,
                iterations=args.iterations,
                model=args.model,
                dry_run=args.dry_run,
            )
        except (RuntimeError, KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return _print_result(result)

    try:
        results = run_pipeline(
            args.project,
            problem,
            iterations=args.iterations,
            model=args.model,
            dry_run=args.dry_run,
            start=args.start,
            only=args.only,
        )
    except (RuntimeError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    code = 0
    for result in results:
        code = max(code, _print_result(result))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
