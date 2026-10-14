---
name: flowmusic-mvp
description: Runs one supervised real-world Flow Music MVP validation on Windows using the pinned CLI, with read-only credit/model checks, at-most-once generation and structured no-secret logs.
---
# MVP real, observability first

Use `scripts/windows/mvp.ps1`, not improvised curl/Chrome automation. For minimal tokens, consult `docs/MVP_RUNBOOK.md` only when needed.

Decision tree:
- First setup -> `-Mode check` (offline, no credits).
- Explicit approved interactive login -> `-Mode login`; operator signs in in their own browser.
- Need account/model evidence -> `-Mode account` (read-only endpoints, logged event).
- Explicit permission to spend credits -> `-Mode generate -RequestId ... -Prompt ... -ApproveLive` (one song request; no automatic retry).
- Timeout/unknown/403/429 -> STOP; inspect Flow Music library and `data/mvp/ledger/` locally. Never reuse ID for a new remote generation.

One experiment = one expected signal, one run, one artifact/log review, one next step. Do not run broad suites for each task.
No session cookies, private URLs, prompts or full raw provider responses in recorded logs. Do not treat this unofficial protocol as an authorized production API.
