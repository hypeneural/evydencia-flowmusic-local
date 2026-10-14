---
name: flowmusic-local
description: Audit, run and repair localhost FastAPI SQLite FIFO generation queue on Windows; focused checks, logs, idempotency, manual reconciliation.
---
# Local API and queue
Follow AGENTS.md. Inspect only `app/main.py`, `app/queue.py` and focused `tests/test_queue.py`; avoid upstream code unless failure points there.
Workflow: one failure -> inspect protected `/v1/music/jobs/{id}/events` and local MVP ledger -> minimal fix -> one targeted offline test -> local supervised request if explicitly authorized.
Default mock. Live requires `start.ps1 -EnableLive` and individual `approve_live=true`. Stop on needs_review; never requeue or delete lock automatically.
