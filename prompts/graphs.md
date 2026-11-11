# Determine the test set

Generalization is the question: a heuristic has to be scored on more than the graph it was grown on. You choose the ladder those later stages share.

Read the formulation in `projects/<id>/memory.md` (`@memory.md` is the contract). Read `@run.md`, `@planter.md`, and `@structure.md`.

## Climb

Use `list_local_graphs` from `@run.md`. The list is smallest `edges_rows` first. Walk upward.

On each graph, in order:

1. Plant a solution first (`@planter.md`). If the plant returns nothing, skip the graph. If it is `too_easy`, skip it.
2. If `|U| + |V|` is above `oracle_vertex_cap`, do not call CP-SAT on the full graph. Record the key and move on.
3. Otherwise call the project solver with `work_limit` set to `oracle_work_limit`. Keep the graph when the status is optimal or feasible, the value is at least the planted value, and `work` is within that limit.
4. Stop the climb at the first graph that has a plant, is small enough to solve, and misses that work threshold. Record that graph as the first failure.

The graphs you keep are the test set. Write them to `projects/<id>/testset.md`: one row per kept graph (`key`, `edges_rows`, planted value, solver status, `work`) and a last line naming the first failure.

This stage is the small-graph identification. It does not run on a graph above `max_comfortable_edges`.

## Project quasi

`rungs.yaml` is already the ladder, and it is read-only. Do not regenerate it and do not edit it. Read it, and write `projects/quasi/testset.md` as a pointer at `rungs.yaml` plus the keys it uses. Confirm a planted solution exists on the smallest dev rung. Do not launch a new climb over KONECT.

## Parallel

This stage runs after the solver exists, because step 3 calls it. It does not run beside reductions or heuristics. Those wait for this file.
