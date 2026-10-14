# Source-of-truth upstream forensic audit

## Target source
- Primary: [deluxebear/flowmusic-cli](https://github.com/deluxebear/flowmusic-cli), pinned to `08491dc3319ae9f530c5c05c431196bbbbb10607` by `scripts/windows/install.ps1` (MIT code).
- Other audited candidates: [south1907/flowmusic-toolkit](https://github.com/south1907/flowmusic-toolkit) (FastAPI/Chrome extension, previous CI Makefile path issue); [genz27/FlowMusic2API](https://github.com/genz27/FlowMusic2API) (Go, unnecessary multi-account scope).
- The FastAPI app does not invoke upstream. An independent `scripts/mvp_probe.py` Windows operator tool may run the pinned upstream for one explicit real MVP. Node.js unit tests and our Python CI do not prove the live request works.

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

## Single-attempt MVP hardening\nThe manual script checks the pinned commit before calls, restricts the isolated local session directory, patches **only the two known unsafe POST retry expressions** inside gitignored vendor source, persists an exclusive request ID and single-flight lock before any generation, and writes allow-listed JSONL events without prompt or tokens. A remote rejection, timeout or other ambiguous failure stops and requires manual reconciliation; it cannot be safely retried blindly. Inspect the local vendor diff if upstream changes.\n\n## Validation levels
1. Static source / GitHub Actions: upstream unit checks and pinned source.
2. Windows `agent.cmd`: mock FastAPI + upstream test suite, no credits.
3. Manually supervised read-only account/model/credits diagnostic (only after terms review).
4. Operator-approved one-shot generation using `scripts/windows/mvp.ps1 -Mode generate -ApproveLive`, output inspection and review of local ledger (not executed by this audit).
No claim beyond level 2 is justified today.

## Evidence 2026-10-14
The operator reported a successful one-shot Lyria 3.5 WAV (28.7 seconds, 23,418,850 bytes, reported credit delta 5). This proves a manual probe at that point, not yet a second authenticated run through the newly added HTTP FIFO queue. The queue uses synthetic offline CI checks only until deliberately exercised on Windows.
