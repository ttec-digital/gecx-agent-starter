"""Mock transport — canned, deterministic replies.

Lets us exercise the full harness (case loading, assertions, reporting, session variables)
with no live app or gRPC stub. Useful for developing the harness itself and for CI smoke
checks of the harness wiring. Reply rules are intentionally trivial and keyword-based.
"""
from __future__ import annotations

import time
from typing import Any

from .base import TurnResult


class MockTransport:
    def __init__(self, config) -> None:
        self.config = config
        self._variables: dict[str, Any] = {}
        self._opened = False

    def open_session(self, app_path: str, variables: dict[str, Any]) -> None:
        self._variables = dict(variables)
        self._opened = True

    def send_turn(self, text: str) -> TurnResult:
        if not self._opened:
            raise RuntimeError("open_session() must be called before send_turn().")

        start = time.perf_counter()
        reply = self._canned_reply(text)
        latency_ms = (time.perf_counter() - start) * 1000
        return TurnResult(reply_text=reply, latency_ms=latency_ms, raw={"mock": True})

    def close(self) -> None:
        self._opened = False

    def _canned_reply(self, text: str) -> str:
        lowered = text.lower()
        if any(g in lowered for g in ("hi", "hello", "hey")):
            name = self._variables.get("customer_name", "there")
            return f"Hello {name}, how can I help you today?"
        if "order" in lowered:
            return "Your order has shipped and is in transit."
        return "I can help with that. Could you tell me a bit more?"
