# Source-of-truth upstream forensic audit

## Target source
- Primary: [deluxebear/flowmusic-cli](https://github.com/deluxebear/flowmusic-cli), pinned to `08491dc3319ae9f530c5c05c431196bbbbb10607` by `scripts/windows/install.ps1` (MIT code).
- Other audited candidates: [south1907/flowmusic-toolkit](https://github.com/south1907/flowmusic-toolkit) (FastAPI/Chrome extension, previous CI Makefile path issue); [genz27/FlowMusic2API](https://github.com/genz27/FlowMusic2API) (Go, unnecessary multi-account scope).
- The local app does not import or invoke upstream yet. Node.js tests confirm behavior of mocks/helpers, not live authentication or music generation.

## Verified source paths and risks
| Upstream path | Logic inspected | Remaining risk |
|---|---|---|
| `src/lib/auth.mjs` | Login via OAuth/PKCE or dedicated Chrome, rotating Supabase refresh token stored in session.json; Unix-biased command discovery | Windows native browser opener, ACL, single-session refresh ownership |
| `src/lib/client.mjs` | `BASE = https://www.flowmusic.app/__api`; `POST /producer/tool-call`; `GET /messages/{id}/stream`; `audio__create_song` | All endpoints are undocumented, susceptible to change; ambiguous POST retry must not double spend |
| `src/commands/context.mjs` | Validates `--model` using `GET /models`; formats prompt/lyrics; polls clips and downloads | Shared conversation/lyrics map with concurrent batches; writes directly to output |
| `src/commands/create.mjs` | `gen`, `batch`, model, length, lyrics | Concurrent jobs share client state; restrict to one until verified |
| `src/lib/state.mjs` | JSON conversation state | No cross-process locking |
| `test/client.test.mjs`, `test/util.test.mjs` | HTTP mock behavior, SSE helper, argument parsing | No live end-to-end coverage |

**Correction of prior report:** The source's `BASE` default is `https://www.flowmusic.app/__api`, **not** `https://api.flowmusic.app`. Do not assume historical routes or stale README claims are current.

## Framework documentation (checked 2026-10-14)
- Python sqlite3 connection context managers commit/rollback but do not close by themselves: https://docs.python.org/3/library/sqlite3.html
- FastAPI lifespan should be tested with `with TestClient(app)`: https://fastapi.tiangolo.com/advanced/testing-events/
- Microsoft icacls: `/inheritance:r` removes inherited ACEs; `/grant:r` replaces explicit grants for a specified principal, not every other principal: https://learn.microsoft.com/windows-server/administration/windows-commands/icacls
- Uvicorn has worker multiprocess support; current service must use `--workers 1` until a durable worker model is implemented: https://www.uvicorn.org/deployment/
- Antigravity defaults to `.agents/skills/`; legacy workflows stop October 19, 2026: https://www.antigravity.google/docs/migration/workflows-to-skills/

## Validation levels
1. Static source / GitHub Actions: upstream unit checks and pinned source.
2. Windows `agent.cmd`: mock FastAPI + upstream test suite, no credits.
3. Manually supervised read-only account/model/credits diagnostic (only after terms review).
4. Explicitly approved single generation and real WAV quality validation (not done).
No claim beyond level 2 is justified today.
