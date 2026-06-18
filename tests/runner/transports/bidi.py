"""Bidi transport — google.cloud.ces.v1.SessionService.StreamRunSession.

The production runtime path; carries streaming partial responses and (later) audio. SKELETON:
gated behind TODO(confirm) for the same reasons as unary.py, plus the streaming send/receive
loop. Until wired, instantiating raises a clear NotImplementedError.

Streaming model: open a single bidirectional stream per session. Each user turn writes a
StreamRunSessionRequest; the agent emits one or more StreamResponse chunks per turn (partial +
final). We aggregate chunks into a single reply_text and treat the final chunk's latency as the
turn latency. For text-first work, a turn is "done" when the final/complete chunk arrives.
"""
from __future__ import annotations

import time
from typing import Any

from .base import TurnResult

# TODO(confirm): same stub-sourcing decision as unary.py.
# from ces.v1 import session_service_pb2 as pb
# from ces.v1 import session_service_pb2_grpc as pb_grpc


class BidiTransport:
    def __init__(self, config) -> None:
        self.config = config
        self._channel = None
        self._stub = None
        self._request_queue = None   # outbound StreamRunSessionRequest queue
        self._response_iter = None   # inbound StreamResponse iterator
        self._session_name: str | None = None
        self._variables: dict[str, Any] = {}

        raise NotImplementedError(
            "BidiTransport (streamRunSession) is not wired yet. Resolve the TODO(confirm) items "
            "in tests/runner/transports/bidi.py. Use --transport mock (or unary once wired) "
            "for text-first work."
        )

    # ------------------------------------------------------------------ #
    # Intended implementation sketch, kept as a guide.
    # ------------------------------------------------------------------ #
    def open_session(self, app_path: str, variables: dict[str, Any]) -> None:
        self._variables = dict(variables)
        self._session_name = f"{app_path}/sessions/test-{int(time.time()*1000)}"
        # TODO(confirm): build secure channel + stub (see unary.py), then open the bidi stream.
        # Use a thread-safe queue as the request generator; the first request seeds session
        # variables via SessionConfig. self._response_iter = self._stub.StreamRunSession(gen()).

    def send_turn(self, text: str) -> TurnResult:
        start = time.perf_counter()
        # TODO(confirm): push a StreamRunSessionRequest carrying `text`, then read StreamResponse
        # chunks until the final/complete marker; concatenate partials into reply_text.
        latency_ms = (time.perf_counter() - start) * 1000
        raise NotImplementedError("StreamRunSession loop not implemented; see TODO(confirm).")

    def close(self) -> None:
        # TODO(confirm): signal end-of-stream (close request queue) before closing the channel.
        if self._channel is not None:
            self._channel.close()
            self._channel = None
