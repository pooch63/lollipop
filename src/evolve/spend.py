"""Dollar cap for evolver LLM calls. The ledger file stores totals, never a key."""

from __future__ import annotations

import fcntl
import json
import os
from copy import copy

from openevolve.llm.openai import OpenAILLM

from problem import ROOT, SRC

SPEND_PATH = SRC / "evolve" / "llm_spend.json"
CAP_DOLLARS = 4.0
# Published standard rates, dollars per token. Input is charged in full
# (cached tokens are not discounted) so the cap cannot be slipped by a guess.
PRICES = {
    "gpt-5-mini": (0.25 / 1_000_000, 2.00 / 1_000_000),
}
# Unknown model ids are charged high so a surprise model still stops at $4.
DEFAULT_PRICE = (10.0 / 1_000_000, 50.0 / 1_000_000)


class SpendCapReached(RuntimeError):
    pass


def _read(path) -> dict:
    if not path.exists():
        return {"dollars": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
    return json.loads(path.read_text())


def spent(path=None) -> float:
    return float(_read(path or SPEND_PATH).get("dollars", 0.0))


def _add(usage: dict, model: str, path) -> float:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        raw = handle.read()
        state = json.loads(raw) if raw.strip() else {
            "dollars": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "calls": 0
        }
        prompt = int(usage.get("prompt_tokens") or 0)
        completion = int(usage.get("completion_tokens") or 0)
        in_rate, out_rate = PRICES.get(model, DEFAULT_PRICE)
        if prompt == 0 and completion == 0:
            # The API returned no usage. Count a small amount so a silent
            # client cannot run past the cap.
            dollars = 0.02
        else:
            dollars = prompt * in_rate + completion * out_rate
        state["dollars"] = float(state.get("dollars", 0.0)) + dollars
        state["prompt_tokens"] = int(state.get("prompt_tokens", 0)) + prompt
        state["completion_tokens"] = int(state.get("completion_tokens", 0)) + completion
        state["calls"] = int(state.get("calls", 0)) + 1
        state["model"] = model
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(state))
        handle.flush()
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return float(state["dollars"])


class CappedLLM:
    """Stop calling the API once recorded spend reaches the cap."""

    def __init__(self, inner, cap: float = CAP_DOLLARS, path=None):
        self.inner = inner
        self.cap = float(cap)
        self.path = path or SPEND_PATH

    async def generate(self, prompt: str, **kwargs) -> str:
        self._refuse_if_spent()
        text = await self.inner.generate(prompt, **kwargs)
        self._charge()
        return text

    async def generate_with_context(self, system_message: str, messages, **kwargs) -> str:
        self._refuse_if_spent()
        text = await self.inner.generate_with_context(system_message, messages, **kwargs)
        self._charge()
        return text

    def _refuse_if_spent(self) -> None:
        if spent(self.path) >= self.cap:
            raise SpendCapReached(f"LLM spend reached ${self.cap:.2f}")

    def _charge(self) -> None:
        usage = getattr(self.inner, "last_usage", None) or {}
        model = getattr(self.inner, "model", "")
        _add(usage, model, self.path)


def load_project_env(path=None) -> None:
    """Read KEY=VALUE lines from the repo .env. An existing environment value wins."""
    path = ROOT / ".env" if path is None else path
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip("'").strip('"')
        if name and name not in os.environ:
            os.environ[name] = value


def openai_api_key() -> str:
    load_project_env()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Set OPENAI_API_KEY in .env")
    return key


def init_capped_client(model_cfg):
    """Build the real client from the environment. Does not store the key on model_cfg."""
    key = openai_api_key()
    local = copy(model_cfg)
    local.api_key = key
    return CappedLLM(OpenAILLM(local))
