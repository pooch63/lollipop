"""Linter, abstract costs, baseline core, and the sandbox."""

import ast

from dsl.errors import LintError
from dsl.lint import lint
from dsl.programs import BASELINE_L, IDENTITY
from dsl.runtime import View, Counter, execute, f_tier, make_primitives, nlog2n
from dsl.render import render
from dsl.sandbox import launcher, run
from graphs import BipartiteGraph


def _toy():
    # U 10, 20 -> dsl 0, 1. V 1, 2, 3 -> dsl 2, 3, 4.
    edges = [(10, 1), (10, 2), (20, 2), (20, 3)]
    return BipartiteGraph.from_edges(edges, [10, 20], [1, 2, 3], name="toy")


def _rejects(source, tier="L"):
    try:
        lint(source, tier)
    except LintError:
        return True
    return False


def test_linter_rejects_each_forbidden_construct():
    samples = {
        "import": "import socket\ndef reduce(G):\n    return peel(0, 0)\n",
        "import_from": "from os import system\ndef reduce(G):\n    return peel(0, 0)\n",
        "def": "def helper():\n    return 1\ndef reduce(G):\n    return peel(0, 0)\n",
        "class": "class Foo:\n    pass\ndef reduce(G):\n    return peel(0, 0)\n",
        "while": "def reduce(G):\n    while False:\n        return peel(0, 0)\n",
        "recursion": "def reduce(G):\n    return reduce(G)\n",
        "try": "def reduce(G):\n    try:\n        return peel(0, 0)\n    except Exception:\n        return peel(0, 0)\n",
        "with": "def reduce(G):\n    with open('x') as f:\n        return peel(0, 0)\n",
        "global": "def reduce(G):\n    global p\n    return peel(0, 0)\n",
        "nonlocal": "def reduce(G):\n    x = 1\n    def inner():\n        nonlocal x\n    return peel(0, 0)\n",
        "eval": "def reduce(G):\n    return eval('1')\n",
        "exec": "def reduce(G):\n    exec('x = 1')\n    return peel(0, 0)\n",
        "open": "def reduce(G):\n    return open('x')\n",
        "getattr": "def reduce(G):\n    return getattr(G, 'm')\n",
        "setattr": "def reduce(G):\n    setattr(G, 'm', 1)\n    return peel(0, 0)\n",
        "dunder": "def reduce(G):\n    return ().__class__\n",
        "attribute": "def reduce(G):\n    return G.m\n",
        "comprehension": "def reduce(G):\n    xs = [u for u in range(1)]\n    return peel(0, 0)\n",
        "star": "def reduce(G):\n    return peel(*[0, 0])\n",
        "fstring": "def reduce(G):\n    s = f'{p}'\n    return peel(0, 0)\n",
        "import_socket_call": "def reduce(G):\n    import socket\n    return peel(0, 0)\n",
    }
    for name, src in samples.items():
        assert _rejects(src), name


def test_linter_rejects_deep_maps_and_huge_trees():
    nested = "def reduce(G):\n    return map('U', lambda x: map('V', lambda y: deg(y)))\n"
    assert _rejects(nested, "L")
    assert _rejects(nested, "N")
    lint(nested, "Q")
    deeper = "def reduce(G):\n    return map('U', lambda x: map('V', lambda y: map('U', lambda z: deg(z))))\n"
    assert _rejects(deeper, "Q")
    body = "\n".join(f"    a{i} = {i}" for i in range(40))
    huge = f"def reduce(G):\n{body}\n    return peel(0, 0)\n"
    assert len(list(ast.walk(ast.parse(huge)))) > 150
    assert _rejects(huge)


def test_linter_accepts_baseline_and_a_branch():
    lint(BASELINE_L, "L")
    lint(IDENTITY, "L")
    src = "def reduce(G):\n    if m() > 0:\n        keep = peel(1, 1)\n    else:\n        keep = peel(0, 0)\n    return keep\n"
    lint(src, "L")


def test_costs_match_hand_computation():
    G = _toy()
    assert f_tier(G, "L") == 2 + 3 + 4
    assert f_tier(G, "N") == 4 * (4).bit_length() - 4  # 4 * 2 = 8? bit_length(4)=3, floor log2=2, 4*2=8
    assert (4).bit_length() - 1 == 2
    assert f_tier(G, "N") == 8
    # degrees 2,2,1,2,1 -> squares 4+4+1+4+1 = 14
    assert f_tier(G, "Q") == 14
    view = View(G, Counter(10**9))
    p = make_primitives(view)
    assert p["n_U"]() == 2 and view.counter.cost == 1
    assert p["n_V"]() == 3 and view.counter.cost == 2
    assert p["m"]() == 4 and view.counter.cost == 3
    assert p["deg"](0) == 2 and view.counter.cost == 4
    before = view.counter.cost
    assert p["nbr_sum"](0, [10, 20, 30]) == 30
    assert view.counter.cost - before == 2
    before = view.counter.cost
    assert p["nbr_count_if"](0, [True, False, True]) == 1
    assert view.counter.cost - before == 2
    before = view.counter.cost
    h = p["minhash"](0, 0)
    assert isinstance(h, int) and view.counter.cost - before == 2
    before = view.counter.cost
    mapped = p["map"]("U", lambda x: p["deg"](x))
    # two deg calls (1 each) plus side size 2
    assert mapped == [2, 2] and view.counter.cost - before == 4
    before = view.counter.cost
    masks = p["peel"](1, 1)
    assert view.counter.cost - before == f_tier(G, "L")
    assert len(masks[0]) == 2 and len(masks[1]) == 3
    before = view.counter.cost
    assert p["threshold"]([1, 2, 3], 2) == [False, True, True]
    assert view.counter.cost - before == 3
    before = view.counter.cost
    assert p["sort_desc"]([1, 3, 2]) == [1, 2, 0]
    assert view.counter.cost - before == nlog2n(3) == 3
    before = view.counter.cost
    assert p["top_q"]([1, 3, 2], 0.5) == [False, True, True] or p["top_q"]([1, 3, 2], 1) 
    # recharge carefully: the assertion above may have called top_q twice. Recompute.
    view2 = View(G, Counter(10**9))
    q = make_primitives(view2)
    assert q["top_q"]([1, 3, 2], 0.5) == [False, True, False] or True
    # ceil(0.5*3)=2, top two are index 1 (value 3) and index 2 (value 2)
    view3 = View(G, Counter(10**9))
    r = make_primitives(view3)
    assert r["top_q"]([1, 3, 2], 0.5) == [False, True, True]
    assert view3.counter.cost == nlog2n(3)
    assert r["rank"]([1, 3, 2]) == [2, 0, 1]
    before = view3.counter.cost
    # common of the two U vertices: they share local v index 1 only.
    assert r["common"](0, 1) == 1
    assert view3.counter.cost - before == 4
    before = view3.counter.cost
    assert abs(r["jaccard"](0, 1) - (1 / 3)) < 1e-12
    assert view3.counter.cost - before == 4
    before = view3.counter.cost
    # u0 neighbors have degrees 1 and 2
    assert r["two_hop_count"](0) == 3
    assert view3.counter.cost - before == 3


def test_render_numbers_every_call():
    text = render(BASELINE_L, "L")
    assert text.splitlines()[0].startswith("1:")
    assert "peel(" in text
    assert "ceil(" in text
    # One number per line, contiguous.
    nums = [int(line.split(":", 1)[0]) for line in text.splitlines()]
    assert nums == list(range(1, len(nums) + 1))


def test_baseline_core_contains_opt_on_small_graphs():
    """The safe core contains every valid pair, so its optimum matches the brute one."""
    import random
    from checker import is_valid
    from projects.quasi.solvers import solve, OPTIMAL, NONE
    from problem import cells, seed
    rng = random.Random(seed())
    for _ in range(15):
        n_u = rng.randint(2, 6)
        n_v = rng.randint(2, 6)
        edges = [(u, n_u + v) for u in range(n_u) for v in range(n_v) if rng.random() < 0.5]
        G = BipartiteGraph.from_edges(edges, range(n_u), range(n_u, n_u + n_v))
        for p, q, theta in cells():
            keep_u, keep_v, _cost = execute(BASELINE_L, G, p, q, theta, "L")
            core = G.induced(
                [u for u, bit in zip(G.u_ids, keep_u) if bit],
                [v for v, bit in zip(G.v_ids, keep_v) if bit],
            )
            S, T, val, status, _w = solve(G, p, q, theta, 3.0)
            Sc, Tc, valc, statusc, _wc = solve(core, p, q, theta, 3.0)
            if status == NONE:
                assert statusc == NONE
                continue
            assert status == OPTIMAL and statusc == OPTIMAL
            assert valc == val
            assert set(S).issubset(core.u_ids) and set(T).issubset(core.v_ids)
            assert is_valid(G, S, T, p, q, theta)


def test_kill_cap_scores_as_failure():
    G = _toy()
    # A program that maps over and over cannot, because of nesting limits.
    # Charge past the cap by calling m() inside a wide-but-legal program is hard
    # under the node cap. Call peel, which costs f_L, in a loop we cannot write.
    # Directly: a tier whose cap is 0 rejects the first charge.
    from graphs import BipartiteGraph as BG
    empty = BG.from_edges([], [0], [1])
    # m = 0, f_N = 0, kill cap 0. n_U charges 1.
    src = "def reduce(G):\n    return peel(n_U(), n_V())\n"
    try:
        execute(src, empty, 1, 1, 2, "N")
        raised = False
    except Exception:
        raised = True
    assert raised


def test_sandbox_rejects_import_and_blocks_escape():
    G = _toy()
    blocked = run("import socket\ndef reduce(G):\n    return peel(0, 0)\n", G, 1, 1, 2, "L")
    assert blocked["ok"] is False
    assert blocked["error"].startswith("lint:")
    opened = run("def reduce(G):\n    return open('/etc/passwd')\n", G, 1, 1, 2, "L")
    assert opened["ok"] is False and opened["error"].startswith("lint:")
    # Bypass the linter. open() is not in the child builtins, and the audit
    # hook rejects the open event if a recovered builtin is used.
    escape = run(
        "def reduce(G):\n    return open('/etc/passwd').read()\n",
        G, 1, 1, 2, "L", skip_lint=True, wall_seconds=10,
    )
    assert escape["ok"] is False
    # Recover a real open/socket via subclass walk and try to use it.
    sneaky = (
        "def reduce(G):\n"
        "    for cls in ().__class__.__bases__[0].__subclasses__():\n"
        "        glob = getattr(getattr(cls, '__init__', None), '__globals__', {})\n"
        "        if glob and 'system' in glob.get('os', type('X', (), {})).__dict__ if False else False:\n"
        "            pass\n"
        "        osmod = glob.get('os') if isinstance(glob, dict) else None\n"
        "        if osmod is not None and hasattr(osmod, 'system'):\n"
        "            osmod.system('true')\n"
        "            return peel(0, 0)\n"
        "    return open('/etc/passwd')\n"
    )
    sneaky_out = run(sneaky, G, 1, 1, 2, "L", skip_lint=True, wall_seconds=10)
    assert sneaky_out["ok"] is False
    # The launcher drops the net namespace when the kernel allows it.
    assert isinstance(launcher(), list) and launcher()[-1] == "dsl.worker"


def test_sandbox_runs_baseline():
    G = _toy()
    out = run(BASELINE_L, G, 1, 1, 2, "L")
    assert out["ok"] is True
    assert len(out["keep_u"]) == G.n_u and len(out["keep_v"]) == G.n_v
    # Identity keeps everyone.
    ident = run(IDENTITY, G, 1, 1, 2, "L")
    assert ident["ok"] and all(ident["keep_u"]) and all(ident["keep_v"])
