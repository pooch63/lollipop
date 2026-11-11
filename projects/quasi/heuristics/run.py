"""OpenEvolve run that rewrites search(). Stops at its own $4 cap.

Does not start the N or Q reduction tiers. Does not call the mock.
Spend is recorded in heuristics/spend.json, separate from the
reduction smoke ledger.
"""

from __future__ import annotations

import asyncio
import os
from copy import copy
from pathlib import Path

from openevolve.config import Config
from openevolve.controller import OpenEvolve
from openevolve.llm.openai import OpenAILLM

from archive_export import export_tier, programs_from_database
from evolve.protect import assert_evolver_readonly
from evolve.spend import CAP_DOLLARS, CappedLLM, openai_api_key, spent
from problem import ROOT
from projects.quasi.heuristics.evaluate import INITIAL_PATH
from projects.quasi.heuristics.prompt import SEARCH_RULES
from store import add_run, connect, seed_search_hypotheses

HERE = Path(__file__).resolve().parent
MODEL = "gpt-5-mini"
ITERATIONS = 40
HYPOTHESIS_ID = "HS1"
SPEND_PATH = HERE / "spend.json"


def init_search_client(model_cfg):
    key = openai_api_key()
    local = copy(model_cfg)
    local.api_key = key
    return CappedLLM(OpenAILLM(local), cap=CAP_DOLLARS, path=SPEND_PATH)


def load_config(claim: str) -> Config:
    cfg = Config.from_yaml(HERE / "openevolve.yaml")
    cfg.max_iterations = ITERATIONS
    cfg.llm.models[0].name = MODEL
    cfg.llm.models[0].temperature = 0.7
    cfg.llm.models[0].max_tokens = 4000
    cfg.llm.models[0].timeout = 120
    cfg.llm.models[0].reasoning_effort = "low"
    cfg.llm.models[0].api_base = "https://api.openai.com/v1"
    cfg.llm.models[0].init_client = init_search_client
    cfg.prompt.system_message = SEARCH_RULES + "\nHypothesis: " + claim + "\n"
    cfg.llm.update_model_params({"system_message": cfg.prompt.system_message}, overwrite=True)
    cfg.database.population_size = 40
    cfg.database.archive_size = 40
    cfg.evaluator.parallel_evaluations = 1
    return cfg


async def run_search() -> None:
    assert_evolver_readonly()
    if spent(SPEND_PATH) >= CAP_DOLLARS:
        print(f"search spend cap ${CAP_DOLLARS:.2f} already reached", flush=True)
        return
    run_id = "search-HS1"
    os.environ["OE_ROLE"] = "evolver"
    os.environ["OE_TIER"] = "search"
    os.environ["OE_HYPOTHESIS_ID"] = HYPOTHESIS_ID
    os.environ["OE_RUN_ID"] = run_id
    conn = connect(ROOT / "hypotheses.sqlite")
    seed_search_hypotheses(conn)
    row = conn.execute("SELECT claim FROM hypotheses WHERE id=?", (HYPOTHESIS_ID,)).fetchone()
    add_run(conn, HYPOTHESIS_ID, run_id)
    cfg = load_config(row["claim"])
    output = HERE / "output"
    controller = OpenEvolve(
        initial_program_path=str(INITIAL_PATH),
        evaluation_file=str(HERE / "oe.py"),
        config=cfg,
        output_dir=str(output),
    )
    print(f"starting search iterations={ITERATIONS} spent=${spent(SPEND_PATH):.4f}", flush=True)
    try:
        await controller.run(iterations=ITERATIONS)
    except Exception as exc:
        print(f"search stopped: {type(exc).__name__}: {exc}", flush=True)
    programs = programs_from_database(controller.database)
    for program in programs:
        program["hypothesis_id"] = HYPOTHESIS_ID
        program["run_id"] = run_id
    export_tier("search", programs, HYPOTHESIS_ID, run_id)
    print(f"search kept {len(programs)} programs, spent=${spent(SPEND_PATH):.4f}", flush=True)


def main() -> None:
    asyncio.run(run_search())


if __name__ == "__main__":
    main()
