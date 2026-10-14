# Evydencia FlowMusic Local

An independent, **mock-first** Windows music-job API scaffold, intended for later connection to Evydencia's Python Workflow. **No real audio or AI Pro credits are used.** The pinned open-source `flowmusic-cli` is fetched for inspection/tests only; a Google consumer Flow Music private-endpoint integration is neither official nor enabled in this app.

## Windows — PR #1 branch
```powershell
git clone https://github.com/hypeneural/evydencia-flowmusic-local.git
cd evydencia-flowmusic-local
git fetch origin
git switch --track origin/feat/windows-local-engine-foundation
powershell -ExecutionPolicy Bypass -File scripts/windows/install.ps1
.\agent.cmd
powershell -ExecutionPolicy Bypass -File scripts/windows/start.ps1
```

Open `http://127.0.0.1:8765/docs`; protected API requests require `X-Local-Token` from local `data/local-token.txt`. Never paste this token into chat, logs or a PR.

The installer clones only `deluxebear/flowmusic-cli` into gitignored `vendor/`, pins commit `08491dc3319ae9f530c5c05c431196bbbbb10607` and runs `npm test` without logging in.

## Source / code graph
- `app/main.py`: FastAPI, SQLite transactions, mock JSON artifacts, local token ACL.
- `tests/test_api.py`: pytest fixture uses isolated temporary DB (never changes your operational `data/`).
- `docs/CODEGRAPH.md`: API call graph, state transitions, upstream boundary.
- `docs/SECURITY.md`: credentials, NTFS limitations, no-credit policy.
- `docs/UPSTREAM_AUDIT.md`: pinned source, known compatibility gaps and official framework docs.
- `AGENTS.md`, `.agents/skills/`: Antigravity Gemini Flash scoped instructions.
- `scripts/windows/`: installer, doctor, localhost startup; `agent.cmd` runs diagnostics.

## Limitations
The mock API is suitable for verifying the HTTP contract and local operational behavior. It is **not yet a live music generator**. Remaining release gates: supported/authorized integration method, Windows OAuth verification, explicit live permission, crash-safe remote job tracking, FFprobe audio QA and recovery without duplicate credit charges.
