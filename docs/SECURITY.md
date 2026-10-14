# Security / release gates

## Scope
Localhost-only FastAPI mock. `flowmusic-cli` under `vendor/` is pinned, separately testable and **not** a live provider here. Never claim that passing mock tests confirms Google Lyria generation.

## Credentials
- `data/local-token.txt` is never committed. `bootstrap()` reapplies access restrictions on every start. On Windows, `icacls` failure blocks startup instead of silently continuing.
- The current `icacls` grants to the Windows user and removes inherited ACEs, but **does not prove removal of unrelated explicit ACL entries**. Before deploying in a shared/multi-user Windows workstation, inspect `icacls data\\local-token.txt` and inherited permissions on `data/` (and protect secrets in the future CLI session directory separately).
- Keep NTFS ACLs on secret directories, not just the token file; do not send token or OAuth sessions to GitHub, logs or chat.
- Loopback binding is not a security boundary against malicious software running as the same Windows user.
- `GET /health` and FastAPI `/docs` remain publicly accessible on loopback; actual jobs and status require X-Local-Token. Do not expose through LAN/reverse proxy.
- Existing session tokens stored by upstream may rotate; no simultaneous producers. Do not copy main Chrome cookies.

## Reliability
- SQLite `request_id` UNIQUE enforces idempotent **creation**, even across processes. It is not a provider-side idempotency guarantee.
- No retry of possibly accepted remote POSTs. Fail/unknown -> `needs_review` until manually reconciled.
- Mock stage saves atomic JSON artifacts, not audio. Do not use mock artifacts in the production media pipeline.
- Local live worker is deliberately absent. Need durable, crash-safe single-worker queue and reconciliation before allowing any real generation.

## Product compliance
Flow Music consumer subscription does not provide an officially documented unlimited public generation API. Validate applicable service terms before any UI automation/private endpoint use. Stop for challenge, 403, 429 or account restrictions; never bypass platform controls. Obtain explicit user approval of every credit-consuming live test.
