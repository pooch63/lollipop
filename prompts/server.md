# What the runner accepts

The pipeline runner is `src/agents/`. It calls OpenAI with `OPENAI_API_KEY` from the environment or `.env`, writes the files in the reply, and runs `test_*.py`. Identification stays on small graphs. A finished reduction may later be applied to a large graph. A heuristic is not run on a huge graph.

## The sandbox

`agents.sandbox.run` is the one sandbox. It is not written per project.

```python
from agents.sandbox import run

out = run(source, G, entry="search", params=params)
# out["ok"], out["result"], out["error"]
```

`source` defines `search(G, params)` and returns a solution. The process has no network, no imports, and a memory and CPU cap from `config.yaml`. `run.py` is the only project file that calls this. A candidate does not.

The DSL (`src/dsl/`) is the quasi-biclique reduction language only: `reduce(G)` returns `(keepU, keepV)`. A problem that is not that formulation writes a Python reduction under `reductions/` and scores it through `agents.sandbox.run` with `entry="reduce"`.

Do not import, open files, or call `eval` / `exec` / `getattr` from a submitted program.

## Features an agent may call

These are the lookups from the drawing. Hops stop at 3.

```python
from agents.features import density, order, hop_ball, hop_rank

order(G)                 # |U| + |V|
density(G)               # m / (|U| * |V|), or 0 when a side is empty
hop_ball(G, vertex, side, hops)   # hops is 1, 2, or 3; side is "U" or "V"
hop_rank(G, side, hops)  # (ball size, id), largest ball first, smaller id on a tie
```

Use them on the small ladder, not on a full graph above `oracle_vertex_cap`.
