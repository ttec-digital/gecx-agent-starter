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

**Naming:** one resource per file, `displayName` in kebab- or snake-case matching the filename.
The app itself (and its `appId`) is recorded in `config/config.json`, not here.
