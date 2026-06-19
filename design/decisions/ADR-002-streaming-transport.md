# ADR-002: Streaming transport = server-streaming (not true bidi), + ADC identity guard

- **Status:** Accepted
- **Date:** 2026-06-19
- **Deciders:** Project team

## Context
We set out to wire the harness's streaming transport as **true bidirectional streaming**
(`SessionService.bidi_run_session`) over gRPC, using the official `google-cloud-ces` client.

Two things surfaced when testing against the live project (`eu`):

1. **`bidi_run_session` is not served.** It returns HTTP **404** at `ces.googleapis.com:443`,
   while `run_session` and `stream_run_session` reach the service at the *same* endpoint (they
   returned 403/200, not 404). A 404 vs 403 is decisive: the bidi method isn't registered for this
   project/location. The regional host `eu-ces.googleapis.com` 404s entirely; the working host is
   the global `ces.googleapis.com` with the location in the resource path.

2. **The harness was authenticating as the wrong account.** `get_access_token()` prefers ADC
   (`google.auth.default()`), and ADC pointed at a *personal* account that lacked
   `ces.sessions.runSession` → 403. gcloud's *active* account was correct, but ADC is a **separate
   credential store** that the `check-auth` hook never inspected, so the mismatch was silent.

## Decision
1. **Use `stream_run_session` (server-streaming) for the `stream` transport.** Each turn sends one
   `RunSessionRequest` and reads a stream of partial `RunSessionResponse` chunks
   (`enable_text_streaming=true`); multi-turn state continues server-side via the shared session id.
   This validates the streaming path with the same library and auth. The transport is named
   `stream` (honest) rather than `bidi`.
2. **Defer true bidi** until `bidi_run_session` is enabled for the project (likely tied to realtime
   audio/voice). The code is removed, not stubbed, to avoid implying it works.
3. **Guard the identity.** `auth.get_access_token(expected_account)` verifies the token's email
   (via the tokeninfo endpoint, cached) against `authAccount` and fails loudly on mismatch.
   `scripts/check-auth.ps1` now checks **both** the gcloud active account *and* ADC.

## Consequences
- The `stream` transport exercises streaming responses (and seeds session variables) but is *not*
  the full realtime/bidi path; audio/barge-in testing remains future work.
- Adds a dependency on `google-cloud-ces` (pulls grpcio, proto-plus, protobuf).
- The identity guard makes a wrong-account setup fail with a clear remediation instead of a
  confusing 403 — at the cost of one tokeninfo call per distinct token.
- `tests/runner/transports/_stubs/` was removed (we use the published client, not hand-generated
  stubs).

## Alternatives considered
- **Keep chasing true bidi** (regional endpoints, enablement) — blocked: no reachable endpoint
  serves it today; needs project/product configuration we don't control.
- **Hand-generate gRPC stubs from the public `.proto`** — unnecessary now that the official
  `google-cloud-ces` client exists and works.
- **Make the harness prefer the gcloud active account over ADC** — rejected; ADC-first is the
  conventional, CI-portable choice. Verifying identity is safer than swapping the precedence.
