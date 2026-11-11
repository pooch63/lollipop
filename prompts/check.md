# Checker, planter, and runner

Write the membership test, the planter, and the scoring runner for this project. Then test all three. The sandbox is already written. You do not write `sandbox.py`, you do not copy it, and you do not start a process yourself.

Read `@memory.md`, `@planter.md`, `@structure.md`, and `@server.md`. The formulation you implement is `projects/<id>/memory.md`.

## Files

All four paths are relative to `projects/<id>/`.

- `checker.py` with `is_valid(G, solution, params) -> bool` and `value(G, solution) -> int`. Integer arithmetic only. `params` is a dict of the formulation's parameters.
- `plant.py` with `plant(G, params) -> dict | None`. `None` means the graph cannot hold a plant. Otherwise the dict has `solution`, `graph`, `value`, `too_easy`, and `params`. `graph` is the graph the solution is feasible on. `too_easy` is true when a trivial baseline already recovers at least 99% of `value`.
- `run.py` with `score(source, G, params) -> int`. Call `agents.sandbox.run(source, G, entry="search", params=params)`. The candidate source defines `search(G, params)` and returns a solution. If `ok` is false, or `is_valid` is false, return 0. Otherwise return `value`.
- `test_formulation.py`. Build a small graph with `BipartiteGraph.from_edges`. Plant a solution. Assert `is_valid` on it and that `value` matches the plant. Assert a broken or empty solution fails `is_valid`. Call `score` on a candidate that returns the planted solution and expect the planted value. Call `score` on a candidate that returns an empty solution and expect 0.

`search` takes `(G, params)` only. It cannot import. The sandbox already refuses imports, network, and file access.

Project `quasi` already has the math in `src/checker.py` and `src/plant.py`. Do not edit those two files. For that project, `checker.py` and `plant.py` adapt `(solution, params)` onto `is_valid(G, S, T, p, q, theta)` and `plant(G, p, q, theta)`, with `solution` equal to `(S, T)` and `params` holding `p`, `q`, and `theta`. Still write `run.py` and `test_formulation.py`, and still make the test pass.

## Reply format

Reply with fenced python blocks and nothing else. The first line inside each fence is `# file: checker.py` (or `plant.py`, `run.py`, `test_formulation.py`).
