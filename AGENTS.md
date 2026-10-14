# Evydencia FlowMusic Local — repo rules for Antigravity / Gemini 3.8 Flash

This is an independent Windows service. Do not edit the Evydencia Python Workflow or CRM. Do not merge PR #1 without review.

## Read in this order (minimal context)
1. `docs/CODEGRAPH.md` — choose the affected call path.
2. `docs/SECURITY.md` — safety gates.
3. Only affected source file(s) + targeted tests; avoid reading all `vendor/`.
4. `docs/UPSTREAM_AUDIT.md` only if debugging the pinned Node upstream.

## Skills
- `/.agents/skills/flowmusic-local/SKILL.md` — local validation and minimal patches.
- `/.agents/skills/flowmusic-codegraph/SKILL.md` — dependency tracing and state machine.
- These paths match the current Antigravity skills standard; do not add legacy workflow files.
- `agent.cmd` is only a safe Windows diagnostics shortcut, NOT an Antigravity instruction file.

## Execution constraints
- Default mock-only; do not log in, capture browser credentials or spend AI Pro credits without explicit per-test approval and permission to automate.
- Never bypass CAPTCHA, rate limits or access restrictions.
- Never commit token files, credentials, session.json, audio/client data or unreviewed vendor copies.
- Maintain local loopback; prevent remote exposure; one Uvicorn worker in staging.
- A `request_id` replay must NEVER cause a second remote music generation; ambiguous remote results need review.
- Tests must use `tmp_path` fixtures (never real `data/jobs.db`).
- For each patch: assert upstream SHA, work on feature branch, add regression, run `agent.cmd`, review `git diff --check`, push to PR; no automatic merge.
- Separate static/codegraph findings, unit/CI results, and actual authenticated evidence in reports.
