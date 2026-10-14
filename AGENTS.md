# Evydencia FlowMusic Local — Gemini 3.8 Flash | AI-FIRST MVP
Goal: deliver **one real, observable Windows experiment at a time** with minimal edits. Independent repo: never modify CRM / Workflow.

## Decision loop
1. Read this file; use ONE relevant skill from `.agents/skills/`, then only affected code.
2. Hypothesis -> one focused check / one explicitly approved live request -> redacted ledger/event evidence -> next action.
3. Do not run the full suite after every change; use targeted tests and Windows smoke before PR merge.

## Core controls
- API default = mock. Live requires `start.ps1 -EnableLive` **and** `approve_live=true` on each job.
- One CLI process / one active generation; SQLite queue FIFO; max 25 pending.
- A failed/uncertain provider submission -> `needs_review`, queue **stops**. Never auto-retry or reuse a prior request ID; manually reconcile based on provider library.
- Do not print/store account tokens, cookies, OAuth URLs, raw provider responses or customer media in Git or external logs.
- No bypass of CAPTCHA, 403/429, platform quotas, or access limits. Terms must permit selected automation; otherwise stop.
- Scripts are Windows-local. No Docker/Redis/Celery/multi-account unless strong evidence justifies it.
- Never merge PR automatically or touch main.

## Where to work
- `app/main.py`: FastAPI contracts and original mock service.
- `app/queue.py`: durable claim + single worker + events and reconciliation.
- `scripts/mvp_probe.py`: already-real one-shot generator; don't reimplement or refactor without proven need.
- `docs/API_QUEUE.md`: API and queue contract.
- `tests/test_queue.py`: fake provider/SQLite queue unit checks, no Google calls.
- `.agents/skills/flowmusic-mvp/`: one-shot probe; `.agents/skills/flowmusic-local/`: API/queue repair.

Report concise: SHA, actual command, state, event evidence, next action. Distinguish simulated CI and authenticated Windows proof.
