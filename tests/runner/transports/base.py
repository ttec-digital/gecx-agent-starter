"""Transport interface — the seam between the harness and the RPC SessionService.

Every transport (unary runSession, bidi streamRunSession, mock) implements this small
interface, so the orchestration/assertion/report code is identical regardless of how turns
are actually delivered. This is the modularity boundary from ADR-001.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class TurnResult:
    """Normalized result of one user turn, transport-agnostic."""

    reply_text: str
    latency_ms: float
    # Signals parsed from SessionOutput once confirmed (see TODO(confirm) in unary/bidi):
    tools_called: list[str] = field(default_factory=list)
    transferred_to: str | None = None
    validation_errors: list[str] = field(default_factory=list)
    raw: Any = None  # underlying response, for debugging


class Transport(Protocol):
    """Drives a single conversation/session against the agent."""

    def open_session(self, app_path: str, variables: dict[str, Any]) -> None:
        """Start a fresh session, seeding any data variables the agent needs."""
        ...

    def send_turn(self, text: str) -> TurnResult:
        """Send one user message; return the normalized agent reply."""
        ...

    def close(self) -> None:
        """Tear down the session / channel."""
        ...
