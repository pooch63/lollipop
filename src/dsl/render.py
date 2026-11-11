"""Mechanical pseudocode rendering of a valid reduce program.

Each statement and each call becomes one numbered line. Nested calls are
lifted into fresh names so a line contains a single call.
"""

from __future__ import annotations

import ast

from dsl.lint import PURE, TIER_Q, lint

_CALLS = TIER_Q | PURE
_OPS = {
    ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/",
    ast.FloorDiv: "//", ast.Mod: "%", ast.Pow: "**",
}
_CMP = {
    ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=",
    ast.Gt: ">", ast.GtE: ">=",
}
_UNARY = {ast.UAdd: "+", ast.USub: "-", ast.Not: "not "}
_BOOL = {ast.And: "and", ast.Or: "or"}


def render(source: str, tier: str = "Q") -> str:
    tree = lint(source, tier)
    fn = tree.body[0]
    lines: list[str] = []
    counter = {"n": 0}

    def emit(text: str) -> None:
        counter["n"] += 1
        lines.append(f"{counter['n']}: {text}")

    def fresh() -> str:
        counter["n"] += 1
        return f"_{counter['n']}"

    def expr(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant):
            return repr(node.value)
        if isinstance(node, ast.Tuple):
            return "(" + ", ".join(expr(e) for e in node.elts) + ")"
        if isinstance(node, ast.UnaryOp):
            return f"({_UNARY[type(node.op)]}{expr(node.operand)})"
        if isinstance(node, ast.BinOp):
            return f"({expr(node.left)} {_OPS[type(node.op)]} {expr(node.right)})"
        if isinstance(node, ast.BoolOp):
            op = f" {_BOOL[type(node.op)]} "
            return "(" + op.join(expr(v) for v in node.values) + ")"
        if isinstance(node, ast.Compare):
            parts = [expr(node.left)]
            for op, right in zip(node.ops, node.comparators):
                parts.append(_CMP[type(op)])
                parts.append(expr(right))
            return "(" + " ".join(parts) + ")"
        if isinstance(node, ast.IfExp):
            return f"({expr(node.body)} if {expr(node.test)} else {expr(node.orelse)})"
        if isinstance(node, ast.Lambda):
            arg = node.args.args[0].arg
            return f"lambda {arg}: {expr(node.body)}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _CALLS:
            args = [expr(a) for a in node.args]
            name = fresh()
            # fresh() consumed a number; the emitted line uses that same number.
            lines.append(f"{counter['n']}: {name} = {node.func.id}({', '.join(args)})")
            return name
        raise ValueError(f"cannot render {type(node).__name__}")

    def target(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        return "(" + ", ".join(target(e) for e in node.elts) + ")"

    def stmt(node: ast.AST) -> None:
        if isinstance(node, ast.Assign):
            value = expr(node.value)
            emit(f"{target(node.targets[0])} = {value}")
            return
        if isinstance(node, ast.Return):
            emit(f"return {expr(node.value) if node.value else ''}")
            return
        if isinstance(node, ast.If):
            emit(f"if {expr(node.test)}:")
            for child in node.body:
                stmt(child)
            if node.orelse:
                emit("else:")
                for child in node.orelse:
                    stmt(child)
            return
        raise ValueError(f"cannot render statement {type(node).__name__}")

    for node in fn.body:
        stmt(node)
    return "\n".join(lines)
