# Heuristics

Evolve a heuristic that recovers a planted solution, then check that it still recovers the planted solutions on the other graphs. A heuristic that only works on the graph it saw is not done.

Read `@memory.md`, `@planter.md`, `@graphs.md`, `@structure.md`, and `@server.md`. The launch message gives the iteration cap `N`.

## Per graph

For each graph in `projects/<id>/testset.md`:

1. Plant a solution (`@planter.md`). Skip `too_easy` and skip a graph the planter refuses.
2. Start from an arbitrary seed. The first seed on every graph is `problem.seed()` plus the graph's place in the ladder. Do not pick the seed by looking at the planted sets.
3. Evolve the heuristic for at most `N` iterations, or until it recovers the entire planted solution, whichever comes first.
4. The jobs are per graph. Do not show this agent every intermediate search state. Show it, after a round, which planted solutions came back and which did not. The misses are how it tells why the heuristic underperformed.

## Cross-test

Take each heuristic that recovered its own plant and run it on the other planted instances. It does not get to refit. The score is the fraction of each planted value it recovers, averaged over the instances it was not grown on. The heuristic with the best average is the one you keep.

An empty return scores 0. A return that fails the formulation's feasibility predicate scores 0.

## What to write

Write the kept program under `projects/<id>/heuristics/`. Score it with `score` from `projects/<id>/run.py`, which calls the shared sandbox in `@server.md`. Do not write `sandbox.py` and do not start a process.

`search(G, params)` returns the solution object from `memory.md`. For project `quasi`, `params` is `{"p", "q", "theta"}` and the solution is `(S, T)`. The seed program is `projects/quasi/heuristics/initial_search.py` (degree core, drop the worst deficit, greedy growth). Replace that rule when the cross-test improves. Loops and helpers are allowed. Imports, dunder attributes, `eval`, `open`, and `getattr` are not.

Reply with fenced python blocks. The first line inside each fence is `# file: heuristics/<name>.py`.

## Scope

Small graphs only, the same ladder as `@reductions.md`. This stage runs beside reductions. You do not read the reduction programs and you do not wait for them.

Order, density, and neighborhoods out to 3 hops are in `@server.md` (`agents.features`). Use those as features. Do not walk a hop deeper than 3.
