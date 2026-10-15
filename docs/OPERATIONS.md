# Operations — default mock, optional real queue

## Contract
Host `127.0.0.1:8765`; header `X-Local-Token` from gitignored `data/local-token.txt`.
- `GET /health` (no token)
- `GET /v1/music/status`, `GET /v1/music/credits` (token; no provider network calls)
- `POST /v1/music/jobs` (token; idempotent `request_id`; 202)
- `GET /v1/music/jobs/{id}`, `GET /v1/music/jobs/{id}/artifacts` (token)
- Input: `request_id`, `prompt`, optional `model/title/lyrics/instrumental/duration_seconds/output_format`.
- Output is mock JSON in `data/output/`, **not an audio file**. Same id+same payload -> original job; different payload -> 409.

## Database and failure semantics
- `db()` uses an explicit `conn.close()` after SQLite transaction commit or rollback, as required by the Python library semantics.
- `request_id` UNIQUE and `INSERT OR IGNORE` prevent duplicate creation races across processes. Not equivalent to provider-side idempotency.
- Mock writes to `.tmp` then `os.replace`; filesystem failure yields `failed`, not perpetual `queued`.
- On restart, transient states (`submitting/generating/downloading/validating`) become `needs_review`. Never automatically repeat a possibly charged remote generation.
- A concurrently queried newly created mock can transiently report `queued`; client must poll.

## Windows security
- Token ACL is reapplied on **every startup**; `icacls` errors prevent service startup. Audit with `icacls data\\local-token.txt`; `/inheritance:r` alone does not remove arbitrary explicit ACEs. On shared desktops also restrict the data/session directories and confirm ACLs.
- Only run one worker with `scripts/windows/start.ps1`; no remote provider implementation exists yet.
- Do not run tests against operational database; tests use pytest `tmp_path`.
- Use `.agents/skills/`, not legacy workflows. `agent.cmd` runs safe checks only.

## Test
Run `agent.cmd` on Windows (Python compile+pytest and pinned upstream npm test). No Google credits are spent.

## FIFO real local
`start.ps1 -EnableLive` activates a single background worker. Each POST requires `approve_live=true` in its payload, and the request is persisted before any provider attempt. One process at a time; unknown results enter `needs_review` and stop the queue. See `docs/API_QUEUE.md` for endpoints, manual reconciliation and first live job.


## Inventário de contas
`GET /v1/music/accounts` devolve saldos cacheados sem realizar consultas externas. Cada pedido live fixa `account_profile` em `payload` do SQLite. Os snapshots por alias são persistidos separadamente em `data/account-snapshots/` e invalidados no início de uma tentativa do perfil. Veja `docs/ACCOUNTS.md`.
