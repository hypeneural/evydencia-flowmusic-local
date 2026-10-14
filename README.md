# Evydencia FlowMusic Local

Independent Windows music-service foundation for eventual integration with Evydencia Python Workflow. **Current revision is MOCK ONLY and does not generate audio**. This avoids consuming Google AI Pro credits before permissions, safety and Windows validation.

## Install and test
```powershell
git clone https://github.com/hypeneural/evydencia-flowmusic-local.git
cd evydencia-flowmusic-local
powershell -ExecutionPolicy Bypass -File scripts/windows/install.ps1
.\agent.cmd
powershell -ExecutionPolicy Bypass -File scripts/windows/start.ps1
```
Visit http://127.0.0.1:8765/docs . A secret token is generated at `data/local-token.txt`; use HTTP header `X-Local-Token` to call protected routes. Do not share this token.

The Windows install script fetches ONLY the pinned MIT-licensed `deluxebear/flowmusic-cli` upstream (commit `08491dc3319ae9f530c5c05c431196bbbbb10607`) into ignored `vendor/` for inspection and executes its 15 unit tests. No login or real generation is performed.

## Source map
- `app/main.py`: FastAPI localhost (127.0.0.1), deterministic SQLite connection cleanup, Windows NTFS ACL token protection, SQLite idempotency, mock artifact JSON.
- `tests/test_api.py`: Comprehensive regression test suite (health, status, credits, lifecycle, idempotency, 409 payload conflict, 404 handling, crash recovery, and safety gates).
- `scripts/windows/`: `install.ps1`, `doctor.ps1`, `start.ps1` (hardened for Windows PowerShell, `py`/`python` runtime resolution, and `npm.cmd`).
- `AGENTS.md`, `.agent/skills/`, `.agent/workflows/`: Antigravity instructions and local workflow rules.
- `docs/UPSTREAM_AUDIT.md`: Upstream technical audit, Windows compatibility findings, and terms analysis.
- `docs/OPERATIONS.md`: API specifications, security, and single-worker operational architecture.

CI runs mock Python tests on Windows and Linux. This is a staging scaffold, not a claim of a working authenticated Lyria generator or officially supported consumer API.
