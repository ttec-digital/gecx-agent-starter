# GECX / CX Agent Studio — REST API v1 Reference

> Distilled from the official reference:
> https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/reference/rest
> **Scope:** v1 only. Verify exact field names/schemas against the live docs before relying on them —
> this is a working summary, not a contract.

## Service endpoint ✅ confirmed

```
https://ces.googleapis.com/v1/...
```

- **Confirmed empirically** against a live project (location `eu`):
  `GET https://ces.googleapis.com/v1/projects/{p}/locations/{l}/apps` returns `200`.
- The product is **CES** (Customer Engagement Suite; console at `ces.cloud.google.com`, RPC package
  `google.cloud.ces.v1`). The host is **`ces.googleapis.com`**.
- ⚠️ The docs-summary host `dialogflow.googleapis.com` is **wrong** for this product — it 404s.
  So does the regional-prefixed `eu-ces.googleapis.com`. The **location lives in the path, not a
  host prefix** — `ces.googleapis.com` is used for all locations (incl. `eu`).

## Resource hierarchy

```
projects/{project}/locations/{location}
└── apps/{app}                         # the deployable application (one per agent project)
    ├── agents/{agent}                 # LLM agents — the core building block
    ├── tools/{tool}                   # individual tool integrations
    ├── toolsets/{toolset}             # grouped tool collections
    ├── guardrails/{guardrail}         # safety / policy controls
    ├── examples/{example}             # few-shot examples to steer behavior
    ├── sessions/{session}             # runtime user sessions
    ├── conversations/{conversation}   # conversation history
    ├── deployments/{deployment}       # deployment configurations
    └── versions/{version}             # app version snapshots
projects/{project}/locations/{location}/operations/{operation}   # long-running ops
message                                                          # messaging endpoint (send)
```

## Standard methods

Most resources support the standard set:

| Method | Verb   | Path pattern                              |
|--------|--------|-------------------------------------------|
| create | POST   | `.../{collection}`                        |
| list   | GET    | `.../{collection}`                        |
| get    | GET    | `.../{collection}/{id}`                    |
| patch  | PATCH  | `.../{collection}/{id}`                    |
| delete | DELETE | `.../{collection}/{id}`                    |

## App-level methods (`projects.locations.apps`)

| Method                | Verb   | Path                                                        |
|-----------------------|--------|-------------------------------------------------------------|
| create                | POST   | `/v1/projects/{p}/locations/{l}/apps`                       |
| list                  | GET    | `/v1/projects/{p}/locations/{l}/apps`                       |
| get                   | GET    | `/v1/projects/{p}/locations/{l}/apps/{app}`                 |
| patch                 | PATCH  | `/v1/projects/{p}/locations/{l}/apps/{app}`                 |
| delete                | DELETE | `/v1/projects/{p}/locations/{l}/apps/{app}`                 |
| exportApp             | POST   | `/v1/.../apps/{app}:exportApp`                              |
| importApp             | POST   | `/v1/.../apps/{app}:importApp`                              |
| executeTool           | POST   | `/v1/.../apps/{app}:executeTool`                            |
| retrieveToolSchema    | POST   | `/v1/.../apps/{app}:retrieveToolSchema`                     |
| getExtendedAgentCard  | GET    | `/v1/.../apps/{app}:getExtendedAgentCard`                   |

> `exportApp` / `importApp` move a whole app snapshot — use for backup and bulk sync.

## Agent resource (`projects.locations.apps.agents`)

Resource path: `projects/{p}/locations/{l}/apps/{app}/agents/{agent}`

An **agent** is "the fundamental building block that provides instructions to the LLM for executing
specific tasks." Agents can be organized hierarchically via `childAgents`.

### JSON schema (working summary)

```json
{
  "name": "string (read-only, server-assigned)",
  "displayName": "string (REQUIRED)",
  "description": "string",
  "instruction": "string",
  "modelSettings": { },
  "tools": ["<tool resource name>"],
  "toolsets": [ { } ],
  "guardrails": ["<guardrail resource name>"],
  "childAgents": ["<agent resource name>"],
  "transferRules": [ { } ],

  "beforeAgentCallbacks": [ ], "afterAgentCallbacks": [ ],
  "beforeModelCallbacks": [ ], "afterModelCallbacks": [ ],
  "beforeToolCallbacks":  [ ], "afterToolCallbacks":  [ ],

  "llmAgent": { },                 // default agent type
  "remoteDialogflowAgent": { },    // delegates to an external Dialogflow CX agent

  "generatedSummary": "string (read-only)",
  "validationErrors": ["string (read-only)"],
  "etag": "string",
  "createTime": "timestamp (read-only)",
  "updateTime": "timestamp (read-only)"
}
```

### Agent types
- **LlmAgent** (default): driven by `instruction` + callbacks against a model.
- **RemoteDialogflowAgent**: hands execution to an external Dialogflow CX agent, with input/output
  variable mapping and language config. Useful for reusing existing CX agents.

### Callbacks (deterministic hooks)
Callbacks let you run deterministic logic around the model/tool lifecycle — e.g. static greetings,
mandatory disclaimers, partial "acknowledgement" responses, validation, and graceful failure /
escalation. See [`best-practices.md`](best-practices.md).

## Session / runtime methods (`projects.locations.apps.sessions`)

| Method            | Purpose                                            |
|-------------------|----------------------------------------------------|
| generateChatToken | Obtain a token for a chat session                  |
| runSession        | Run a turn synchronously (unary)                   |
| streamRunSession  | Run a turn with streaming responses (bidi)         |

`message.send` is the messaging entry point.

### runSession — ✅ confirmed live contract

```
POST https://ces.googleapis.com/v1/{session}:runSession
  where {session} = projects/{p}/locations/{l}/apps/{app}/sessions/{sessionId}
  ({sessionId} is a free-form id you choose; a fresh id = a fresh conversation)
```

Request body:
```json
{
  "config": { "session": "projects/.../apps/{app}/sessions/{sessionId}" },
  "inputs": [
    { "variables": { "customer_name": "Sam" } },   // optional, see note
    { "text": "Hi there!" }
  ]
}
```

Response body:
```json
{
  "outputs": [
    {
      "text": "Hello! How can I help you today?",   // <- agent reply
      "turnCompleted": true,
      "turnIndex": 1,
      "diagnosticInfo": {
        "messages": [ /* user + agent turns, with default/updatedVariables chunks */ ],
        "rootSpan": { /* latency + per-agent/LLM spans */ }
      }
    }
  ]
}
```

- **Reply text:** `outputs[-1].text`.
- **Session variables:** `SessionInput` is a **oneof `input_type`** — `text` and `variables` are
  *separate* input entries. Pass variables as their own `{"variables": {...}}` entry **before**
  the `{"text": ...}` entry (seed once on the first turn). Undeclared variables are accepted and
  appear as `updatedVariables` in the diagnostic; to surface a variable to the LLM, reference it in
  the agent `instruction` (template) or declare it in the app's `predefinedVariableDeclarations`.
- This is exactly what the harness `unary` transport sends — see
  [`../tests/runner/transports/unary.py`](../tests/runner/transports/unary.py).

### Setting an agent's instruction — ✅ confirmed
```
PATCH https://ces.googleapis.com/v1/{agent}?updateMask=instruction
body: { "instruction": "You are a friendly assistant ..." }
```
`instruction` is a **top-level** field on the agent (default agent type is LlmAgent).

## Long-running operations

Mutating calls may return an `operation`; poll
`projects/{p}/locations/{l}/operations/{op}` until `done: true`.

---

### ⚠️ To confirm as we build
- [x] ~~Exact regional endpoint host~~ → `https://ces.googleapis.com` (location in path).
- [ ] Full schemas for `tools`, `toolsets`, `guardrails`, `examples`, `modelSettings`.
- [ ] Required IAM roles / API enablement steps (see [`authentication.md`](authentication.md)).
- [x] ~~`update_mask` semantics~~ → query param `?updateMask=<field>` (e.g. `?updateMask=instruction`). Confirmed live.
