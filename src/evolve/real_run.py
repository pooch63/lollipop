"""L-tier smoke: H1 and H2, 40 iterations each, real model, $4 total cap.

Stops after these two runs. Does not start N or Q, and does not promote.
"""

from __future__ import annotations

import asyncio
import json
import os

from openevolve.config import Config
from openevolve.controller import OpenEvolve

from archive_export import export_tier, programs_from_database
from dsl.programs import BASELINE_L
from evolve.dsl_prompt import TIER_L_RULES
from evolve.protect import assert_evolver_readonly
from evolve.smoke import _gate, initial_source
from evolve.spend import CAP_DOLLARS, init_capped_client, spent
from problem import ROOT, SRC
from store import add_run, connect, seed_hypotheses

MODEL = "gpt-5-mini"
ITERATIONS = 40
HYPOTHESES = ("H1", "H2")
LOG_PATH = SRC / "evolve" / "smoke_evals.jsonl"


def load_real_config(claim: str) -> Config:
    cfg = Config.from_yaml(SRC / "evolve" / "openevolve.yaml")
    cfg.max_iterations = ITERATIONS
    cfg.llm.models[0].name = MODEL
    cfg.llm.models[0].temperature = 0.7
    cfg.llm.models[0].max_tokens = 4000
    cfg.llm.models[0].timeout = 120
    cfg.llm.models[0].reasoning_effort = "low"
    cfg.llm.models[0].api_base = "https://api.openai.com/v1"
    cfg.llm.models[0].init_client = init_capped_client
    cfg.prompt.system_message = TIER_L_RULES + "\nHypothesis: " + claim + "\n"
    cfg.llm.update_model_params({"system_message": cfg.prompt.system_message}, overwrite=True)
    cfg.database.population_size = 80
    cfg.database.archive_size = 80
    cfg.database.num_islands = 1
    cfg.evaluator.parallel_evaluations = 1
    return cfg


async def run_one(hypothesis_id: str) -> list[dict]:
    assert_evolver_readonly()
    _gate()
    if spent() >= CAP_DOLLARS:
        print(f"spend cap ${CAP_DOLLARS:.2f} already reached; skipping {hypothesis_id}", flush=True)
        return []
    run_id = f"smoke-L-{hypothesis_id}"
    os.environ["OE_ROLE"] = "evolver"
    os.environ["OE_TIER"] = "L"
    os.environ["OE_HYPOTHESIS_ID"] = hypothesis_id
    os.environ["OE_RUN_ID"] = run_id
    os.environ["OE_SMOKE_LOG"] = str(LOG_PATH)
    conn = connect(ROOT / "hypotheses.sqlite")
    seed_hypotheses(conn)
    row = conn.execute("SELECT claim FROM hypotheses WHERE id=?", (hypothesis_id,)).fetchone()
    if row is None:
        raise KeyError(hypothesis_id)
    add_run(conn, hypothesis_id, run_id)
    cfg = load_real_config(row["claim"])
    program_path = SRC / "evolve" / f"initial_L_{hypothesis_id}.py"
    program_path.write_text(initial_source("L"))
    output = SRC / "evolve" / f"output_{hypothesis_id}"
    controller = OpenEvolve(
        initial_program_path=str(program_path),
        evaluation_file=str(SRC / "oe_evaluator.py"),
        config=cfg,
        output_dir=str(output),
    )
    print(f"starting {hypothesis_id} iterations={ITERATIONS} spent=${spent():.4f}", flush=True)
    try:
        await controller.run(iterations=ITERATIONS)
    except Exception as exc:
        print(f"{hypothesis_id} stopped: {type(exc).__name__}: {exc}", flush=True)
    programs = programs_from_database(controller.database)
    for program in programs:
        program["hypothesis_id"] = hypothesis_id
        program["run_id"] = run_id
    print(f"{hypothesis_id} kept {len(programs)} programs, spent=${spent():.4f}", flush=True)
    return programs


async def run_smoke() -> None:
    assert_evolver_readonly()
    _gate()
    collected = []
    for hypothesis_id in HYPOTHESES:
        collected.extend(await run_one(hypothesis_id))
    export_tier("L", collected, "H1+H2", "smoke-L")
    from evolve.summary import write_summary
    text = write_summary()
    print(text, flush=True)


def main() -> None:
    asyncio.run(run_smoke())


if __name__ == "__main__":
    main()
