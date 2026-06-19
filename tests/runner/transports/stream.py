"""Stream transport - google.cloud.ces.v1.SessionService.stream_run_session.

Server-streaming: each turn sends one RunSessionRequest and reads a stream of partial
RunSessionResponse messages (incremental text chunks, since enable_text_streaming=True).
Multi-turn conversations continue server-side via the shared session id, same as unary.

Note: true bidirectional streaming (`bidi_run_session`) is NOT served at ces.googleapis.com for
this project/location - it returns HTTP 404 - so the harness validates the server-streaming path.
Uses the official `google-cloud-ces` client (pip install -r tests/requirements.txt).
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from .. import auth
from .base import TurnResult


class StreamTransport:
    def __init__(self, config) -> None:
        self.config = config
        self._client = None
        self._ces = None
        self._session_name: str | None = None
        self._pending_variables: dict[str, Any] = {}

    def open_session(self, app_path: str, variables: dict[str, Any]) -> None:
        from google.cloud import ces_v1
        from google.oauth2.credentials import Credentials

        self._ces = ces_v1
        self._pending_variables = dict(variables)
        self._session_name = f"{app_path}/sessions/test-{uuid.uuid4().hex[:12]}"

        host = self.config.endpoint.split("://", 1)[-1]  # ces.googleapis.com
        creds = Credentials(token=auth.get_access_token(self.config.auth_account))
        creds = creds.with_quota_project(self.config.project_id)
        self._client = ces_v1.SessionServiceClient(
            credentials=creds, client_options={"api_endpoint": f"{host}:443"}
        )

    def send_turn(self, text: str) -> TurnResult:
        if self._client is None:
            raise RuntimeError("open_session() must be called before send_turn().")
        ces_v1 = self._ces

        inputs = []
        if self._pending_variables:
            inputs.append(ces_v1.SessionInput(variables=self._pending_variables))  # seed once
            self._pending_variables = {}
        inputs.append(ces_v1.SessionInput(text=text))

        request = ces_v1.RunSessionRequest(
            config=ces_v1.SessionConfig(session=self._session_name, enable_text_streaming=True),
            inputs=inputs,
        )

        start = time.perf_counter()
        texts: list[str] = []
        tools: list[str] = []
        for resp in self._client.stream_run_session(request=request):
            for out in resp.outputs:
                if out.text:
                    texts.append(out.text)  # incremental chunk
                try:  # bonus signal; never let it break a turn
                    for tc in out.tool_calls.tool_calls:
                        tools.append(tc.name)
                except Exception:
                    pass
        latency_ms = (time.perf_counter() - start) * 1000
        return TurnResult(reply_text="".join(texts), latency_ms=latency_ms, tools_called=tools)

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.transport.close()
            except Exception:
                pass
            self._client = None
