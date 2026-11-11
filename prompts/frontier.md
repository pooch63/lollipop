# Frontier

You score the reductions and the heuristics that the previous wave wrote, and you name the next harder instance. This stage is allowed to cost more than the small-graph identification. It runs after both `@reductions.md` and `@heuristics.md`, and it is the only place those two are compared.

Read `projects/<id>/testset.md`, the programs under `projects/<id>/reductions/` and `projects/<id>/heuristics/`, plus `@structure.md` and `@server.md`.

## Score

For each heuristic, use the cross-test average from `@heuristics.md`: recovery of planted value on the instances it was not grown on. A program that fails feasibility scores 0.

For each reduction, use vertices removed and edges removed, and only count a reduction whose best-known solution is still fully inside the kept subgraph (`@reductions.md`).

Write both tables to `projects/<id>/frontier.md`.

## Harder instance

Inject one instance that is harder than the current ladder, and record what happened.

- Prefer the next KONECT graph above the last kept row in `testset.md`, still at or under `max_comfortable_edges`.
- If that graph is above `oracle_vertex_cap`, plant on a BFS ball whose order equals the cap instead of solving the full graph. The ball construction for quasi is `bfs_ball` in `src/make_rungs.py`. Do not edit `rungs.yaml`.
- Run the single best heuristic and the single best reduction on that instance.
- Write whether the planted solution came back, and whether the reduction kept it.

The miss, if there is one, is the message the next heuristic round should see. Do not dump every intermediate job into `frontier.md`. Write the instance key, the planted value, and the value each program returned.

Stop after one harder instance. A second climb is another launch, not this one.
