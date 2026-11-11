# Decisions

Simplest reading taken wherever the spec left a choice.

1. **Graph library.** No Python graph/KONECT library is installed. The matching
   library is GraphLogic.jl (`/home/kiyaanpillai/Documents/graph-logic`). The
   harness reads its indexed CSVs and meta files. It does not reimplement
   download or id indexing. See `API_NOTES.md`.

2. **Data roots.** `config.yaml` lists epsilon-core and aco-mkdb `data/`
   directories. On a duplicate key, the first root wins.

3. **Simple edges.** Indexed CSVs repeat `(u, v)` when KONECT stored multi-edges.
   `m` and adjacency are the simple graph (unique pairs). The MILP indicator
   `A_uv` is 0/1.

4. **`solve` return value.** The spec lists `(S, T, value, status)` and also
   asks for the work used. `solve` returns `(S, T, value, status, work)`.
   `work` is CP-SAT `deterministic_time`. `S` and `T` are sorted id lists.

5. **Edge variables.** `z_uv >= x_u + y_v - 1` is added so a feasible (not only
   optimal) objective equals `|E(S, T)|`. It does not change the optimum.

6. **DSL ids.** U vertices are `0 .. n_U-1`. V vertices are `n_U .. n_U+n_V-1`.
   Masks returned by `reduce` are side-local boolean lists of length `n_U` and
   `n_V`. `map("V", f)` returns a list indexed by the local V index
   (`global_id - n_U`). Original KONECT ids stay on `BipartiteGraph`.

7. **`threshold(arr, t)`** keeps indices where `arr[i] >= t`.

8. **`top_q(arr, q)`.** `0 < q <= 1` means a fraction (`ceil(q * n)` entries).
   `q > 1` means that many entries (integer count). Ties prefer the smaller index.

9. **`rank` / `sort_desc`.** Larger value is better. Ties break toward the
   smaller index. Rank 0 is the best element.

10. **Integer `n log2 n`.** `floor_log2(n) = n.bit_length() - 1` for `n >= 2`.
    Sort costs `n * floor_log2(n)`. Tier budget `f_N` uses the same factor.
    `f_N = 0` when `m <= 1`.

11. **Map nesting.** Maximum nested `map` depth is 1 for tiers L and N (a `map`
    may not contain another `map`) and 2 for tier Q.

12. **Strings.** The only string constants allowed in a program are `"U"` and
    `"V"`, because `map` needs a side. f-strings and `"%s" % x` are rejected.

13. **Sandbox names.** `p`, `q`, and `theta` are integer globals bound to the
    cell being evaluated. `ceil` / `floor` are the allowed pure functions.
    For the baseline, `p * theta / q` is exact in float for the project grid
    (`p <= 10`, `theta <= 5`).

14. **Extend ties.** Maximize the gain in `|E|`. If the gain is equal, the
    smaller vertex id wins. If a U id and a V id are equal, the U vertex is
    tried first.

15. **Degree-threshold baseline** (planted "too easy" check). Let `t = ceil(p * theta / q)`
    computed with integer arithmetic. Start from `S = {u : deg(u) >= t}`,
    `T = {v : deg(v) >= t}`. While the pair is invalid, drop the vertex with
    the largest membership deficit, breaking ties by smaller degree then smaller
    id (U first). Then run `extend`. If `value / planted_value >= 0.99`, the
    instance is `too_easy` and is excluded from scoring.

16. **Planted sizes.** `a = b = theta`. `S*` is `a` vertices of largest degree
    among those with `deg > b` (ties: smaller id). `T*` is analogous with
    `deg > a`. Edges are added only inside `S* x T*`. The number added is the
    minimum that meets the integer membership test, solved by a one-thread
    CP-SAT model. `max(U deficit, V deficit)` is only a lower bound: edges
    already present can block a pairing that hits it.

17. **Families.** Every local bipartite KONECT graph is in the Authorship
    category. Families used for the dev ladder are `wiktionary`, `wikiquote`,
    and `author-paper`.

18. **Comfortable held-out size.** Full graphs with more than `3_000_000`
    simple edges are not held-out rungs (eswiki is about 67M raw rows). The
    oracle is not built for graphs with `|U| + |V| > 250`; those rungs get
    `exact_status: false` without a solve.

19. **`exact_status` probe.** One CP-SAT run per dev rung at `(p, q, theta) = (9, 10, 3)`
    with `oracle_work_limit` from config. Held-out full graphs are above the
    vertex cap, so their status is false.

20. **Half-magnitude buckets.** `floor(2 * log10(m)) / 2`. One held-out graph
    per occupied bucket: the smallest `m` among bipartite graphs that were not
    used to cut dev rungs. The local corpus has no bipartite graph near `10^3`;
    the ladder starts at the smallest held-out graph that exists.

21. **Dev seeds.** BFS balls are cut from `konect-small/edit-zuwiktionary`,
    `konect-small/edit-srwikiquote`, and `konect/matter`. A prefix of the
    global maximum-degree vertex is a star on these graphs, and a star has no
    K_{2,2}. Every grid cell needs a K_{2,2} (for `|T| = 2`, even `γ = 7/10`
    requires two neighbors). The seed is the maximum-degree vertex whose
    degree is at least 2 and strictly less than 45% of the target order, so
    the ball includes a second hop. Ties: smaller id, then U before V. If no
    vertex sits in that degree band, the global maximum is used. Vertices are
    taken in BFS order (neighbors in id order) until `|U| + |V|` equals the
    target. The rung is that vertex-induced subgraph. No edge sampling.

22. **`κ`.** p-value threshold for the cost-ratio slope test. A program is a
    class violation when the least-squares slope of `cost_ratio` against
    `log(m)` is positive and the linregress p-value is `< κ`.

23. **`ρ`-kill.** After cascade stage 1, a program whose mean `ρ` is `<`
    `rho_kill_threshold` scores 0 and does not run stage 2.

24. **Predictions.** `prediction_json` is either one constraint
    `{metric, comparator, value, rungs, grid_cells}` or
    `{"all_of": [constraints, ...]}`. Comparators are `>=`, `>`, `<=`, `<`, `==`.

25. **Identity program.** `return peel(0, 0)`, which deletes nothing.

26. **Reference value.** On a proven cell the reference is the oracle optimum
    on the unreduced graph. Otherwise it is the planted value. `W_r` on a
    proven cell is `λ` times that proof's deterministic time. On a planted
    cell it is `λ` times the deterministic time CP-SAT reports on the
    unreduced planted graph under `planted_proof_cap` (10.0). A floor of
    `1e-4` remains so a zero-time proof is not an unlimited solve. Scoring
    rho on a planted cell is clipped at 1; the raw ratio is kept beside it.

27. **Fixed seed.** `config.yaml` `seed: 0` for graph sampling, CP-SAT
    `random_seed`, and any shuffle.

28. **Proven empty.** `solve` maps a CP-SAT infeasible model to status `NONE`,
    and the deterministic time comes back as 0. The reference builder treats
    `NONE` with work `<= 1e-6` as a proof that no solution exists (reference
    value 0). A `NONE` that consumed visible search time is unproven, and
    that cell is planted.

29. **Unplantable cells.** If fewer than `theta` vertices on a side have
    degree above the opposite planted size, the cell is excluded from the
    mean, same as a too-easy plant. It is not scored as a failure.

30. **Identity-control gate.** Only proven cells. Rho is clipped to `[0, 1]`
    before the mean. Planted cells are not in the gate. The three controls
    are identity, the baseline core, and an oracle reducer that keeps exactly
    the vertices of the proven optimum. A lambda passes when identity's mean
    is in `[0.2, 0.9]`, identity rho is `> 0` on at least half the proven
    cells, the core mean is at least the identity mean, and the oracle
    reducer mean is at least `0.95`. The sweep is the `lambda_grid` in
    config. The chosen lambda minimizes `|mean_rho(identity) - 0.5|` among
    those that pass; a tie keeps the smaller lambda. If none pass, config
    is left unchanged. The three controls run in-process. Evolution does
    not start from this sweep.

31. **protocol-v1.** `config.yaml` and `rungs.yaml` are the git tag
    `protocol-v1` (lambda 0.75 and the rung ladder). Both files are mode
    `0444`. The evolver refuses to start if either is writable.

32. **Matched-reduction controls.** For each evolved program and each scored
    cell, the target edge count is that cell's reduction times `m`. The
    random control adds vertices in a seeded shuffle. The degree control
    adds vertices in decreasing degree, breaking ties by U-before-V then
    smaller id. The kept prefix is the first one whose induced edge count
    is closest to the target. Both are then scored with the same lift as
    an evolved program.

33. **Smoke model and cap.** The L-tier smoke calls `gpt-5-mini` at the
    published rates of $0.25 / 1M input tokens and $2.00 / 1M output
    tokens. The hard cap is $4 for H1 and H2 together. A call is refused
    once recorded spend reaches $4. The key is `OPENAI_API_KEY` in the
    environment, or in `.env` at the repo root when the variable is unset.
    The program does not write the key. `.env` is gitignored.

34. **Search evolution.** `reduce` only chooses a vertex subset. CP-SAT and
    `extend` still build `(S, T)`. A second OpenEvolve loop evolves
`search(G, p, q, theta) -> (S, T)` (`projects/quasi/heuristics/openevolve.yaml`,
full rewrite). The parent scores that pair with `checker` and does not
call the solver. An empty pair scores as value 0. A nonempty pair that
fails the checker scores 0. Cost is graph queries divided by
`|U|+|V|+m`. The seed is the degree-threshold core plus greedy growth,
written out in `projects/quasi/heuristics/initial_search.py` so the evolver can change the
rule. The language allows loops and helpers and rejects imports, dunder
    attributes, and `eval`/`open`/`getattr`. The identity-control gate stays
    a reduction check and does not block this loop. Archive directory is
    `archive/search/`. Hypothesis id is `HS1`. Its LLM spend is a separate
    $4 cap in `projects/quasi/heuristics/spend.json`.
