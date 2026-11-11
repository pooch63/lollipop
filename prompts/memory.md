# Formulation contract

This file is the shape of a formulation. It is not the formulation of one problem. The define agent copies these headings into `projects/<id>/memory.md` and fills them. A finished example is `projects/quasi/memory.md`.

Leave this file unchanged.

## Name

One name for the structure being sought.

## Graph

The class of graph the problem is defined on: undirected, directed, bipartite, or something else. Say which side a vertex lives on when the graph is bipartite. Say what a solution is allowed to read (`neighbors`, degrees, edge presence).

## Parameters

Every parameter, its domain, and the integer form of any ratio. No floating-point test of feasibility.

## Solution

The object a solver or a heuristic returns. Name the sets, the tuple order, and the empty answer.

## Feasibility

The predicate in notation. Then the same predicate with integers only, if a ratio is involved.

## Objective

What is maximized or minimized, in notation.

## Planted solution

How to hide a known feasible solution in a small graph, and when that instance is too easy to score. The procedure the code must follow is `@planter.md`.

## Reduction invariant

What a reduction must keep so that a best-known solution is still feasible on the reduced graph.

## Heuristic return value

The function name, its arguments, and the value it returns. State how that return is scored against the planted solution.
