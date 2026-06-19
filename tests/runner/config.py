"""Configuration loading for the test harness.

Reads config/config.json (falling back to config/config.example.json) from the repo root and
exposes a typed Config. An optional "testing" block supplies harness defaults.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# repo root = two levels up from this file (tests/runner/config.py -> repo/)
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class TestingDefaults:
    transport: str = "unary"        # text-first default; see ADR-001
    latency_ms_max: int | None = None


@dataclass
class Config:
    project_id: str
    location: str
    endpoint: str
    api_version: str
    app_id: str
    auth_account: str = ""        # expected gcloud/ADC identity; verified by auth.get_access_token
    testing: TestingDefaults = field(default_factory=TestingDefaults)

    @property
    def app_path(self) -> str:
        """Resource path of the app under test."""
        return (
            f"projects/{self.project_id}/locations/{self.location}/apps/{self.app_id}"
        )


def load_config(path: Path | None = None) -> Config:
    """Load configuration from config/config.json (or the provided path)."""
    if path is None:
        path = REPO_ROOT / "config" / "config.json"
        if not path.exists():
            path = REPO_ROOT / "config" / "config.example.json"

    raw = json.loads(path.read_text(encoding="utf-8"))
    testing_raw = raw.get("testing", {}) or {}

    return Config(
        project_id=raw.get("projectId", ""),
        location=raw.get("location", "global"),
        endpoint=raw.get("endpoint", "https://ces.googleapis.com"),
        api_version=raw.get("apiVersion", "v1"),
        app_id=raw.get("appId", ""),
        auth_account=raw.get("authAccount", ""),
        testing=TestingDefaults(
            transport=testing_raw.get("transport", "unary"),
            latency_ms_max=testing_raw.get("latencyMsMax"),
        ),
    )
