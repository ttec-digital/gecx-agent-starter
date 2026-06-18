# Best Practices — CX Agent Studio

> Distilled from:
> https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/best-practices
>
> Per project guidance: these are guidelines to be **aware of**, not rules to fully comply with.
> Where a better design decision exists, we take it and record the reasoning in an ADR under
> [`../design/decisions/`](../design/decisions/).

## Agent design
- **Start simple.** Ship a narrow, well-scoped use case before adding complexity.
- **Instructions: specific & unambiguous**, organized by topic. Use the platform's *restructure*
  feature to format instructions — it improves reliability.

## Tools & integration
- **Wrap APIs in Python tools** rather than exposing raw endpoints — keeps irrelevant data out of
  the context window and saves tokens.
- **Chain inside one tool.** Prefer a single tool that orchestrates a multi-step chain over telling
  the agent to call several tools in sequence — fewer model predictions, less hallucination.
- **Clear definitions:** distinct tool names; `snake_case`, descriptive parameter names; flatten
  nested structures.
- **Pass session context** to OpenAPI tools via `x-ces-session-context` annotations so the model
  doesn't have to predict those values.

## Sessions, latency & UX
- **Deterministic greetings** via callbacks — avoids a model call, cuts latency.
- **Partial / prefix responses** to acknowledge quickly while the model works in the background.
- **Mandatory content** (disclaimers, legal text): validate/enforce via callbacks rather than
  hoping the model emits it.

## Error handling
- **Fail gracefully & deterministically.** When a critical tool fails, transfer to an escalation
  agent or end the session — never let the agent loop.

## Context & variables
- Use variables + callbacks to build **adaptive instructions** from user/session context.

## Audio & voice (if voice channel)
- Prerecorded brand greetings / legal disclosures with `interruptable: false`.
- Cancellable hold music during slow tool calls; auto-stops on completion.
- Use the `customize_response` system tool for **barge-in control** — block interruption on
  critical info, allow it elsewhere.

## Versioning & collaboration
- **Version often** — every ~10–15 changes — with semantic labels (`v1.0.0`) or descriptive ones
  (`prod-ready-for-testing`) and meaningful descriptions.
- Agree on a **merge/version-control process** up front (third-party VCS vs. built-in snapshots).

## Testing & QA
- Use **evaluations** to pin expected behavior and validate external API behavior before deploy.
- Do **end-to-end** testing of integrations before going live.

---

## Our stance (living list)
Decisions where we deviate or make a deliberate choice — link the ADR.

| Topic | Decision | ADR |
|-------|----------|-----|
| Source of truth | JSON resource defs under `app/`, reviewed in VCS; `exportApp` for backup | _TBD_ |
| _…_ | | |
