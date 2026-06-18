# Agent Design

> The single most important doc in this repo: **what** we're building and **why**.
> Everything under `app/` should trace back to a decision here. Fill in the `TODO`s with Lee.

## 1. Purpose & scope
- **Problem this agent solves:** _TODO_
- **Primary users:** _TODO_
- **Channels:** _TODO (chat / voice / both)_
- **In scope:** _TODO_
- **Explicitly out of scope:** _TODO_

## 2. Success criteria
How do we know it works? (e.g. containment rate, task completion, CSAT, latency.)
- _TODO_

## 3. Persona & tone
- **Name / persona:** _TODO_
- **Tone:** _TODO_
- **Must always:** _TODO (e.g. greet, confirm identity, give disclaimer)_
- **Must never:** _TODO (e.g. give legal/financial advice, expose internal data)_

## 4. Agent architecture
Single LLM agent, or a root agent with child/specialist agents + transfer rules?
- **Topology:** _TODO_
- **Agents:**
  | Agent | Responsibility | Tools | Transfers to |
  |-------|----------------|-------|--------------|
  | _root_ | _TODO_ | | |

## 5. Tools & integrations
What backend systems must the agent reach? (CRM, order system, KB, etc.)
| Tool | Backend / API | Inputs | Outputs | Notes |
|------|---------------|--------|---------|-------|
| _TODO_ | | | | |

## 6. Guardrails & compliance
- **Disclaimers / mandatory content:** _TODO_
- **Escalation rules:** _TODO_
- **Data handling / PII:** _TODO_

## 7. Conversation examples (happy paths)
Sketch 2–3 ideal dialogs — these become `examples/` and evaluation cases.

```
User:
Agent:
...
```

## 8. Environment
| Setting | Value |
|---------|-------|
| GCP project id | _TODO_ |
| Location / region | _TODO_ |
| App id (once created) | _TODO_ |
| API enabled? | _TODO_ |
