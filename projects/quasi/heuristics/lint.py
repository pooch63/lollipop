"""AST linter for an evolved search(G, p, q, theta).

Loops and helpers are allowed. This is a search procedure, not the reduction
DSL. Imports, dunder access, and the usual escape calls are rejected before
any graph is touched.
"""

from __future__ import annotations

import ast

from dsl.errors import LintError

MAX_NODES = 1500

# Calls that recover builtins or start a process. A helper with one of these
# names is still rejected at the call, so a rewrite cannot smuggle them in.
DENY_CALLS = {
    "eval", "exec", "open", "compile", "__import__", "getattr", "setattr",
    "delattr", "globals", "locals", "vars", "dir", "type", "super",
    "memoryview", "classmethod", "staticmethod", "property", "object",
    "breakpoint", "help", "input", "exit", "quit", "copyright", "credits",
    "license",
}

# Frame and code objects. These names do not start with an underscore.
DENY_ATTRS = {
    "gi_frame", "gi_code", "gi_yieldfrom",
    "cr_frame", "cr_code", "ag_frame", "ag_code",
    "f_back", "f_globals", "f_locals", "f_code", "f_builtins",
    "tb_frame", "tb_next", "mro",
}

_ALLOWED = {
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg,
    ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr,
    ast.Name, ast.Load, ast.Store,
    ast.Constant,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.UnaryOp, ast.UAdd, ast.USub, ast.Not, ast.Invert,
    ast.BoolOp, ast.And, ast.Or,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.If, ast.IfExp,
    ast.For, ast.While, ast.Break, ast.Continue, ast.Pass,
    ast.Return, ast.Tuple, ast.List, ast.Set, ast.Dict,
    ast.Subscript, ast.Slice,
    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.comprehension,
    ast.Call, ast.Lambda, ast.keyword, ast.Expr, ast.Attribute,
    ast.Assert, ast.Delete, ast.Global, ast.Nonlocal,
}


def lint(source: str) -> ast.AST:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise LintError(f"syntax error: {exc}") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_NODES:
        raise LintError(f"AST node count {len(nodes)} exceeds {MAX_NODES}")
    for node in nodes:
        if type(node) not in _ALLOWED:
            raise LintError(f"forbidden syntax: {type(node).__name__}")
        if isinstance(node, ast.Name) and _hidden(node.id):
            raise LintError(f"hidden name {node.id}")
        if isinstance(node, ast.Attribute):
            _check_attr(node.attr)
        if isinstance(node, ast.arg) and _hidden(node.arg):
            raise LintError(f"hidden name {node.arg}")
        if isinstance(node, ast.FunctionDef) and _hidden(node.name):
            raise LintError(f"hidden name {node.name}")
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            for name in node.names:
                if _hidden(name):
                    raise LintError(f"hidden name {name}")
        if isinstance(node, ast.Call):
            _check_call(node)
    _check_structure(tree)
    return tree


def _hidden(name: str) -> bool:
    return name.startswith("_") or name.endswith("__")


def _check_attr(name: str) -> None:
    if _hidden(name) or name in DENY_ATTRS:
        raise LintError(f"forbidden attribute: {name}")


def _check_call(node: ast.Call) -> None:
    for arg in node.args:
        if isinstance(arg, ast.Starred):
            raise LintError("star-args are forbidden")
    for keyword in node.keywords:
        if keyword.arg is None:
            raise LintError("star-args are forbidden")
    func = node.func
    if isinstance(func, ast.Name):
        if func.id in DENY_CALLS:
            raise LintError(f"forbidden call: {func.id}")
        return
    if isinstance(func, ast.Attribute):
        _check_attr(func.attr)
        return
    if isinstance(func, ast.Lambda):
        return
    if isinstance(func, ast.Subscript):
        raise LintError("only direct function calls are allowed")
    raise LintError("only direct function calls are allowed")


def _check_structure(tree: ast.AST) -> None:
    funcs = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    others = [node for node in tree.body if not isinstance(node, (ast.FunctionDef, ast.Assign, ast.AnnAssign))]
    if others or not funcs:
        raise LintError("module must be helper functions plus def search(G, p, q, theta)")
    searches = [node for node in funcs if node.name == "search"]
    if len(searches) != 1:
        raise LintError("module must define search exactly once")
    fn = searches[0]
    if fn.decorator_list:
        raise LintError("decorators are forbidden")
    args = fn.args
    if args.vararg or args.kwarg or args.kwonlyargs or args.defaults or args.posonlyargs:
        raise LintError("search takes exactly (G, p, q, theta)")
    names = [arg.arg for arg in args.args]
    if names != ["G", "p", "q", "theta"]:
        raise LintError("search takes exactly (G, p, q, theta)")
