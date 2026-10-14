---
name: flowmusic-local
description: Use for auditing, testing, securing or maintaining the mock-first Evydencia Windows FlowMusic FastAPI service; avoid real credits and secret exposure.
---
# Evydencia FlowMusic Local

Read `AGENTS.md` first, then `docs/CODEGRAPH.md`. Inspect only the affected code and tests.

## Minimal path for Gemini 3.8 Flash
1. Inspect PR #1, branch head, working tree; do not overwrite uncommitted Windows changes.
2. Read the graph to select **only** the relevant file and route; avoid scanning all vendor code.
3. Run `agent.cmd` on Windows. `python -m pytest -q` must use isolated temporary test data.
4. Make minimal patch; add a failing regression test first; run focused tests, then full tests.
5. Re-check `git status --short` and CI; commit only reviewed source, never data, tokens or audio.
6. Report evidence (commit, test counts, CI, limits) and stop without merge.

## Gates
- Default provider mock; never auto-login, scrape sessions, generate live music or consume credits.
- Do not bypass restrictions or account enforcement.
- Only localhost. One process/worker for current prototype. No automatic retries for ambiguous remote generation.
- Upstream CLI is pinned for offline inspection, not verified against live Google Flow Music.

See `docs/SECURITY.md` and `docs/UPSTREAM_AUDIT.md`. 
