# App resource definitions

Source-of-truth JSON for the GECX app's resources. Each file maps to one platform resource and is
pushed via the REST API (see [`../docs/api-reference.md`](../docs/api-reference.md)).

| Folder        | Resource path                              | What goes here                          |
|---------------|--------------------------------------------|-----------------------------------------|
| `agents/`     | `apps/{app}/agents/{agent}`                | LLM agent definitions (instruction, tools, callbacks) |
| `tools/`      | `apps/{app}/tools/{tool}`                  | Tool definitions (OpenAPI specs, Python tools) |
| `toolsets/`   | `apps/{app}/toolsets/{toolset}`            | Grouped tool collections                |
| `guardrails/` | `apps/{app}/guardrails/{guardrail}`        | Safety / policy controls                |
| `examples/`   | `apps/{app}/examples/{example}`            | Few-shot examples to steer agents       |

**Naming:** one resource per file; the file name is a readable slug. The **server resource id** is
the last segment of each file's `name` field and is **not** always the file name (some ids are
UUIDs) — the scripts below address resources by that embedded id, so you can keep readable file
names. The app itself (and its `appId`) is recorded in `config/config.json`, not here.

## Pushing & exporting

These files are the diff-able source of truth; move them to/from the platform with:

```powershell
./scripts/push-app.ps1                          # DRY RUN: show the PATCH/CREATE plan
./scripts/push-app.ps1 -Apply                   # push every resource to the configured app
./scripts/push-app.ps1 -Id my_agent -Apply      # push a single resource
./scripts/export-app.ps1                         # refresh app/*.json from the live app
./scripts/export-app.ps1 -Prune                  # ...also delete locally-orphaned files
```

- **Push is dry-run by default** — it prints the plan and writes nothing until `-Apply`. Read-only
  fields (`name`, `etag`, `createTime`, …) are stripped; existing resources are PATCHed, missing
  ones POST-created (in dependency order: tools → toolsets → guardrails → examples → agents).
- Both target **only** the app in `config/config.json`. Reference fields (an agent's `tools[]`, the
  app's `rootAgent`) embed the source app path, so push back to the **same** app they came from; use
  the platform's `exportApp`/`importApp` for whole-app moves to a different app.
