# Merges

You try hypotheses that combine a reduction and a heuristic into one program that is still valid for the formulation. Then you try a reduction that only deletes a vertex when a lower bound says every good solution can spare it.

This is the last stage. It runs after `@frontier.md`. Read `@memory.md`, `@heuristics.md`, `@reductions.md`, `@structure.md`, and `projects/<id>/frontier.md`.

## Combine

Take the best heuristic and the best reduction named in `frontier.md`. Write one program under `projects/<id>/merges/` that reduces first and then searches on the kept subgraph. It must return the same object the formulation's heuristic returns.

Check it on the planted instances in `testset.md`. It scores zero when the return is infeasible. Record the cross-test average next to the heuristic's average from the frontier. Keep the combined program even when it does not win. The comparison is the result.

## Lower bound

Write a second hypothesis in the same directory: a reduction that deletes a vertex only when a proven lower bound shows that some solution of value at least the planted value survives without it.

State the bound in notation, in the same integer language as `memory.md`. For the quasi-biclique a starting bound is the degree core: a vertex of degree below `ceil(p * theta / q)` cannot sit in any feasible pair with both sides at least `theta`. A vertex the bound does not cover stays.

Then say what the bound does on the harder instance from `frontier.md`: which vertices it deletes, and whether the planted solution remains.

Do not claim the bound deletes more than the argument shows. A hypothesis that is only a guess belongs in the file labeled as unproved.
