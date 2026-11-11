"""Fixed programs. The L baseline is the (ceil(p*theta/q), same)-core.

That core contains every valid gamma-quasi-biclique, so an exact solve on it
has rho = 1. The identity program keeps every vertex.
"""

BASELINE_L = """\
def reduce(G):
    keep = peel(ceil((p * theta) / q), ceil((p * theta) / q))
    return keep
"""

IDENTITY = """\
def reduce(G):
    return peel(0, 0)
"""
