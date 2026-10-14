# Evydencia FlowMusic Local — Antigravity rules
Read docs/OPERATIONS.md first. This is an independent Windows repository; do not modify Python Workflow or CRM.
Default mock-only. Never send music-generation requests, log in, extract browser cookies, or consume Google credits automatically.
No CAPTCHA or rate-limit bypass. Confirm terms and account permission before live automation.
No secrets in Git, PR descriptions, terminal transcripts or screenshots. The local token file lives under gitignored data/.
Read only relevant code, not all of vendor/. Vendor upstream must be pinned and license preserved.
Keep one worker / process, SQLite idempotency, no automatic retry of ambiguous remote POSTs.
Agent strategy for Gemini 3.8 Flash: inspect narrow file, formulate minimal patch, run mock tests, document evidence, create PR. Never declare a live generation tested on mock evidence.
agent.cmd is a Windows diagnostics shortcut, not a native Antigravity instruction format.
Use .agent/skills/flowmusic-local/SKILL.md and .agent/workflows/validate-local.md.
