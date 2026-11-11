# Where a project's files go

The launch message names `<id>`. Write only under `projects/<id>/`, except where this file names an existing shared module.

```
projects/<id>/
  memory.md            formulation. The define agent fills it.
  checker.py           is_valid and value. The check agent writes and tests it.
  plant.py             plant. The check agent writes and tests it.
  run.py               score. Calls the shared sandbox. The check agent writes and tests it.
  test_formulation.py  the test for those three files.
  testset.md           the ladder written by the graphs agent.
  frontier.md          scores and the harder instances, written by the frontier agent.
  solvers/solver.py    CP-SAT solver. Public name: solve.
  reductions/          one file per reduction program.
  heuristics/          one file per heuristic program.
  merges/              a combined program and the lower-bound hypothesis.
```

`config.yaml` and `rungs.yaml` are mode `0444`. Do not edit them, and do not edit `DECISIONS.md`.

Shared code under `src/`:

- `graphs.py` loads a local KONECT graph. See `@run.md`.
- `agents/sandbox.py` runs every candidate. Projects do not write a sandbox. See `@server.md`.
- `src/dsl/` is the quasi-biclique reduction language, separate from that sandbox.
- `src/checker.py` and `src/plant.py` are the quasi-biclique originals. A new project writes its own `checker.py` and `plant.py`. Do not edit the originals.

## Project quasi

`quasi` is the gamma-quasi-biclique, already filled in.

- Formulation: `projects/quasi/memory.md`
- Solver: `projects/quasi/solvers/cpsat.py`, imported as `projects.quasi.solvers`
- How to plant and call it: `projects/quasi/run.md`
- Encoding notes: `projects/quasi/structure.md`
- Search programs: `projects/quasi/heuristics/`

If that solver already returns the planted answer on the check in `projects/quasi/run.md`, leave `cpsat.py` in place. Do not add a second `solvers/solver.py` for quasi.
