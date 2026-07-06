# Tests — RPC validation harness

Validates the agent behaves as expected after major changes, by driving it over the RPC
`SessionService` and asserting on replies. **Full design & schema: [`../docs/testing.md`](../docs/testing.md)**
and [ADR-001](../design/decisions/ADR-001-test-harness.md).

## Quick start
```powershell
python -m runner                         # all cases (mock self-test + live hello-world)
python -m runner --transport mock        # mock only, no live agent needed
python -m runner --case hello-world      # just the live agent case
../scripts/run-tests.ps1                  # the gate to run after changes
```
> `unary` uses stdlib only; `pip install -r requirements.txt` (google-cloud-ces) is needed for the
> `stream` transport.

## Call reporting — what happened to one call
Pull the **server-side CES conversation trace** for a single call and render a per-call report
(overview, transcript interleaved with tool calls/responses, guardrail decisions, outcome). Driven
by `config/config.json`; auth is your active gcloud account. Stdlib only.

```powershell
./scripts/call-report.ps1 -List [-Limit 20]        # recent calls, newest first
./scripts/call-report.ps1 -Id test-1a2b3c4d5e6f    # rendered report to console
./scripts/call-report.ps1 -Id <id> -Out report.md  # ...or to a markdown file
./scripts/call-report.ps1 -Id <id> -Raw            # raw conversation JSON
```

`<id>` is the conversation id — the **same `test-<hex>` session id the harness mints**, so you can
jump straight from a test call to its full trace. Module: `tests/runner/conversations.py`
(`list` / `get` / `report`). This reads the CES `conversations` API — the agent's own server-side log.

## Layout
```
tests/
├── cases/                 # ⭐ test cases as YAML (copy _template.yaml to add one)
│   ├── smoke-greeting.yaml      # mock self-test
│   ├── hello-world.yaml         # live agent over unary runSession
│   └── hello-world-stream.yaml  # live agent over server-streaming
├── runner/                # modular Python package
│   ├── config / auth / cases / assertions / session / report
│   └── transports/        # base + mock + unary (REST) + stream (gRPC, live)
└── requirements.txt
```

## Status — all green (3/3)
- ✅ `mock` — harness self-test (case loading, variables, assertions, exit codes).
- ✅ `unary` — **live** over REST `runSession`; seeds session variables.
- ✅ `stream` — **live** over gRPC `stream_run_session` (server-streaming) via google-cloud-ces.
- ⛔ true `bidi_run_session` is not served for this project/location (404) — see [ADR-002](../design/decisions/ADR-002-streaming-transport.md).
