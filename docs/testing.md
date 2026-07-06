# Testing & Validation

How we validate the agent behaves as expected after major changes. Design rationale lives in
[ADR-001](../design/decisions/ADR-001-test-harness.md).

## Two layers

| Layer | Where it runs | What it's for |
|-------|---------------|---------------|
| **RPC harness** (this repo) | Local / CI, Python | Fast outer loop. Scripted conversations + assertions over `SessionService`. We control it. |
| **Platform evaluations** | Server-side | Documented best practice. Pins expected behavior server-side; run before deploy. |

Start with the harness; add platform evaluations once the agent stabilizes.

## The RPC harness

Drives the agent over `google.cloud.ces.v1.SessionService`:
- **`runSession`** (unary) — default while we make **text** rock-solid.
- **`streamRunSession`** (`stream`) — live server-streaming path; carries streaming + future audio.
  (True `bidi_run_session` is not served here — see [ADR-002](../design/decisions/ADR-002-streaming-transport.md).)
- **`mock`** — canned responses; lets us exercise the harness with no live app.

### Layout
```
tests/
├── cases/                 # ⭐ test cases as YAML data (no code to add a test)
│   ├── _template.yaml     # annotated template — copy this
│   └── smoke-greeting.yaml
├── runner/                # modular Python package
│   ├── __main__.py        # CLI: python -m runner ...
│   ├── config.py          # loads config/config.json + env
│   ├── auth.py            # ADC bearer token
│   ├── cases.py           # parse/validate YAML cases -> dataclasses
│   ├── assertions.py      # assertion evaluators (contains/regex/latency/...)
│   ├── session.py         # turn-by-turn orchestration
│   ├── report.py          # pass/fail report + process exit code
│   └── transports/
│       ├── base.py        # Transport interface
│       ├── mock.py        # runnable today
│       ├── unary.py       # runSession over REST - LIVE (validates the real agent)
│       └── stream.py      # stream_run_session over gRPC - LIVE (server-streaming)
└── requirements.txt
```

### Test case schema
```yaml
name: order-status-happy          # unique id
description: User asks order status; agent retrieves and reports it
transport: unary                  # unary | stream | mock  (optional; default from config)

session:
  variables:                      # data variables handed to the agent at session start
    customer_id: "C-1001"
    channel: "web"

turns:
  - user: "Where is order 12345?"
    expect:
      - contains: "shipped"       # case-insensitive substring
      - regex: "(shipped|in transit|delivered)"
      - not_contains: "error"
      - latency_ms_max: 5000
      # planned, pending SessionOutput confirmation:
      # - tool_called: get_order_status
      # - transferred_to: escalation_agent
      # - escalated: false

final:                            # optional end-of-conversation checks
  expect:
    - no_validation_errors: true
```

Each case runs in a **fresh session** for isolation.

### Running
```powershell
# Install deps once
pip install -r tests/requirements.txt

# Run everything (default transport from config)
./scripts/run-tests.ps1

# Or directly, with options
python -m runner --cases tests/cases --transport mock
python -m runner --cases tests/cases --transport unary --case order-status-happy
```
Exit code is non-zero if any case fails — that's the gate to run after major changes.

## Configuration
The runner reads [`config/config.json`](../config/config.example.json) for `projectId`, `location`,
`endpoint`, and `appId`, plus an optional `testing` block for defaults (default transport, latency
budget). Secrets stay out of cases — auth is via ADC (`gcloud`), see
[authentication.md](authentication.md).

## Transport status
- ✅ **`mock`** — runnable with no live app (harness self-test).
- ✅ **`unary`** — **live over REST `runSession`** (stdlib only). Sends `text`, seeds session
  `variables`. Contract: [api-reference.md](api-reference.md#runsession--confirmed-live-contract).
- ✅ **`stream`** — **live over gRPC `stream_run_session`** (server-streaming) via the official
  `google-cloud-ces` client. Streams partial text chunks; same multi-turn + variables model.
- ⛔ **true bidi** (`bidi_run_session`) is **not served** at `ces.googleapis.com` for this
  project/`eu` location — it returns HTTP **404** (vs. the 403 the other methods give, so it's a
  real availability gap, not auth). See [ADR-002](../design/decisions/ADR-002-streaming-transport.md).

## Auth note
The harness uses **ADC** (`google.auth.default`), a *separate* store from gcloud's active account.
`get_access_token()` verifies the token identity matches `authAccount` and fails loudly on a
mismatch; `scripts/check-auth.ps1` checks **both** stores. See [authentication.md](authentication.md).

## Still open
- [ ] Parse `SessionOutput.tool_calls` / `diagnosticInfo` to populate the `tool_called` /
      `transferred_to` / `escalated` assertions (the data is already returned).
- [ ] Revisit true `bidi_run_session` if/when it's enabled (needed for realtime audio).
