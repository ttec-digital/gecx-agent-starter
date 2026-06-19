"""Transport implementations for the test harness.

Selected by name via get_transport(); keeps the runner decoupled from RPC details.
"""
from __future__ import annotations

from .base import Transport, TurnResult


def get_transport(name: str, config) -> Transport:
    """Factory: return a transport instance by name (mock | unary | stream)."""
    name = (name or "").lower()
    if name == "mock":
        from .mock import MockTransport

        return MockTransport(config)
    if name == "unary":
        from .unary import UnaryTransport

        return UnaryTransport(config)
    if name == "stream":
        from .stream import StreamTransport

        return StreamTransport(config)
    raise ValueError(f"Unknown transport {name!r}. Use one of: mock, unary, stream.")


__all__ = ["Transport", "TurnResult", "get_transport"]
