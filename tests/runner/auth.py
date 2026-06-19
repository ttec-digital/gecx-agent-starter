"""Authentication for the harness API calls.

Prefers Application Default Credentials via google-auth; falls back to the gcloud CLI
(`gcloud auth print-access-token`). When an expected account is supplied, the token's identity
is verified against it - this catches the classic "ADC is a different account than you think"
trap (e.g. ADC pointing at a personal account that lacks access). See docs/authentication.md.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

_verified_tokens: set[str] = set()  # cache so we hit the tokeninfo endpoint at most once per token


def get_access_token(expected_account: str | None = None) -> str:
    """Return a short-lived OAuth2 bearer token.

    1) Application Default Credentials via google-auth (user creds, service accounts, CI).
    2) Fallback: `gcloud auth print-access-token`.

    If `expected_account` is set, verify the token actually belongs to it and raise a clear,
    actionable error otherwise.
    """
    token = _raw_token()
    if expected_account:
        _verify_identity(token, expected_account)
    return token


def _raw_token() -> str:
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


def _verify_identity(token: str, expected: str) -> None:
    if token in _verified_tokens:
        return
    email = _token_email(token)
    if email and email.lower() != expected.lower():
        raise RuntimeError(
            f"Auth identity mismatch: the active credential is for {email!r}, but config "
            f"'authAccount' is {expected!r}. Your harness calls would use the wrong account.\n"
            f"Fix your Application Default Credentials:\n"
            f"  gcloud auth application-default login {expected}"
        )
    _verified_tokens.add(token)  # cache even when email is unknown (best-effort)


def _token_email(token: str) -> str | None:
    """Best-effort identity lookup via the public tokeninfo endpoint; None on any failure."""
    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?access_token={token}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.load(resp).get("email")
    except Exception:
        return None


def get_credentials():
    """Return raw ADC credentials (for building gRPC call credentials)."""
    import google.auth

    credentials, _ = google.auth.default(scopes=[CLOUD_PLATFORM_SCOPE])
    return credentials
