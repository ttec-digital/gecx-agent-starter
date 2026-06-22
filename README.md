# GECX Agent — build & test starter

A working starter for building a **Gemini Enterprise for Customer Experience (GECX)** application
that runs as a **CX Agent Studio** agent. It pairs a clean, source-of-truth folder structure with
distilled platform docs, a connectivity smoke test, and an **RPC test harness** — so you can focus
on designing and validating your agent instead of scaffolding.

> **📋 This is a GitHub _template repository_.** Click **"Use this template" → "Create a new
> repository"** to start a new agent project with a clean history (don't fork or clone this one
> directly). Full walkthrough: [Using this template](#using-this-template).
>
> **Status:** 🟢 Working "hello world" agent, validated end-to-end by the RPC harness over live
> `runSession`. Use it as a worked example; define your own agent in
> [`design/agent-design.md`](design/agent-design.md).
>
> **Shareable by design:** all environment-specific values live only in `config/config.json`
> (gitignored). Nothing else hardcodes a project, account, or path. See [Privacy](#privacy--sharing).

---

## What is this?

GECX is built on the **CX Agent Studio** platform (a playbook/LLM-agent model, *not* the older
Dialogflow CX flows-and-intents model). The core building block is an **app**, which contains
one or more **agents** (LLM agents with instructions), plus **tools**, **toolsets**,
**guardrails**, and **examples**.

You interact with the platform through its **direct REST API (v1)** for build/admin, and the
**RPC API** (`SessionService`) for running/testing sessions:

```
https://ces.googleapis.com/v1/projects/{project}/locations/{location}/apps/...
```

See [`docs/api-reference.md`](docs/api-reference.md) for the full resource map.

---

## Repository layout

```
<your-project>/
├── README.md                 # You are here — overview & onboarding
├── .gitignore                # Keeps secrets/config/runtime artifacts out of VCS
│
├── docs/                     # Platform knowledge (how the API & platform work)
│   ├── api-reference.md      # REST v1 resource hierarchy, paths, methods
│   ├── authentication.md     # How to authenticate API calls
│   ├── best-practices.md     # Distilled platform best practices + our stance
│   ├── testing.md            # How we validate the agent (RPC test harness)
│   └── auth-hook.md          # Optional: auto-check gcloud auth at session start
│
├── design/                   # What we are building and why
│   ├── agent-design.md       # Agent purpose, persona, scope, success criteria
│   └── decisions/            # Architecture Decision Records (ADRs)
│       ├── ADR-template.md
│       └── ADR-001-test-harness.md
│
├── app/                      # Source-of-truth resource definitions (JSON)
│   ├── agents/  tools/  toolsets/  guardrails/  examples/
│
├── config/
│   └── config.example.json   # Copy to config.json (gitignored) and fill in
│
├── scripts/                  # Helper scripts for API operations
│   ├── smoke-test.ps1        # Verifies auth + connectivity (lists apps)
│   ├── run-tests.ps1         # Runs the RPC regression harness (gate after changes)
│   └── check-auth.ps1        # Optional auth check (see docs/auth-hook.md)
│
├── tests/                    # RPC test harness (validate the agent)
│   ├── cases/                # test cases as YAML data (one convo per file)
│   ├── runner/               # modular Python runner (mock | unary | stream)
│   └── requirements.txt
│
└── .claude/
    └── settings.local.example.json   # Opt-in hook example (copy to settings.local.json)
```

> **Source-of-truth strategy.** Keep resource definitions as JSON under `app/` so changes are
> reviewable and diff-able. The platform also supports `exportApp` / `importApp` (a full app
> snapshot) — use those for backup and bulk sync. See [`docs/api-reference.md`](docs/api-reference.md).

---

## Using this template

This repository is a **GitHub template**, so every new agent project starts from a clean copy:

1. On GitHub, click **"Use this template" → "Create a new repository."** Name it for your agent
   (convention: `gecx-<purpose>-agent`) and choose **Private** to start.
2. **Clone your new repo** locally (not this template): `git clone https://github.com/<org>/<your-new-repo>.git`
3. Continue with [Getting started](#getting-started) — authenticate, copy `config.example.json` →
   `config.json`, fill in your project details, and run the smoke test.

You start from a clean, working baseline: a throwaway **"hello world"** agent as a worked example,
the RPC test harness, and distilled platform docs. Personal config is **not** carried over —
`config/config.json` and `.claude/settings.local.json` are gitignored — so define your own agent in
[`design/agent-design.md`](design/agent-design.md) and fill in your own environment.

> **Maintainers:** to (re)mark a repo as a template, run `gh repo edit <org>/<repo> --template`
> (or GitHub → *Settings* → check *Template repository*).

---

## Getting started

### Prerequisites
- A Google Cloud project with the CX Agent Studio / Conversational Agents API enabled.
- [`gcloud` CLI](https://cloud.google.com/sdk/docs/install) installed and initialized.
- Appropriate IAM permissions on the project (see [`docs/authentication.md`](docs/authentication.md)).

### 1. Authenticate
```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project <YOUR_PROJECT_ID>
```

### 2. Configure
```powershell
Copy-Item config/config.example.json config/config.json
# Edit config/config.json: projectId, location, appId (once created), optional authAccount
```

### 3. Verify connectivity
```powershell
./scripts/smoke-test.ps1   # lists apps in your project = auth + endpoint OK
```

*(Optional)* enable the auto auth-check hook — see [`docs/auth-hook.md`](docs/auth-hook.md).

---

## Build workflow

1. **Design** the agent in [`design/agent-design.md`](design/agent-design.md) — purpose, scope, persona, tools.
2. **Create the app** (one per agent project) via the API.
3. **Define agents, tools, toolsets, guardrails** as JSON under `app/`, then push via the API.
4. **Add examples** to steer agent behavior.
5. **Validate** after every major change with the RPC harness (`./scripts/run-tests.ps1`) and
   platform evaluations — see [`docs/testing.md`](docs/testing.md).
6. **Version** frequently (every 10–15 changes) with semantic names — see best practices.
7. **Deploy** to an environment.

---

## Define for your project

Fill these in as you go (see [`design/agent-design.md`](design/agent-design.md)):

- [ ] **What should this agent do?** Use case, target users, channels (chat/voice).
- [ ] **GCP environment:** project id, region/location, is the API enabled?
- [ ] **Integrations:** what backend systems/APIs must the agent call?
- [ ] **Guardrails:** compliance, disclaimers, escalation rules.

---

## Privacy & sharing

This repo is built to be shared safely:
- Real values (project id, app id, account) live **only** in `config/config.json` — gitignored.
- `.claude/settings.local.json` (personal hooks/paths) is gitignored; an example ships instead.
- `__pycache__/`, tokens, and key files are gitignored.

Before publishing: run a final scan for stray identifiers, and create the GitHub repo **private
first**, then flip to public after review.

---

## Key references

- REST API reference: https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/reference/rest
- RPC API reference: https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/reference/rpc
- Best practices: https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/best-practices
- Local distilled docs: [`docs/`](docs/)

---

## Conventions

- **API version:** v1 only, unless explicitly instructed otherwise.
- **Naming:** snake_case for tool parameters; semantic version labels for app versions (`v1.0.0`).
- **Secrets:** never commit `config/config.json`, `.claude/settings.local.json`, or tokens — all gitignored.
