"""Unary transport - google.cloud.ces.v1.SessionService.RunSession over REST.

Confirmed CES v1 contract (verified live against the platform):
  POST {endpoint}/{version}/{session}:runSession
  body: {"config": {"session": "<session resource>"},
         "inputs": [ {"variables": {...}}?, {"text": "<user text>"} ]}
  reply: outputs[-1].text   (response also has turnCompleted, turnIndex, diagnosticInfo)

SessionInput is a oneof 'input_type' - `text` and `variables` are SEPARATE input entries, so
session variables are sent as their own {"variables": {...}} entry *before* the text entry,
seeded once on the first turn. Uses stdlib urllib (no extra dependency).
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

from .. import auth
from .base import TurnResult


class UnaryTransport:
    def __init__(self, config) -> None:
        self.config = config
        self._session_name: str | None = None
        self._pending_variables: dict[str, Any] = {}
        self._token: str | None = None

    def open_session(self, app_path: str, variables: dict[str, Any]) -> None:
        session_id = f"test-{uuid.uuid4().hex[:12]}"
        self._session_name = f"{app_path}/sessions/{session_id}"
        self._pending_variables = dict(variables)
        self._token = auth.get_access_token()

    def send_turn(self, text: str) -> TurnResult:
        if not self._session_name:
            raise RuntimeError("open_session() must be called before send_turn().")

        inputs: list[dict[str, Any]] = []
        if self._pending_variables:
            inputs.append({"variables": self._pending_variables})
            self._pending_variables = {}  # seed session variables once, on the first turn
        inputs.append({"text": text})

        body = {"config": {"session": self._session_name}, "inputs": inputs}
        url = f"{self.config.endpoint}/{self.config.api_version}/{self._session_name}:runSession"

        start = time.perf_counter()
        raw = self._post(url, body)
        latency_ms = (time.perf_counter() - start) * 1000

        outputs = raw.get("outputs", []) if isinstance(raw, dict) else []
        texts = [o.get("text", "") for o in outputs if o.get("text")]
        reply = texts[-1] if texts else ""  # agent's reply is the last text output of the turn
        return TurnResult(reply_text=reply, latency_ms=latency_ms, raw=raw)

    def close(self) -> None:
        self._session_name = None
        self._token = None

    def _post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("x-goog-user-project", self.config.project_id)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"runSession HTTP {exc.code}: {detail}") from exc
