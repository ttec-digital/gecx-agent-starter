"""Authentication for the harness HTTP (and future gRPC) calls.

Prefers Application Default Credentials via google-auth; falls back to the gcloud CLI
(`gcloud auth print-access-token`) so it works on a developer box without google-auth
installed. See docs/authentication.md.
"""
from __future__ import annotations

import shutil
import subprocess

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def get_access_token() -> str:
    """Return a short-lived OAuth2 bearer token.

    1) Application Default Credentials via google-auth (user creds, service accounts, CI).
    2) Fallback: `gcloud auth print-access-token`.
    """
    # 1) google-auth / ADC
    try:
        import google.auth
        from google.auth.transport.requests import Request

        credentials, _ = google.auth.default(scopes=[CLOUD_PLATFORM_SCOPE])
        credentials.refresh(Request())
        if credentials.token:
            return credentials.token
    except Exception:
        pass  # fall through to the gcloud CLI

    # 2) gcloud CLI fallback
    if shutil.which("gcloud"):
        result = subprocess.run(
            "gcloud auth print-access-token",
            shell=True, capture_output=True, text=True,
        )
        token = result.stdout.strip()
        if result.returncode == 0 and token:
            return token
        raise RuntimeError(
            f"gcloud auth print-access-token failed: {result.stderr.strip() or 'no token returned'}"
        )

    raise RuntimeError(
        "Could not obtain an access token. Either 'pip install -r tests/requirements.txt' and run "
        "'gcloud auth application-default login', or ensure the gcloud CLI is authenticated."
    )


def get_credentials():
    """Return raw ADC credentials (for building gRPC call credentials later)."""
    import google.auth

    credentials, _ = google.auth.default(scopes=[CLOUD_PLATFORM_SCOPE])
    return credentials
