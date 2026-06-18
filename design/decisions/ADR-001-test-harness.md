# ADR-001: RPC-driven regression test harness

- **Status:** Accepted
- **Date:** 2026-06-18
- **Deciders:** Lee, Claude

## Context
We need a repeatable way to validate the agent behaves as expected after major changes —
before building the agent itself. The platform offers two ways to run a session over the RPC API
(`google.cloud.ces.v1.SessionService`):

- `runSession` — unary (one request → one response).
- `streamRunSession` — bidirectional streaming ("bidi"); the production runtime path, and the
  only path that carries audio/voice and streaming partial responses.

Constraints from Lee:
- Support **both** transports, but make **text rock-solid first**.
- **Modular**, easy to configure and administer.
- Must be able to **start sessions and pass in data variables** the agent needs.
- Runner in **Python**.
- Build the **plan + skeleton now**; the agent/app doesn't exist yet and some gRPC details are
  still unconfirmed.

## Decision
Build a **declarative, data-driven test harness** in Python:

- **Test cases are YAML data** (`tests/cases/*.yaml`): a scripted multi-turn conversation plus
  per-turn assertions. No code needed to add a test.
- **Transport is pluggable** behind a single `Transport` interface, with three implementations:
  `unary` (runSession), `bidi` (streamRunSession), and `mock` (canned responses, so the harness
  logic is testable today before gRPC is wired).
- **Text first:** the default transport is `unary` while we stabilize text regression; `bidi` is
  fully scaffolded and becomes default once voice/streaming matters.
- **Session variables** are first-class: each case can declare `session.variables`, passed at
  session start via `SessionConfig`/`SessionInput`.
- **One command, one exit code** (`scripts/run-tests.ps1`): non-zero on any failure, so it gates
  "after major changes" and later slots into CI / pre-deploy.
- This harness **complements**, not replaces, the platform's server-side **evaluations** (a
  documented best practice). Harness = fast outer loop we control; evaluations = server-side pin.

### Build/run split
- **Build & administer** the app (REST API, `dialogflow.googleapis.com`) — per earlier decision.
- **Run & test** sessions over the **RPC API** (`SessionService`) — this ADR.

## Consequences
- Adds a Python dependency (grpcio, google-auth, pyyaml) to an otherwise PowerShell/JSON repo.
- The `unary`/`bidi` transports are **skeletons** until we confirm: the gRPC host, how to obtain
  the `SessionService` stub (generated protos vs. a client library), and the exact
  `SessionInput`/`SessionOutput`/`SessionConfig` field names. These are marked `TODO(confirm)`.
- The `mock` transport + the case loader, assertions, orchestration, and reporter are **real and
  runnable now**, so we can validate the harness design immediately.
- Assertions start text-focused (contains/regex/latency); richer ones (tool_called, transferred,
  escalated) are stubbed pending confirmation of how `SessionOutput` surfaces those signals.

## Alternatives considered
- **REST-only / unary-only harness** — simplest, but ignores the explicit RPC/bidi requirement and
  can't validate the real streaming/voice runtime path.
- **PowerShell runner** — no new runtime, but gRPC bidi in PowerShell is impractical; would force
  unary-only. Rejected.
- **Rely solely on platform evaluations** — good, but server-side only; we lose the fast local/CI
  outer loop and fine-grained control over assertions and session variables.
