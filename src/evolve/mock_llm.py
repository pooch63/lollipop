"""Deterministic stand-in for the evolver LLM. No network.

Each call returns the next full-rewrite in a python fence. The variants are
lint failures, so a smoke run exercises parsing and the stage-1 filter without
a second full-grid solve. The initial program is still the real baseline.
"""

from __future__ import annotations

from pathlib import Path

from problem import SRC

COUNTER = SRC / "evolve" / "mock_calls.txt"

# All three fail the linter, so stage 1 scores 0 and stage 2 is not started.
VARIANTS = [
    "```python\nimport socket\n\ndef reduce(G):\n    return peel(0, 0)\n```",
    "```python\ndef reduce(G):\n    return open('x')\n```",
    "```python\ndef reduce(G):\n    while True:\n        return peel(0, 0)\n```",
]


def next_response() -> str:
    n = 0
    if COUNTER.exists():
        text = COUNTER.read_text().strip()
        n = int(text) if text else 0
    COUNTER.parent.mkdir(parents=True, exist_ok=True)
    COUNTER.write_text(str(n + 1))
    return VARIANTS[n % len(VARIANTS)]


class MockLLM:
    async def generate(self, prompt: str, **kwargs) -> str:
        return next_response()

    async def generate_with_context(self, system_message: str, messages, **kwargs) -> str:
        # The hypothesis claim is supposed to be in the system message. Keep the
        # argument live so a missing prompt would be a caller bug, not a dead param.
        if system_message is None:
            raise RuntimeError("mock LLM was called without a system message")
        return next_response()


def init_mock_client(model_cfg):
    return MockLLM()
