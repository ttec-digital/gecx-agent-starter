# Optional: auto-check gcloud auth at session start

A convenience for working in Claude Code: a **SessionStart hook** that runs
[`../scripts/check-auth.ps1`](../scripts/check-auth.ps1) every time a session starts and prints a
one-line `[AUTH OK]` / `[AUTH REMINDER]`. The output becomes session context, so you (and Claude)
get an early nudge if your gcloud token is stale or the wrong account is active. **Opt-in** - it's
not enabled by default.

## What the check does
- Reads `authAccount` from `config/config.json`.
  - **Set** (e.g. `"you@yourorg.com"`): enforces that exact account is active with a valid token.
  - **Empty**: just confirms a usable gcloud token exists.
- Always exits 0, so it never blocks a session.

## Enable it
1. Set your account in `config/config.json` (optional but recommended):
   ```json
   "authAccount": "you@yourorg.com"
   ```
2. Copy the example hook and point it at this repo:
   ```powershell
   Copy-Item .claude/settings.local.example.json .claude/settings.local.json
   ```
   Then edit `.claude/settings.local.json` and replace `<ABSOLUTE_PATH_TO_REPO>` with the repo's
   absolute path (e.g. `C:/Users/you/projects/gecx-agent`).
3. Open `/hooks` once (or restart Claude Code) so the new hook is loaded. It fires from the next
   session onward.

`.claude/settings.local.json` is gitignored, so your personal account/paths never get shared.

## Test it without the hook
```powershell
./scripts/check-auth.ps1
```
