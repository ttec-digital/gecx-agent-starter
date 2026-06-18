# gRPC stubs for SessionService

The `unary` and `bidi` transports need a generated `SessionServiceStub` for
`google.cloud.ces.v1.SessionService`. Resolve this when wiring the live transports
(it's the main `TODO(confirm)` in `../unary.py` / `../bidi.py`).

## Option A — published client library (preferred)
Check whether a Python client library ships the CES/Conversational Agents v1 stubs
(e.g. under `google-cloud-dialogflow` or a dedicated package). If so, import from it and
delete this folder.

## Option B — generate from .proto
1. Obtain the `google/cloud/ces/v1/*.proto` definitions (from the Google APIs repo or the
   product's published protos).
2. Generate Python stubs into this folder:
   ```bash
   python -m grpc_tools.protoc -I <proto_root> \
     --python_out=. --grpc_python_out=. \
     google/cloud/ces/v1/session_service.proto
   ```
3. Update the imports at the top of `../unary.py` and `../bidi.py`.

## Also confirm
- gRPC target host/port for `google.cloud.ces.v1` (vs. the REST host `dialogflow.googleapis.com`).
- Field locations for: user text, **session variables** (SessionConfig/SessionInput), reply text,
  tool-call and transfer signals (SessionOutput).
