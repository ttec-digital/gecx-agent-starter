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
> `unary` uses stdlib only; `pip install -r requirements.txt` is needed only for the future
> `bidi` (gRPC) transport.

## Layout
```
tests/
├── cases/                 # ⭐ test cases as YAML (copy _template.yaml to add one)
│   ├── smoke-greeting.yaml   # mock self-test
│   └── hello-world.yaml      # live agent over runSession
├── runner/                # modular Python package
│   ├── config / auth / cases / assertions / session / report
│   └── transports/        # base + mock + unary (REST, live) + bidi (skeleton)
└── requirements.txt
```

## Status
- ✅ `mock` — harness self-test (case loading, variables, assertions, exit codes).
- ✅ `unary` — **live** over REST `runSession`; validates the real agent and seeds session variables.
- 🟡 `bidi` — `streamRunSession` over gRPC; still a skeleton (see `runner/transports/bidi.py`).
