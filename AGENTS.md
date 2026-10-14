# Evydencia FlowMusic Local | AI-FIRST MVP (Gemini 3.8 Flash)

Goal: deliver **one real, observable Windows MVP experiment at a time**, not an oversized test framework. This project is standalone; do not edit Workflow/CRM.

## Operating loop (always)
1. Read this file; pick **one** relevant skill from `.agents/skills/` and **only affected code**.
2. State the single hypothesis, expected signal and stop condition in one sentence.
3. Make the smallest safe change, run **one focused check or real supervised probe**, and inspect redacted logs.
4. Report: command, result, evidence path, problem/next action. Repeat only when needed. Do not rerun the whole suite after each edit.

## Critical boundaries
- No real Google request without an explicit operator choice of `account` or `generate` in the one-shot MVP tool and explicit verification of applicable terms/credit budget.
- Do not bypass CAPTCHA, 403, 429, platform limits or account restrictions. Never print/copy OAuth tokens, URLs with auth codes, cookies, prompt contents or signed media URLs into logs, git or chat.
- An ambiguous upstream POST is **needs_review**: never automatically retry or spend credits twice. Same `request_id` must not regenerate.
- Pin upstream source; localhost only; one operator/process; never modify `main` or merge a PR automatically.
- Real audio proof is **distinct** from mock tests. Never claim mock = real.
- No extra dashboards, Docker, parallel agents, all-repo scans or generic refactors without evidence.

## Map
- `/flowmusic-mvp`: one-shot Windows check/account/real song + safe logs.
- `/flowmusic-local`: targeted API maintenance.
- `/flowmusic-codegraph`: dependency tracing **only if blocked**.
- `docs/MVP_RUNBOOK.md`: executable commands and log schema.
- `docs/SECURITY.md`: secrets and release gates.
- `agent.cmd`: optional safe diagnostics, not the Antigravity context file.
