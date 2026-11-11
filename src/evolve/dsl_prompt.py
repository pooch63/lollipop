"""System prompt for a tier-L evolver. The hypothesis claim is appended by the runner."""

TIER_L_RULES = """\
You evolve one Python function reduce(G) for a bipartite graph.
Return exactly one fenced python block and no other code.

The function returns boolean masks (keepU, keepV), or the pair that peel returns.
Allowed: assignments, arithmetic, comparisons, min max abs ceil floor, if/else,
tuple returns, and calls to the functions below. A lambda is allowed only as
the second argument of map. p, q, and theta are positive integer globals.
The only string constants are "U" and "V".

Tier L functions:
n_U(), n_V(), m(), deg(x), nbr_sum(x, arr), nbr_count_if(x, mask),
minhash(x, i) with i in 0..7, map(side, lambda), peel(a, b), threshold(arr, t).
peel(a, b) returns (keepU, keepV) for the (a, b)-core.
threshold(arr, t) keeps indices where arr[i] >= t.
map("U", f) or map("V", f) returns a list indexed on that side.

Forbidden: import, loops, comprehensions, classes, try, with, attribute access,
extra defs, and any name that is not a local or one of the functions above.
At most 150 AST nodes. Do not nest map.

The score is the fraction of the optimum quasi-biclique edge count recovered
after the reduced graph is solved and the solution is extended. A program
that fails the linter scores 0. Keep the result valid. Lower cost is better
only when the recovered fraction stays high.

A safe starting point, which keeps every vertex of every valid solution, is:
def reduce(G):
    keep = peel(ceil((p * theta) / q), ceil((p * theta) / q))
    return keep
"""
