# CLAUDE.md — working guide for AI assistants (and humans)

Operational conventions for working in this repo. The [README](README.md) is the onboarding
overview; this file is the "how we work here" companion — read it before making changes.

This is a **GECX / CX Agent Studio** starter (a playbook / LLM-agent model, not Dialogflow CX
flows). Define your own agent in [design/agent-design.md](design/agent-design.md); keep resource
definitions under `app/` and validate with the test harness.

---

## Golden rules

1. **Plan first, then act — and challenge.** Before non-trivial work, share a short plan. If a
   request conflicts with the code, the docs, or itself, say so rather than order-taking.
2. **Never commit environment/secret files.** `config/config.json`, `.claude/settings.local.json`,
   `*.local.md`, tokens and `*-key.json` are all gitignored — keep it that way. All real values
   (project id, app id, account) live **only** in `config/config.json`.
3. **Pushing to `main` needs explicit user sign-off.** Staging a commit is fine on request; the
   `checkout main → merge --ff-only → push` step must be authorized each time.
4. **Don't touch the user's `gcloud` state.** Auth is theirs to control. If the active account is
   wrong, report it and let them switch — don't run `gcloud config set account`.
5. **`app/` mirrors the live platform.** Files under `app/` are faithful exports of the deployed
   app — don't "improve" them; sync them (see `export-app.ps1` / `push-app.ps1`). Design intent
   goes in `design/`, not by editing exports.
6. **Confirm before destructive actions. Dry-run wherever possible.** Prefer a preview/plan first
   (e.g. `push-app.ps1` without `-Apply`); only mutate live resources or discard work after showing
   what will change and getting the go-ahead.

---

## Environment & targets

- Target project / location / app / account all come from **`config/config.json`** (gitignored,
  per-user). Copy [config/config.example.json](config/config.example.json) to create it.
- The platform is reached at `https://ces.googleapis.com/v1/projects/{project}/locations/{location}/apps/{app}/...`
  — **location lives in the path; the host is always `ces.googleapis.com`.**
- **Know your external dependencies.** An app may reference resources in *other* GCP projects
  (secrets, DLP templates, Cloud Functions/tools). Those don't move when the app is copied — record
  them in [design/agent-design.md](design/agent-design.md) so a copy in a new project still resolves.

---

## Everyday commands

Run from the repo root unless noted. All scripts are PowerShell.

```powershell
# Auth / connectivity
./scripts/smoke-test.ps1                 # lists apps = auth + endpoint OK
./scripts/check-auth.ps1                 # active gcloud account vs config

# Push / export the app resources (app/*.json <-> live platform)
./scripts/push-app.ps1                   # DRY RUN: show the PATCH/CREATE plan (writes nothing)
./scripts/push-app.ps1 -Apply            # push every resource to the app in config.json
./scripts/push-app.ps1 -Id my_agent -Apply         # push a single resource
./scripts/export-app.ps1 [-Prune]        # refresh app/*.json from the live app

# Tests (the gate after any change)
./scripts/run-tests.ps1
cd tests; python -m runner                       # all cases (mock + live)
cd tests; python -m runner --transport mock      # mock only, no live agent
cd tests; python -m runner --case smoke-greeting

# Per-call report (CES conversations API — the agent's own server-side trace, NOT BigQuery)
cd tests; ../scripts/call-report.ps1 -List -Limit 10
cd tests; ../scripts/call-report.ps1 -Id <conversation-id> [-Out report.md] [-Raw]
```

> The call-report `<id>` **is** the `test-<hex>` session id the harness mints, so you can jump
> straight from a test run to that call's full trace. See [tests/README.md](tests/README.md).

---

## Git workflow ("the usual")

```
branch  →  commit  →  checkout main  →  merge --ff-only  →  push origin main  →  branch -d
```

- Feature work goes on a branch; keep commits focused.
- **Never** fold `config/config.json` or `config/config.example.json` changes into a feature commit.
- The `merge --ff-only` + `push` step is **only** done with explicit user authorization (rule 3).
- End commit messages with the required `Co-Authored-By` trailer.

---

## Windows / PowerShell gotchas (this repo is developed on Windows)

- **Commit messages:** PowerShell 5.1 mangles `git commit -m "...quotes..."`. Write the message to
  a temp file and use `git commit -F <file>`.
- **BOM:** `Out-File utf8` / PowerShell writes a UTF-8 **BOM**. Read such files in Python with
  `encoding="utf-8-sig"`, or `json.load` will fail on "Unexpected UTF-8 BOM".
- **Console encoding:** the Windows console is cp1252 — emoji/curly-quote output crashes with
  `UnicodeEncodeError`. Prefer ASCII; keep non-ASCII out of `.ps1` files (a `.ps1` with no BOM is
  read as ANSI, so an em-dash in a string breaks the parser).
- **`.ps1` runs with PowerShell, not `python`.** Invoke `../scripts/foo.ps1`, never `python foo.ps1`.

---

## Where things live

| Area | Path |
|---|---|
| What we're building & why | [design/agent-design.md](design/agent-design.md) |
| Architecture decisions | [design/decisions/](design/decisions/) (ADR-001 harness, ADR-002 streaming) |
| Platform knowledge | [docs/](docs/) (api-reference, authentication, best-practices, testing) |
| Live app export (source of truth) | [app/](app/) — agents / tools / toolsets / guardrails / examples |
| Test harness | [tests/](tests/) — `cases/` (YAML) + `runner/` (mock \| unary \| stream) |

---

## Conventions

- **API version:** v1 only, unless explicitly told otherwise.
- **Naming:** snake_case for tool parameters; semantic version labels (`v1.0.0`) for app versions.
  App-resource file names are readable slugs — the **server resource id** is the last segment of
  each file's `name` field and isn't always the file name (some ids are UUIDs); the push/export
  scripts address resources by that embedded id.
- **Testing model:** cases are declarative YAML; `mock` self-tests the harness, `unary` (REST
  `runSession`) drives the live agent, `stream` uses server-streaming `stream_run_session`. Guard
  the build with `run-tests.ps1` after any change.
