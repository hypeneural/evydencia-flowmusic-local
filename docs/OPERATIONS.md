# Local service operations

This repository provides a **mock-tested API scaffold**, not a verified live Google Flow Music integration. Real account tests need explicit confirmation of platform permissions and user approval.

## Endpoints
- `GET /health` (public, health status)
- `GET /v1/music/status` (`X-Local-Token` required; provider state and safety note)
- `GET /v1/music/credits` (`X-Local-Token` required; read-only account diagnostic gate)
- `POST /v1/music/jobs` (`X-Local-Token` required; accepts payload with unique `request_id`, returns 202; idempotent repeat returns same `job_id`; payload conflict returns 409)
- `GET /v1/music/jobs/{id}` (`X-Local-Token` required; returns job state, result, or error)
- `GET /v1/music/jobs/{id}/artifacts` (`X-Local-Token` required; returns artifact metadata if completed, 409 otherwise)

## Security and Windows NTFS Protection
- The secret local token is generated at `data/local-token.txt` on startup.
- On Windows, `bootstrap()` enforces NTFS ACL restrictions via `icacls`, granting read/write exclusively to the current Windows user (`%USERNAME%`).
- Never bind beyond `127.0.0.1`.
- Never commit or paste `data/local-token.txt` or `data/jobs.db`.

## Single Worker & Concurrency Safety
- Run with `--workers 1` only. Concurrency can corrupt Supabase OAuth rotating refresh tokens and cause race conditions.
- SQLite connections are managed via context managers ensuring deterministic connection close (`conn.close()`) to avoid Windows file locks.
- Ambiguous in-flight remote operations during crash/restart are transitioned to `needs_review` rather than re-executed.

## Upstream Integration & Windows Notes
- Upstream reference: `deluxebear/flowmusic-cli` at commit `08491dc3319ae9f530c5c05c431196bbbbb10607` (MIT).
- If evaluating upstream live login on Windows, `CHROME_BIN` must be explicitly pointed to `chrome.exe` (e.g. `C:\Program Files\Google\Chrome\Application\chrome.exe`) because upstream only checks POSIX paths.
- Interactive browser login via `loginWithBrowser` requires manual navigation to the logged URL on Windows because upstream relies on Unix `xdg-open`/`open`.
- Live provider remains disabled (`FLOWMUSIC_PROVIDER=mock`) until authorized and validated.
