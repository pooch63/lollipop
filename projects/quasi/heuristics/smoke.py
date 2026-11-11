"""Three-iteration OpenEvolve smoke for the search program. Mock LLM, no API spend.

Stage 2 stays off: the cascade threshold is above any clipped rho, so only
the two smallest dev cells are solved. Does not consult the identity-control
gate. That gate measures the reduction solver, not this search. CPU time goes
to a side ledger so a wiring run does not spend the shared budget, and this
smoke does not write archive/search.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from openevolve.config import Config
from openevolve.controller import OpenEvolve

from evolve.protect import assert_evolver_readonly
from projects.quasi.heuristics.evaluate import INITIAL_PATH
from projects.quasi.heuristics.mock import COUNTER, init_mock_client
from projects.quasi.heuristics.prompt import SEARCH_RULES
from store import add_run, connect, seed_search_hypotheses

HERE = Path(__file__).resolve().parent
HYPOTHESIS_ID = "HS1"


def load_smoke_config(claim: str) -> Config:
    cfg = Config.from_yaml(HERE / "openevolve.yaml")
    cfg.max_iterations = 3
    cfg.evaluator.cascade_thresholds = [1.01]
    cfg.database.population_size = 8
    cfg.database.archive_size = 8
    cfg.prompt.system_message = SEARCH_RULES + "\nHypothesis: " + claim + "\n"
    cfg.llm.models[0].init_client = init_mock_client
    cfg.llm.update_model_params({"system_message": cfg.prompt.system_message})
    return cfg


async def run_smoke(iterations: int = 3):
    assert_evolver_readonly()
    store = HERE / "search_smoke.sqlite"
    os.environ["OE_ROLE"] = "evolver"
    os.environ["OE_TIER"] = "search"
    os.environ["OE_HYPOTHESIS_ID"] = HYPOTHESIS_ID
    os.environ["OE_RUN_ID"] = "smoke-search-HS1"
    os.environ["OE_STORE"] = str(store)
    os.environ["OE_LEDGER"] = str(HERE / "search_smoke_budget.sqlite")
    conn = connect(store)
    seed_search_hypotheses(conn)
    row = conn.execute("SELECT claim FROM hypotheses WHERE id=?", (HYPOTHESIS_ID,)).fetchone()
    add_run(conn, HYPOTHESIS_ID, os.environ["OE_RUN_ID"])
    if COUNTER.exists():
        COUNTER.unlink()
    cfg = load_smoke_config(row["claim"])
    cfg.max_iterations = iterations
    output = HERE / "output_smoke"
    controller = OpenEvolve(
        initial_program_path=str(INITIAL_PATH),
        evaluation_file=str(HERE / "oe.py"),
        config=cfg,
        output_dir=str(output),
    )
    best = await controller.run(iterations=iterations)
    metrics = getattr(best, "metrics", None) or {}
    print(
        f"search smoke finished, best_id={getattr(best, 'id', None)} "
        f"rho={metrics.get('rho')} combined={metrics.get('combined_score')}",
        flush=True,
    )
    return best


def main() -> None:
    asyncio.run(run_smoke())


if __name__ == "__main__":
    main()
