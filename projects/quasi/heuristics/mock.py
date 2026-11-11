"""Deterministic stand-in for the search evolver. No network.

The first and third replies fail the linter. The second is a legal search
that returns nothing, so stage 1 runs and scores 0.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
COUNTER = HERE / "mock_calls.txt"

VARIANTS = [
    "```python\nimport os\n\ndef search(G, p, q, theta):\n    return [], []\n```",
    "```python\ndef search(G, p, q, theta):\n    return [], []\n```",
    "```python\ndef search(G, p, q, theta):\n    return eval('[]'), []\n```",
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
        if system_message is None:
            raise RuntimeError("mock LLM was called without a system message")
        return next_response()


def init_mock_client(model_cfg):
    return MockLLM()
