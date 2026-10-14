# Validate Windows without Google credit consumption
1. Read AGENTS.md.
2. Run scripts/windows/install.ps1 (clones pinned upstream into ignored vendor directory).
3. Run agent.cmd, verify tests and localhost.
4. Run mock API and test repeat request_id and 409 conflict.
5. Confirm Git status excludes tokens, audio and local sessions.
6. Report blockers, CI evidence and next steps; do not generate music.
