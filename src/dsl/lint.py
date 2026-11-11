"""AST linter for evolved `reduce` programs.

A candidate that fails here is not executed. Tiers:
  L, N: map calls may not contain another map (depth <= 1)
  Q:    map depth <= 2
The whole tree may contain at most 150 AST nodes.
"""

from __future__ import annotations

import ast

from dsl.errors import LintError

PURE = {"min", "max", "abs", "ceil", "floor"}
TIER_L = {
    "n_U", "n_V", "m", "deg", "nbr_sum", "nbr_count_if", "minhash",
    "map", "peel", "threshold",
}
TIER_N = TIER_L | {"sort_desc", "top_q", "rank"}
TIER_Q = TIER_N | {"common", "jaccard", "two_hop_count"}
TIER_FUNCS = {"L": TIER_L, "N": TIER_N, "Q": TIER_Q}
MAP_DEPTH = {"L": 1, "N": 1, "Q": 2}
MAX_NODES = 150

# Every other node type is rejected. This is the allowlist the forbidden-construct
# tests sit on top of.
_ALLOWED_TYPES = {
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg,
    ast.Assign, ast.Name, ast.Load, ast.Store,
    ast.Constant,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.UnaryOp, ast.UAdd, ast.USub, ast.Not,
    ast.BoolOp, ast.And, ast.Or,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.If, ast.IfExp,
    ast.Return, ast.Tuple,
    ast.Call, ast.Lambda,
}


def lint(source: str, tier: str = "L") -> ast.AST:
    if tier not in TIER_FUNCS:
        raise LintError(f"unknown tier {tier}")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise LintError(f"syntax error: {exc}") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_NODES:
        raise LintError(f"AST node count {len(nodes)} exceeds {MAX_NODES}")
    for node in nodes:
        if type(node) not in _ALLOWED_TYPES:
            raise LintError(f"forbidden syntax: {type(node).__name__}")
        if isinstance(node, ast.Name) and _is_dunder(node.id):
            raise LintError(f"dunder name {node.id}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value not in ("U", "V"):
                raise LintError("only string constants 'U' and 'V' are allowed")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            if _contains_string(node):
                raise LintError("string formatting is forbidden")
    _check_structure(tree, tier)
    depth = _map_depth(tree)
    if depth > MAP_DEPTH[tier]:
        raise LintError(f"map nesting depth {depth} exceeds {MAP_DEPTH[tier]} for tier {tier}")
    return tree


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def _contains_string(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            return True
    return False


def _check_structure(tree: ast.AST, tier: str) -> None:
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    others = [n for n in tree.body if not isinstance(n, ast.FunctionDef)]
    if others or len(funcs) != 1 or funcs[0].name != "reduce":
        raise LintError("module must contain only def reduce(G)")
    fn = funcs[0]
    args = fn.args
    if args.vararg or args.kwarg or args.kwonlyargs or args.defaults or args.posonlyargs:
        raise LintError("reduce takes exactly one argument G")
    if len(args.args) != 1 or args.args[0].arg != "G":
        raise LintError("reduce takes exactly one argument G")
    if fn.decorator_list:
        raise LintError("decorators are forbidden")
    allowed = TIER_FUNCS[tier] | PURE
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    for node in ast.walk(fn):
        if isinstance(node, ast.Lambda):
            parent = parents.get(node)
            if not (isinstance(parent, ast.Call) and _call_name(parent) == "map" and len(parent.args) == 2 and parent.args[1] is node):
                raise LintError("lambdas are allowed only as the second argument of map")
            if len(node.args.args) != 1 or node.args.vararg or node.args.kwarg:
                raise LintError("map lambda takes one argument")
        if isinstance(node, ast.Call):
            name = _call_name(node)
            if name is None:
                raise LintError("only direct function calls are allowed")
            if name not in allowed:
                raise LintError(f"forbidden call: {name}")
            if node.keywords:
                raise LintError("keyword arguments are forbidden")
            for arg in node.args:
                if isinstance(arg, ast.Starred):
                    raise LintError("star-args are forbidden")
        if isinstance(node, ast.Assign):
            for target in node.targets:
                _check_target(target)


def _check_target(target: ast.AST) -> None:
    if isinstance(target, ast.Name):
        if _is_dunder(target.id):
            raise LintError(f"dunder name {target.id}")
        return
    if isinstance(target, ast.Tuple) and target.elts and all(isinstance(e, ast.Name) for e in target.elts):
        return
    raise LintError("assignment targets must be names or tuples of names")


def _call_name(node: ast.Call):
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _map_depth(tree: ast.AST) -> int:
    best = 0

    def walk(node: ast.AST, depth: int) -> None:
        nonlocal best
        for child in ast.iter_child_nodes(node):
            nxt = depth
            if isinstance(child, ast.Call) and _call_name(child) == "map":
                nxt = depth + 1
                best = max(best, nxt)
            walk(child, nxt)

    walk(tree, 0)
    return best
