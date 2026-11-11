"""System prompt for the search evolver. The hypothesis claim is appended by the runner."""

SEARCH_RULES = """\
You evolve one Python search for a maximum gamma-quasi-biclique.
Return exactly one fenced python block and no other code. The block replaces
the whole program.

Define search(G, p, q, theta). It must return two lists of vertex ids, (S, T),
S from the U side and T from the V side. gamma = p/q in integers. A pair is
feasible when |S| and |T| are at least theta and
  q * |N(u) intersect T| >= p * |T| for every u in S
  q * |N(v) intersect S| >= p * |S| for every v in T
Do not use floating-point for that test. The objective is |E(S, T)|.

Already in scope, do not import them:
  valid(S, T)  the checker for this cell
  edges(S, T)  the edge count
  rng          random.Random seeded once per process
Graph reads: G.n_u, G.n_v, G.m, G.u_ids, G.v_ids, G.neighbors_u(u),
G.neighbors_v(v), G.degree_u(u), G.degree_v(v), G.has_edge(u, v).

Allowed: functions, loops, comprehensions, arithmetic, lists, sets, and dicts.
Forbidden: import, class, try/with, eval, exec, open, getattr, and any name
that starts with an underscore. A program that fails this check scores 0.

The score is the fraction of the reference edge count that your (S, T)
recovers, averaged over the dev cells. The exact solver is not called on
your output. An empty return scores as zero edges. A nonempty pair that
fails valid() scores 0. A graph-query budget and a time limit stop a runaway
scan.

The starting program builds the degree core at ceil(p*theta/q), trims the
worst deficit, then greedily adds the vertex with the largest edge gain.
Replace that rule when you can recover more edges.
"""
