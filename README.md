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

The Windows install script fetches ONLY the pinned MIT-licensed `deluxebear/flowmusic-cli` upstream into ignored `vendor/` for inspection and runs its `npm test`. No login or real generation is performed. The agent may assess official terms and implement a reviewed live adapter on a separate PR; it must not bypass service controls.

## Source map
- `app/main.py`: FastAPI localhost, SQLite idempotency, mock artifact JSON.
- `tests/`: deterministic smoke tests.
- `scripts/windows/`: install/doctor/start.
- `AGENTS.md`, `.agent/skills/`, `.agent/workflows/`: Antigravity instructions.
- `docs/UPSTREAM_AUDIT.md`: pinned upstream rationale; `docs/OPERATIONS.md`: API and security.

CI runs mock Python tests on Windows and Linux. This is a staging scaffold, not a claim of a working authenticated Lyria generator or officially supported consumer API.
