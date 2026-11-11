"""Three-iteration OpenEvolve smoke test with the mock LLM.

Refuses to start when the identity-control gate aborted or has not been run.
Does not call a real model. Credentials are never written to disk.
"""

from __future__ import annotations

import asyncio
import json
import os

from openevolve.config import Config
from openevolve.controller import OpenEvolve

from archive_export import export_tier, programs_from_database
from dsl.programs import BASELINE_L
from evolve.mock_llm import COUNTER, init_mock_client
from problem import ROOT, SRC
from store import add_run, connect, seed_hypotheses


def evolution_allowed(gate: dict) -> bool:
    return bool(gate.get("passed"))


def _gate():
    path = ROOT / "rungs" / "identity_gate.json"
    if not path.exists():
        raise SystemExit("identity-control gate has not been run; not starting evolution")
    gate = json.loads(path.read_text())
    if not evolution_allowed(gate):
        raise SystemExit("identity-control gate did not pass; not starting evolution")
    return gate


def load_smoke_config(hypothesis_claim: str) -> Config:
    cfg = Config.from_yaml(SRC / "evolve" / "openevolve.yaml")
    cfg.prompt.system_message = (
        "You write a Python function reduce(G) in the restricted graph DSL.\n"
        f"Hypothesis: {hypothesis_claim}\n"
        "Return one fenced python block and nothing else."
    )
    cfg.llm.models[0].init_client = init_mock_client
    cfg.llm.update_model_params({"system_message": cfg.prompt.system_message})
    return cfg


def initial_source(tier: str) -> str:
    """N starts from the best L program. Q starts from the best N program."""
    if tier == "L":
        return BASELINE_L
    previous = {"N": "L", "Q": "N"}[tier]
    path = ROOT / "archive" / previous / "best_rho.json"
    if not path.exists():
        raise FileNotFoundError(f"no {previous}-tier archive to seed {tier}")
    return json.loads(path.read_text())["source"]


async def run_smoke(tier: str = "L", hypothesis_id: str = "H1", iterations: int = 3):
    _gate()
    os.environ["OE_TIER"] = tier
    os.environ["OE_HYPOTHESIS_ID"] = hypothesis_id
    os.environ["OE_RUN_ID"] = f"smoke-{tier}-{hypothesis_id}"
    conn = connect(ROOT / "hypotheses.sqlite")
    seed_hypotheses(conn)
    row = conn.execute("SELECT claim FROM hypotheses WHERE id=?", (hypothesis_id,)).fetchone()
    if row is None:
        raise KeyError(hypothesis_id)
    add_run(conn, hypothesis_id, os.environ["OE_RUN_ID"])
    if COUNTER.exists():
        COUNTER.unlink()
    cfg = load_smoke_config(row["claim"])
    program_path = SRC / "evolve" / f"initial_{tier}.py"
    program_path.write_text(initial_source(tier))
    output = SRC / "evolve" / "smoke_output"
    controller = OpenEvolve(
        initial_program_path=str(program_path),
        evaluation_file=str(SRC / "oe_evaluator.py"),
        config=cfg,
        output_dir=str(output),
    )
    best = await controller.run(iterations=iterations)
    programs = programs_from_database(controller.database)
    export_tier(tier, programs, hypothesis_id, os.environ["OE_RUN_ID"])
    print(f"smoke finished, programs={len(programs)}, best_id={getattr(best, 'id', None)}")
    return best


def main() -> None:
    asyncio.run(run_smoke())


if __name__ == "__main__":
    main()
